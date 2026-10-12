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
DEFAULT_EVENTS = 24
# The plugin root's last component, which the hooks take as the version naming the venv.
TIMING_VERSION = "0.0.0-timing"
CACHE_PARENT = Path("plugins/cache/phx-claude-siat/phx")
# The file a completed sync leaves in the venv. The environment tests under
# skills/writing-adrs/tests name it too, but `scripts/` may not import from there.
VENV_MARKER = ".phx-synced"

# The order events are timed in, cycling. Twenty-four events give six of each, so each
# path below is read exactly once.
EVENT_CYCLE = ("SessionStart", "PreToolUse", "PostToolBatch", "Stop")
# Paths decisions bind, each read once so every PreToolUse is a first touch that injects.
TOUCHED_PATHS = (
    Path("AGENTS.md"),
    Path("hooks/hooks.json"),
    Path("scripts/ci/versions.py"),
    Path("skills/writing-adrs/adr.py"),
    Path(".githooks/pre-commit"),
    Path("docs/adr/INDEX.md"),
)
SESSION_ID = "time-hooks"
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


def build_event(name: str, project_dir: Path, index: int) -> dict:
    """The stdin for the `index`th timed occurrence of `name`, from the fields hook.py reads."""
    event = {"cwd": str(project_dir), "hook_event_name": name, "session_id": SESSION_ID}
    path = str(project_dir / TOUCHED_PATHS[index % len(TOUCHED_PATHS)])
    read = {"tool_input": {"file_path": path}, "tool_name": "Read"}
    if name == "SessionStart":
        event["source"] = "startup"
    elif name == "PreToolUse":
        event |= read
    elif name == "PostToolBatch":
        event["tool_calls"] = [read]
    return event


def run_event(
    commands: list[tuple[str, float]], event: dict, env: dict[str, str], cwd: Path
) -> float:
    """Run each command for `event` through `sh -c`; return the wall time they took."""
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
    return time.perf_counter() - start


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
    """Time `events` events cycling EVENT_CYCLE in one session; seconds per event name."""
    commands = hook_commands(hooks_file)
    env = hook_env(plugin_root, data_dir, project_dir)
    samples: dict[str, list[float]] = {name: [] for name in EVENT_CYCLE}
    for index in range(events):
        name = EVENT_CYCLE[index % len(EVENT_CYCLE)]
        event = build_event(name, project_dir, len(samples[name]))
        samples[name].append(run_event(commands[name], event, env, project_dir))
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
            cold = build_event("SessionStart", repo_root, 0)
            run_event(
                commands["SessionStart"],
                cold,
                hook_env(plugin_root, data_dir, repo_root),
                repo_root,
            )
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
        if not marker.is_file():
            print(f"❌ No {marker} after the timed events: the later ones timed nothing")
            return 1

    every = print_table(samples)
    overall = p95(every)
    if overall > args.ceiling:
        print(
            f"❌ Overall p95 {overall:.3f} s exceeds the {args.ceiling} s ceiling (docs/adr/034)"
        )
        return 1
    print(f"✅ Overall p95 {overall:.3f} s is within the {args.ceiling} s ceiling")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], REPO_ROOT))
