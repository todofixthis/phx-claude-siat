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
under a lock because matching hooks run in parallel. The lock is taken non-blocking with a
bounded retry, never held open-ended: a hook that cannot get it reports nothing for that
call rather than stall the tool call it runs beside.
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
# Bounded so a contended lock gives up rather than blocking the tool call beside it; ~1s
# worst case, well under the harness's own hook timeout.
LOCK_ATTEMPTS = 20
LOCK_RETRY_SECONDS = 0.05
MAIN_AGENT = "main"
MAX_ROWS = 10
# Under the harness's 10,000-character cap, past which the text is swapped for a file path.
MAX_CHARS = 9_000
PRUNE_AFTER_SECONDS = 30 * 24 * 60 * 60
STATE_SUBDIR = "sessions"
# The session a valid event naming none is handled against, so it still gets state and the
# crash-once rule rather than a KeyError reported on every call.
UNKNOWN_SESSION = "unknown"

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


class StateUnavailable(Exception):
    """The session lock could not be taken within the retry budget."""


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
        """Take the lock without blocking forever, then load state, corrupt-file safe.

        A lock never released — held by a hung sibling call, or a process that died before
        `__exit__` ran — must not wedge every later call for the session, so the wait is
        bounded rather than the blocking `flock` a `with`-only implementation would use.
        """
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = self.lock_path.open("w")
        for _ in range(LOCK_ATTEMPTS):
            try:
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                time.sleep(LOCK_RETRY_SECONDS)
        else:
            self.lock.close()
            raise StateUnavailable(f"could not lock {self.lock_path}")
        try:
            self.data = self._load()
        except Exception:
            fcntl.flock(self.lock, fcntl.LOCK_UN)
            self.lock.close()
            raise
        self.data.setdefault("injected", {})
        self.data.setdefault("roots", {})
        self.data.setdefault("crash_reported", False)
        self._normalise()
        return self

    def __exit__(self, *exc) -> None:
        """Write state, then always release the lock — even where the write itself fails."""
        try:
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.data, sort_keys=True), encoding="utf-8")
            os.replace(temporary, self.path)
        finally:
            fcntl.flock(self.lock, fcntl.LOCK_UN)
            self.lock.close()

    def _normalise(self) -> None:
        """Bring a state file an older version wrote to the shape this one reads.

        The file is a cache, so a shape that no longer fits costs the keys it is missing
        rather than the session's whole memory: a root record gains the keys added since
        it was written, and an `injected` that is no longer a mapping of lists is dropped,
        there being nothing in it to key by agent.
        """
        if not isinstance(self.data["injected"], dict) or not all(
            isinstance(value, list) for value in self.data["injected"].values()
        ):
            self.data["injected"] = {}
        for record in self.data["roots"].values():
            record.setdefault("baseline", None)
            record.setdefault("raised", [])
            record.setdefault("reported", [])

    def _load(self) -> dict:
        """The state on disk, or empty where it is missing, corrupt, or not a JSON object.

        The file is a cache the hook rewrites on every call, not a record a caller must
        trust: corruption from a partial write or a stale format costs one baseline reset,
        not a crash on every hook call thereafter.
        """
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        # ValueError covers both ways the file can be unreadable: a JSONDecodeError from
        # a partial write, and a UnicodeDecodeError from bytes that are not UTF-8 at all.
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def reset(self) -> None:
        """Forget everything, as `clear` does."""
        self.data = {"crash_reported": False, "injected": {}, "roots": {}}

    def root(self, root: Path) -> dict:
        """The record for one managed root, created empty on first sight."""
        return self.data["roots"].setdefault(
            str(root), {"baseline": None, "raised": [], "reported": []}
        )


def output(
    event_name: str, context: str, system_message: str | None = None, *, cap: bool = True
) -> dict:
    """The JSON Claude Code reads.

    `cap` guards the harness's character limit for every event except PreToolUse, whose
    caller already fits the text itself and keeps the "also binding" line whole — a blind
    slice here could otherwise cut a row's number off mid-line, naming it nowhere.
    """
    text = context[:MAX_CHARS] if cap else context
    result = {"hookSpecificOutput": {"additionalContext": text, "hookEventName": event_name}}
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


def overflow_line(rows: list[adr.Row]) -> str:
    """The "also binding" line naming rows by number and path only."""
    return "Also binding, by number and path: " + "; ".join(
        f"{row.number} [{(adr.ADR_DIR / row.filename).as_posix()}]" for row in rows
    )


def fit_bound_rows(label: str, shown: list[adr.Row], rest: list[adr.Row]) -> str:
    """Render `shown` in full and `rest` by number, trimming `shown` into `rest` to fit `MAX_CHARS`.

    Every injected number stays named even where its full row will not fit: the row the
    cap would otherwise cut is moved to the named-only line instead of being dropped
    silently mid-truncation.
    """
    shown, rest = list(shown), list(rest)

    def render() -> str:
        lines = [label, *(format_row(row) for row in shown)]
        if rest:
            lines.append(overflow_line(rest))
        return "\n".join(lines)

    text = render()
    while len(text) > MAX_CHARS and shown:
        rest.insert(0, shown.pop())
        text = render()
    if len(text) > MAX_CHARS and rest:
        # Every row has already moved to the named-only line; if the label and that line
        # still overrun together, trim the label rather than cut a number off the line
        # naming it.
        tail = overflow_line(rest)
        budget = max(MAX_CHARS - len(tail) - 1, 0)
        text = label[:budget] + "\n" + tail
    return text


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
    """Rows binding the touched paths, once per agent, fitted under the context cap."""
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
            # Keyed by root as well as number: two managed corpora in one session each
            # number their decisions from 001, and a bare number would let the first
            # corpus's 001 suppress the second's.
            key = f"{root}:{row.number}"
            if key in injected:
                continue
            injected.append(key)
            rows.append(row)
            named.extend(adr.relative_to_root(p, root) or p for p in paths)
    if not rows:
        return None
    label = LABEL.format(paths=", ".join(sorted(set(named))))
    text = fit_bound_rows(label, rows[:MAX_ROWS], rows[MAX_ROWS:])
    return output("PreToolUse", text, cap=False)


def written_adr_roots(event: dict) -> list[Path]:
    """Every managed root under which a file tool in the batch wrote an ADR, in order.

    One batch can write into two corpora, and stopping at the first would leave the
    second's index stale with nothing to say so.
    """
    roots: dict[Path, None] = {}
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
            roots[root] = None
    return list(roots)


def new_findings(state: State, root: Path, findings: list[adr.Finding]) -> list[adr.Finding]:
    """Findings not in the baseline; snapshots a baseline first where the root has none."""
    record = state.root(root)
    if record["baseline"] is None:
        record["baseline"] = sorted(f.id for f in findings)
        return []
    return [f for f in findings if f.id not in record["baseline"]]


def on_post_tool_batch(event: dict, state: State) -> dict | None:
    """Reconcile every root the batch touched; write only where it wrote; report once.

    A root the batch wrote an ADR under is regenerated; the working directory's root is
    checked without writing, since an edit through the shell is not the agent's own ADR
    edit. Each is reported under its own label, so two corpora are two sections rather
    than one list of findings with no root against them.
    """
    written = written_adr_roots(event)
    targets = [(root, True) for root in written]
    cwd_root = managed_root_for(Path(event.get("cwd", ".")))
    if cwd_root is not None and cwd_root not in written:
        targets.append((cwd_root, False))
    sections = []
    for root, write in targets:
        findings = adr.reconcile(root, write=write)
        record = state.root(root)
        fresh = [
            f for f in new_findings(state, root, findings) if f.id not in record["reported"]
        ]
        if not fresh:
            continue
        record["reported"].extend(f.id for f in fresh)
        sections.append(FINDINGS_LABEL.format(root=root) + "\n" + format_findings(fresh))
    if not sections:
        return None
    return output("PostToolBatch", "\n\n".join(sections))


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
    """Drop session files older than the retention period, and the locks left orphaned.

    A lock sidecar goes only once no session file shares its stem: while the JSON stands
    the lock is that session's, and taking it away from a live session would let two calls
    edit the file at once.
    """
    directory = state_dir / STATE_SUBDIR
    if not directory.is_dir():
        return
    for path in directory.iterdir():
        if not path.is_file():
            continue
        if path.suffix == ".lock" and path.with_suffix(".json").exists():
            continue
        try:
            if now - path.stat().st_mtime > PRUNE_AFTER_SECONDS:
                path.unlink(missing_ok=True)
        except OSError:  # a vanished file needs no action; pruning is best effort
            pass


def handle(event: dict, state_dir: Path, now: float) -> dict | None:
    """Dispatch one event. Raises on a malformed event; `main` turns that into context.

    A lock that cannot be taken within the retry budget yields no context for this call
    rather than blocking or crashing — the next matching event tries again.
    """
    handler = HANDLERS.get(event.get("hook_event_name", ""))
    if handler is None:
        return None
    if event.get("hook_event_name") == "SessionStart":
        prune(state_dir, now)
    try:
        with State(state_dir, event.get("session_id") or UNKNOWN_SESSION) as state:
            return handler(event, state)
    except StateUnavailable:
        return None


def crash_context(exc: Exception) -> str:
    """The crash line and where to look, from the exception currently being handled."""
    error = traceback.format_exc().strip().split("\n")[-1] or repr(exc)
    return CRASH.format(error=error, path=Path(__file__).resolve())


def main(stdin: str, state_dir: Path) -> str:
    """Read the event, handle it, and return the JSON text to print — or "" for nothing.

    An event that fails to parse names no session to remember against, so its crash is
    reported on every call rather than silenced after one, and never touches state; a
    crash from a parsed event is silenced once per the session it names. An event that
    parses but names no session is handled against a session named `unknown`, which is a
    shape the harness could send rather than a fault to report.
    """
    try:
        event = json.loads(stdin)
        session_id = event.get("session_id") or UNKNOWN_SESSION
    except Exception as exc:  # noqa: BLE001 — no session to report to; nothing to silence
        return json.dumps(output("SessionStart", crash_context(exc)))
    try:
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
        return json.dumps(output("SessionStart", crash_context(exc)))


if __name__ == "__main__":
    text = main(sys.stdin.read(), state_root(dict(os.environ)))
    if text:
        print(text)
    sys.exit(0)
