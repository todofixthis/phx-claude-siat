"""Time the writing-adrs hooks per event, and fail where their p95 breaks the ceiling.

ADR 034 sets the budget: p95 at most 1 s per hook event, over at least twenty events on
this repository's corpus, SessionStart with its no-op sync counted and the first (cold)
sync not. This runs the hooks.json commands through `sh -c` as Claude Code would, from a
plugin root laid out as the plugin cache lays one out, and prints a table of what it
timed. Runs under uv from the repo root and imports only what `scripts/pyproject.toml`
declares (ADR 035):

    uv run python -m scripts.ci.time_hooks
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Every path below is repo-relative and joined to a `repo_root` where it is read, and
# `REPO_ROOT` is read only on the `__main__` line (ADR 027): nothing resolves a default
# path against whichever tree the caller happens to be standing in.
REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_HOOKS_FILE = Path("hooks/hooks.json")

CEILING_SECONDS = 1.0
# Twenty of each event type: each type's p95 is gated, and of fewer than twenty samples
# the nearest-rank p95 is the maximum, so one slow sample would fail the build.
DEFAULT_EVENTS = 80
# The plugin root's last component, which the hooks take as the version naming the venv.
TIMING_VERSION = "0.0.0-timing"
CACHE_PARENT = Path("plugins/cache/phx-claude-siat/phx")
# The file a completed sync leaves in the venv. The environment tests under
# skills/writing-adrs/tests name it too, but `scripts/` may not import from there.
VENV_MARKER = ".phx-synced"

# The order events are timed in, cycling, so the default gives twenty of each.
EVENT_CYCLE = ("SessionStart", "PreToolUse", "PostToolBatch", "Stop")
# The events that must print context every time: the note at each SessionStart, and the
# binding rows at each PreToolUse, every one a first touch. PostToolBatch and Stop speak
# only of new findings, so silence from them is no fault.
INJECTING_EVENTS = ("SessionStart", "PreToolUse")
# How hook.py's crash text opens. hook.py prints it and exits 0, so a crashing hook looks
# like a working one but for this text; `scripts/` may not import hook.py to share its
# constant, and a test asserts the two still agree.
CRASH_PREFIX = "phx:writing-adrs hook failed"
# Paths decisions bind, cycled through by the PreToolUse events. Each follows a timed
# SessionStart, a compact that resets injection, so every read is a first touch.
TOUCHED_PATHS = (
    Path("AGENTS.md"),
    Path("hooks/hooks.json"),
    Path("scripts/ci/versions.py"),
    Path("skills/writing-adrs/adr.py"),
    Path(".githooks/pre-commit"),
    Path("docs/adr/INDEX.md"),
)
SESSION_ID = "time-hooks"
# The cold SessionStart opens the session. Each timed one is a compact instead: compact
# resets the session's per-decision injection record, so every timed PreToolUse is a
# first touch that injects its path's full set of rows, whatever earlier reads delivered.
COLD_SOURCE = "startup"
TIMED_SOURCE = "compact"
# For an entry naming no timeout of its own; a bound either way.
DEFAULT_TIMEOUT_SECONDS = 120

# Set by `uv run` or by a Claude Code session running this; each would redirect a hook away
# from the venv and plugin root built here.
STRIPPED_VARIABLES = (
    "CLAUDE_PLUGIN_DATA",
    "CLAUDE_PLUGIN_ROOT",
    "CLAUDE_PROJECT_DIR",
    "UV_PROJECT_ENVIRONMENT",
    "VIRTUAL_ENV",
)


class HookError(Exception):
    """A hook failed or never ran, so its time measures nothing."""


def marker_path(data_dir: Path) -> Path:
    """Where the timing venv's sync marker lives under the plugin data directory."""
    return data_dir / "venvs" / TIMING_VERSION / VENV_MARKER


def p95(samples: list[float]) -> float:
    """The nearest-rank 95th percentile of `samples`."""
    if not samples:
        raise ValueError("no samples to take a percentile of")
    # ceil(0.95 * n) in integers, so float rounding cannot shift the rank.
    rank = (95 * len(samples) + 99) // 100
    return sorted(samples)[rank - 1]


def hook_commands(hooks_file: Path) -> dict[str, list[tuple[str, float]]]:
    """Each timed event's commands and their timeouts, in hooks-file order.

    Matchers are not applied: the real file's match every event built here, and an event
    with no command at all is an error rather than a zero.
    """
    hooks = json.loads(hooks_file.read_text(encoding="utf-8"))["hooks"]
    commands = {}
    for name in EVENT_CYCLE:
        commands[name] = [
            (entry["command"], entry.get("timeout", DEFAULT_TIMEOUT_SECONDS))
            for block in hooks.get(name, [])
            for entry in block["hooks"]
        ]
        if not commands[name]:
            raise HookError(f"{hooks_file} has no command for {name}")
    return commands


def build_event(name: str, project_dir: Path, index: int, *, cold: bool) -> dict:
    """The stdin for the `index`th occurrence of `name`, from the fields hook.py reads.

    `cold` marks the untimed SessionStart that opens the session.
    """
    event = {"cwd": str(project_dir), "hook_event_name": name, "session_id": SESSION_ID}
    path = str(project_dir / TOUCHED_PATHS[index % len(TOUCHED_PATHS)])
    read = {"tool_input": {"file_path": path}, "tool_name": "Read"}
    if name == "SessionStart":
        event["source"] = COLD_SOURCE if cold else TIMED_SOURCE
    elif name == "PreToolUse":
        event |= read
    elif name == "PostToolBatch":
        event["tool_calls"] = [read]
    return event


def run_event(
    commands: list[tuple[str, float]], event: dict, env: dict[str, str], cwd: Path
) -> tuple[float, list[str]]:
    """Run each command for `event` through `sh -c`; return their wall time and stdouts."""
    outputs = []
    start = time.perf_counter()
    for command, timeout in commands:
        try:
            result = subprocess.run(
                ["sh", "-c", command],
                capture_output=True,
                check=False,
                cwd=cwd,
                env=env,
                input=json.dumps(event),
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise HookError(
                f"{event['hook_event_name']} hook ran past its {timeout} s timeout"
            ) from exc
        if result.returncode != 0:
            raise HookError(
                f"{event['hook_event_name']} hook exited {result.returncode}: {result.stderr}"
            )
        outputs.append(result.stdout)
    return time.perf_counter() - start, outputs


def check_outputs(name: str, outputs: list[str], label: str) -> None:
    """Raise unless each output shows hook.py ran: no crash, and context where it must inject.

    A hook exiting at its marker gate, or a venv path the per-event hooks compute
    differently from sync.sh, prints nothing; hook.py crashing prints its crash text.
    Either times no work while passing the ceiling.
    """
    for stdout in outputs:
        context = ""
        if stdout.strip():
            try:
                context = json.loads(stdout)["hookSpecificOutput"]["additionalContext"]
            except (KeyError, TypeError, ValueError) as exc:
                raise HookError(f"{label} printed no hook JSON: {stdout!r}") from exc
        if context.startswith(CRASH_PREFIX):
            raise HookError(f"{label} reported a hook.py crash: {context}")
        if name in INJECTING_EVENTS and not context:
            raise HookError(f"{label} printed no additionalContext")


def hook_env(plugin_root: Path, data_dir: Path, project_dir: Path) -> dict[str, str]:
    """This process's environment minus what would redirect a hook, plus what Claude Code sets."""
    env = {key: value for key, value in os.environ.items() if key not in STRIPPED_VARIABLES}
    return env | {
        "CLAUDE_PLUGIN_DATA": str(data_dir),
        "CLAUDE_PLUGIN_ROOT": str(plugin_root),
        "CLAUDE_PROJECT_DIR": str(project_dir),
    }


def time_hooks(
    hooks_file: Path, plugin_root: Path, data_dir: Path, project_dir: Path, events: int
) -> dict[str, list[float]]:
    """Time `events` events cycling EVENT_CYCLE in one session; seconds per event name.

    Raises HookError where an event's output shows hook.py did not run, or where the venv
    is unmarked after any event: a SessionStart re-sync that fails unmarks it, the events
    after it exit at their gate, and a later re-sync would hide that from a check at the end.
    """
    commands = hook_commands(hooks_file)
    env = hook_env(plugin_root, data_dir, project_dir)
    marker = marker_path(data_dir)
    samples: dict[str, list[float]] = {name: [] for name in EVENT_CYCLE}
    for index in range(events):
        name = EVENT_CYCLE[index % len(EVENT_CYCLE)]
        label = f"{name} (timed event {index + 1} of {events})"
        event = build_event(name, project_dir, len(samples[name]), cold=False)
        elapsed, outputs = run_event(commands[name], event, env, project_dir)
        check_outputs(name, outputs, label)
        if not marker.is_file():
            raise HookError(
                f"No {marker} after {label}: the events after it would time nothing"
            )
        samples[name].append(elapsed)
    return samples


def print_table(samples: dict[str, list[float]]) -> list[float]:
    """Print count, mean and p95 per event and overall; return every sample."""
    print(f"{'event':<14} {'count':>5} {'mean (s)':>9} {'p95 (s)':>9}")
    every = [sample for name_samples in samples.values() for sample in name_samples]
    rows = [(name, values) for name, values in samples.items() if values]
    for name, values in [*rows, ("overall", every)]:
        mean = sum(values) / len(values)
        print(f"{name:<14} {len(values):>5} {mean:>9.3f} {p95(values):>9.3f}")
    return every


def main(argv: list[str], repo_root: Path) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ceiling", type=float, default=CEILING_SECONDS)
    parser.add_argument("--data-dir", type=Path, help="default: a fresh temp directory")
    parser.add_argument("--events", type=int, default=DEFAULT_EVENTS)
    # Joined to `repo_root` where it is read (ADR 027); an absolute path passes through.
    parser.add_argument("--hooks-file", type=Path, default=DEFAULT_HOOKS_FILE)
    args = parser.parse_args(argv)
    if args.events < 1:
        parser.error("--events must be at least 1")
    hooks_file = repo_root / args.hooks_file
    # The timing sync prunes every venv whose version is missing from its own one-version
    # cache, so pointed at a real plugin data directory it would delete the real venvs.
    if args.data_dir is not None and (args.data_dir / "venvs").is_dir():
        others = sorted(
            entry.name
            for entry in (args.data_dir / "venvs").iterdir()
            if entry.name != TIMING_VERSION
        )
        if others:
            print(
                f"❌ {args.data_dir} holds other venvs ({', '.join(others)}) the timing "
                "sync would prune; pass an empty or timing-only data directory"
            )
            return 1

    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        # A symlink, so the hooks see a cache path while running this checkout's files.
        plugin_root = tmp / CACHE_PARENT / TIMING_VERSION
        plugin_root.parent.mkdir(parents=True)
        plugin_root.symlink_to(repo_root.resolve(), target_is_directory=True)
        data_dir = args.data_dir or tmp / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        marker = marker_path(data_dir)

        try:
            commands = hook_commands(hooks_file)
            print("▶️ Cold SessionStart (untimed): syncing the venv")
            cold = build_event("SessionStart", repo_root, 0, cold=True)
            _, outputs = run_event(
                commands["SessionStart"],
                cold,
                hook_env(plugin_root, data_dir, repo_root),
                repo_root,
            )
            check_outputs("SessionStart", outputs, "SessionStart (cold)")
            # Without the marker every per-event hook exits at its gate in milliseconds,
            # which would pass the ceiling while timing nothing.
            if not marker.is_file():
                print(f"❌ No {marker} after the cold SessionStart: the sync failed")
                return 1
            print(f"▶️ Timing {args.events} hook events")
            samples = time_hooks(hooks_file, plugin_root, data_dir, repo_root, args.events)
        except HookError as exc:
            print(f"❌ {exc}")
            return 1

    every = print_table(samples)
    # ADR 034 bounds each hook event's p95, so one slow event type fails on its own even
    # where the others pull the overall figure under the ceiling.
    failed = False
    for name, values in samples.items():
        if values and p95(values) > args.ceiling:
            print(
                f"❌ {name} p95 {p95(values):.3f} s exceeds the {args.ceiling} s ceiling "
                "(docs/adr/034)"
            )
            failed = True
    overall = p95(every)
    if overall > args.ceiling:
        print(
            f"❌ Overall p95 {overall:.3f} s exceeds the {args.ceiling} s ceiling (docs/adr/034)"
        )
        return 1
    print(f"✅ Overall p95 {overall:.3f} s is within the {args.ceiling} s ceiling")
    if failed:
        # Logs are scanned for the last marker, so a failing run never ends on a ✅.
        print("❌ An event type's p95 exceeds the ceiling; see above")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], REPO_ROOT))
