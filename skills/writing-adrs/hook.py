"""Claude Code hook entry for the writing-adrs skill.

Reads one hook event as JSON on stdin, decides what the agent should hear, and prints
`hookSpecificOutput` JSON — or nothing. Always exits 0: a hook here is advisory, and a
broken tool must say so in context rather than fall silent.

Events handled: SessionStart (standing note, baseline), SubagentStart (note), PreToolUse
(decisions binding the touched paths, once per agent per session), PostToolBatch
(reconcile; regenerate the index only after the agent's own ADR edit; report findings new
since the baseline once), Stop and SubagentStop (raise an open new finding once more).

Session state — the baseline and reported findings per managed root, the injected rows
per agent — lives in one JSON file per session under the plugin's data directory, updated
under a lock because matching hooks run in parallel.
"""

import fcntl
import json
import os
import shlex
import sys
import tempfile
import time
import traceback
from pathlib import Path

# The floor the syntax here needs. Never a non-zero exit, even here: print the crash as
# context and leave.
PYTHON_FLOOR = (3, 10)
if sys.version_info < PYTHON_FLOOR:
    print(
        '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":'
        '"phx:writing-adrs hook needs Python 3.10 or newer; the ADR checks are off until it is."}}'
    )
    sys.exit(0)

import adr

FILE_TOOLS = ("Edit", "NotebookEdit", "Read", "Write")
MAIN_AGENT = "main"
MAX_ROWS = 10
# Under the harness's 10,000-character cap, past which the text is swapped for a file path.
MAX_CHARS = 9_000
PRUNE_AFTER_SECONDS = 30 * 24 * 60 * 60
STATE_SUBDIR = "sessions"

NOTE = (
    "This repository records architectural decisions in docs/adr/ ({count} in force). Read "
    "docs/adr/INDEX.md before proposing an architectural or tooling change, so a settled "
    "decision is not relitigated. The decisions binding a file arrive in context the first "
    "time you touch it. Record a new decision with the phx:writing-adrs skill."
)
LABEL = (
    "Decisions binding {paths} — these paths, not the whole corpus; read docs/adr/INDEX.md "
    "before proposing an architectural or tooling change:"
)
FINDINGS_LABEL = "phx:writing-adrs found problems in {root}:"
STOP_LABEL = (
    "Before finishing, the ADR corpus in {root} still has problems you introduced this session:"
)
CRASH = "phx:writing-adrs hook failed ({error}); the ADR checks are off until it is fixed. See {path}."


def state_root(env: dict) -> Path:
    """Where session state lives: the plugin data directory, else the system temp directory."""
    base = env.get("CLAUDE_PLUGIN_DATA")
    return Path(base) if base else Path(tempfile.gettempdir()) / "phx-writing-adrs"


class State:
    """One session's state file, edited under a lock and written by atomic rename."""

    def __init__(self, state_dir: Path, session_id: str) -> None:
        self.directory = state_dir / STATE_SUBDIR
        self.path = self.directory / f"{session_id}.json"
        self.lock_path = self.directory / f"{session_id}.lock"
        self.data: dict = {}

    def __enter__(self) -> "State":  # noqa: PYI034 — no Self on the 3.10 floor
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = self.lock_path.open("w")
        fcntl.flock(self.lock, fcntl.LOCK_EX)
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.data.setdefault("injected", {})
        self.data.setdefault("roots", {})
        self.data.setdefault("crash_reported", False)
        return self

    def __exit__(self, *exc) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, sort_keys=True), encoding="utf-8")
        os.replace(temporary, self.path)
        fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.lock.close()

    def reset(self) -> None:
        """Forget everything, as `clear` does."""
        self.data = {"crash_reported": False, "injected": {}, "roots": {}}

    def root(self, root: Path) -> dict:
        """The record for one managed root, created empty on first sight."""
        return self.data["roots"].setdefault(
            str(root), {"baseline": None, "raised": [], "reported": []}
        )


def output(event_name: str, context: str, system_message: str | None = None) -> dict:
    """The JSON Claude Code reads."""
    result = {
        "hookSpecificOutput": {
            "additionalContext": context[:MAX_CHARS],
            "hookEventName": event_name,
        }
    }
    if system_message:
        result["systemMessage"] = system_message
    return result


def agent_key(event: dict) -> str:
    """Which context the rows go to: the main thread or one subagent."""
    return event.get("agent_id") or MAIN_AGENT


def managed_root_for(path: Path) -> Path | None:
    """The managed root above `path`, or None where nothing managed is above it."""
    root = adr.resolve_root(path)
    return root if adr.is_managed(root) else None


def format_row(row: adr.Row) -> str:
    """One decision as an injected line."""
    revisit = f" Revisit when: {row.revisit}" if row.revisit else ""
    return f"- {row.number} ({row.status}): {row.title} — {row.summary}{revisit} [{(adr.ADR_DIR / row.filename).as_posix()}]"


def format_findings(findings: list[adr.Finding]) -> str:
    """Findings as lines the agent can act on."""
    return "\n".join(f"- {f.message}" for f in findings)


def snapshot_baseline(state: State, root: Path) -> list[adr.Finding]:
    """Record the findings present now as the repository's, returning them."""
    findings = adr.reconcile(root, write=False)
    record = state.root(root)
    record["baseline"] = sorted(f.id for f in findings)
    return findings


def paths_in_command(command: str, cwd: Path) -> list[Path]:
    """Every token of a shell command that names an existing path, resolved from `cwd`."""
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    found = []
    for token in tokens:
        candidate = Path(token) if Path(token).is_absolute() else cwd / token
        # An existing path, or a slash-bearing token whose directory exists: the second
        # is a heredoc or redirect about to create a file, which still binds.
        if candidate.exists() or ("/" in token and candidate.parent.exists()):
            found.append(candidate)
    return found


def touched_paths(event: dict) -> list[Path]:
    """The paths a PreToolUse event is about."""
    tool = event.get("tool_name")
    tool_input = event.get("tool_input") or {}
    if tool == "Bash":
        return paths_in_command(tool_input.get("command", ""), Path(event.get("cwd", ".")))
    if tool in FILE_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        return [Path(path)] if path else []
    return []


def on_session_start(event: dict, state: State) -> dict | None:
    """The standing note, the baseline, and the state each source implies."""
    root = managed_root_for(Path(event.get("cwd", ".")))
    if root is None:
        return None
    source = event.get("source", "startup")
    if source == "clear":
        state.reset()
    if source == "compact":
        state.data["injected"] = {}
    rows, _ = adr.inspect(root)
    context = [NOTE.format(count=f"{len(rows)} decision" + ("" if len(rows) == 1 else "s"))]
    system_message = None
    if state.root(root)["baseline"] is None:
        findings = snapshot_baseline(state, root)
        if findings:
            body = format_findings(findings)
            context.append(FINDINGS_LABEL.format(root=root) + "\n" + body)
            system_message = FINDINGS_LABEL.format(root=root) + "\n" + body
    return output("SessionStart", "\n\n".join(context), system_message)


def on_subagent_start(event: dict, state: State) -> dict | None:
    root = managed_root_for(Path(event.get("cwd", ".")))
    if root is None:
        return None
    rows, _ = adr.inspect(root)
    return output(
        "SubagentStart",
        NOTE.format(count=f"{len(rows)} decision" + ("" if len(rows) == 1 else "s")),
    )


def on_pre_tool_use(event: dict, state: State) -> dict | None:
    """Rows binding the touched paths, once per agent."""
    by_root: dict[Path, list[str]] = {}
    for path in touched_paths(event):
        root = managed_root_for(path)
        if root is not None:
            by_root.setdefault(root, []).append(str(path))
    if not by_root:
        return None
    injected = state.data["injected"].setdefault(agent_key(event), [])
    rows: list[adr.Row] = []
    named: list[str] = []
    for root, paths in by_root.items():
        for row in adr.binding(root, paths):
            if row.number in injected:
                continue
            injected.append(row.number)
            rows.append(row)
            named.extend(adr.relative_to_root(p, root) or p for p in paths)
    if not rows:
        return None
    shown, rest = rows[:MAX_ROWS], rows[MAX_ROWS:]
    lines = [LABEL.format(paths=", ".join(sorted(set(named))))]
    lines.extend(format_row(row) for row in shown)
    if rest:
        lines.append(
            "Also binding, by number and path: "
            + "; ".join(f"{r.number} [{(adr.ADR_DIR / r.filename).as_posix()}]" for r in rest)
        )
    return output("PreToolUse", "\n".join(lines))


def written_adr_root(event: dict) -> Path | None:
    """The managed root of an ADR a file tool in the batch wrote, if any."""
    for result in event.get("tool_calls") or []:
        if result.get("tool_name") not in FILE_TOOLS or result.get("tool_name") == "Read":
            continue
        tool_input = result.get("tool_input") or {}
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not path:
            continue
        root = managed_root_for(Path(path))
        if root is not None and Path(path).resolve().is_relative_to(
            (root / adr.ADR_DIR).resolve()
        ):
            return root
    return None


def new_findings(state: State, root: Path, findings: list[adr.Finding]) -> list[adr.Finding]:
    """Findings not in the baseline; snapshots a baseline first where the root has none."""
    record = state.root(root)
    if record["baseline"] is None:
        record["baseline"] = sorted(f.id for f in findings)
        return []
    return [f for f in findings if f.id not in record["baseline"]]


def on_post_tool_batch(event: dict, state: State) -> dict | None:
    """Reconcile; write only after an ADR edit; report each new finding once."""
    root = written_adr_root(event)
    write = root is not None
    if root is None:
        root = managed_root_for(Path(event.get("cwd", ".")))
    if root is None:
        return None
    findings = adr.reconcile(root, write=write)
    record = state.root(root)
    fresh = [f for f in new_findings(state, root, findings) if f.id not in record["reported"]]
    if not fresh:
        return None
    record["reported"].extend(f.id for f in fresh)
    return output(
        "PostToolBatch", FINDINGS_LABEL.format(root=root) + "\n" + format_findings(fresh)
    )


def on_stop(event: dict, state: State) -> dict | None:
    """Raise each open finding that arose this session once more, then stay silent."""
    if event.get("stop_hook_active"):
        return None
    root = managed_root_for(Path(event.get("cwd", ".")))
    if root is None:
        return None
    findings = adr.reconcile(root, write=False)
    record = state.root(root)
    open_now = [f for f in new_findings(state, root, findings) if f.id not in record["raised"]]
    if not open_now:
        return None
    record["raised"].extend(f.id for f in open_now)
    return output(
        event["hook_event_name"],
        STOP_LABEL.format(root=root) + "\n" + format_findings(open_now),
    )


HANDLERS = {
    "PostToolBatch": on_post_tool_batch,
    "PreToolUse": on_pre_tool_use,
    "SessionStart": on_session_start,
    "Stop": on_stop,
    "SubagentStart": on_subagent_start,
    "SubagentStop": on_stop,
}


def prune(state_dir: Path, now: float) -> None:
    """Drop state files older than the session retention period."""
    directory = state_dir / STATE_SUBDIR
    if not directory.is_dir():
        return
    for path in directory.iterdir():
        if now - path.stat().st_mtime > PRUNE_AFTER_SECONDS:
            path.unlink(missing_ok=True)


def handle(event: dict, state_dir: Path, now: float) -> dict | None:
    """Dispatch one event. Raises on a malformed event; `main` turns that into context."""
    handler = HANDLERS.get(event.get("hook_event_name", ""))
    if handler is None:
        return None
    if event.get("hook_event_name") == "SessionStart":
        prune(state_dir, now)
    with State(state_dir, event.get("session_id", "unknown")) as state:
        return handler(event, state)


def main(stdin: str, state_dir: Path) -> str:
    """Read the event, handle it, and return the JSON text to print — or "" for nothing."""
    session_id = "unknown"
    try:
        event = json.loads(stdin)
        session_id = event.get("session_id", session_id)
        result = handle(event, state_dir, time.time())
        return json.dumps(result) if result else ""
    except Exception as exc:  # noqa: BLE001 — a hook must never fall silent
        try:
            with State(state_dir, session_id) as state:
                if state.data["crash_reported"]:
                    return ""
                state.data["crash_reported"] = True
        except Exception:  # noqa: BLE001, S110 — state is best effort on the crash path
            pass
        error = traceback.format_exc().strip().split("\n")[-1] or repr(exc)
        return json.dumps(
            output("SessionStart", CRASH.format(error=error, path=Path(__file__).resolve()))
        )


if __name__ == "__main__":
    text = main(sys.stdin.read(), state_root(dict(os.environ)))
    if text:
        print(text)
    sys.exit(0)
