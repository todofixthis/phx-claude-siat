"""Tests for time_hooks.py.

`unittest` rather than pytest, so the suite needs no dependency beyond the declared ones
(ADR 035). Run from the repo root:

    uv run python -m unittest discover -s scripts -t . -p 'test_*.py'

The subject builds its plugin root on the `repo_root` its entry point requires (ADR 027),
so these tests pass a fixture root and never `chdir`. The one test that does change
directory asserts that a `chdir` *cannot* redirect the anchored root, and reads the
constant rather than calling the subject.

The integration fixtures replace every hooks.json command with `true`, `sleep` or an `rm`
of the marker, each SessionStart and PreToolUse command also printing the minimal context
the subject requires of them. They pre-create the marker through `--data-dir` wherever the
case is not about it, so the ceiling alone decides the timing cases and no test syncs a
venv.
"""

import contextlib
import io
import json
import re
import shlex
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.ci import time_hooks
from scripts.ci.time_hooks import (
    CRASH_PREFIX,
    DEFAULT_EVENTS,
    DEFAULT_HOOKS_FILE,
    EVENT_CYCLE,
    INJECTING_EVENTS,
    REPO_ROOT,
    SESSION_ID,
    STRIPPED_VARIABLES,
    TIMING_VERSION,
    TOUCHED_PATHS,
    VENV_MARKER,
    build_event,
    main,
    marker_path,
    p95,
)

# Below the slow fixture's `sleep`, so only a hook that really waits breaches it.
FIXTURE_CEILING = "0.2"
# One of each event in the cycle.
FIXTURE_EVENTS = "4"
SLOW_COMMAND = "sleep 0.3"
MARKER_IN_SHELL = f'"${{CLAUDE_PLUGIN_DATA}}/venvs/{TIMING_VERSION}/{VENV_MARKER}"'
DROP_MARKER_COMMAND = f"rm -f {MARKER_IN_SHELL}"
# The least a SessionStart or PreToolUse hook must print to count as having run.
INJECT_COMMAND = "printf '%s' " + shlex.quote(
    json.dumps({"hookSpecificOutput": {"additionalContext": "ok"}})
)
# What hook.py prints when it crashes: exit 0, with the crash as the context.
CRASH_COMMAND = "printf '%s' " + shlex.quote(
    json.dumps({"hookSpecificOutput": {"additionalContext": f"{CRASH_PREFIX} (boom)."}})
)
HOOK_PY = Path("skills/writing-adrs/hook.py")


class TimeHooksTestCase(unittest.TestCase):
    """A temp directory holding a fixture repo root, a hooks file and a plugin data directory."""

    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.data = self.tmp / "data"
        self.data.mkdir()
        self.hooks_file = self.tmp / "hooks.json"

    def write_hooks(
        self,
        default: str,
        timeout: float | None = None,
        path: Path | None = None,
        **overrides: str,
    ) -> dict:
        """A hooks file running `default` for every timed event, bar those in `overrides`.

        `default` is followed by INJECT_COMMAND for the events that must inject, so the
        fixture passes; an override is used verbatim. Each entry carries `timeout` where one
        is given, as hooks.json's do. Written to `path`, else the fixture's hooks file, and
        returned so a test can extend it.
        """
        entry = {} if timeout is None else {"timeout": timeout}
        hooks = {}
        for name in EVENT_CYCLE:
            command = f"{default} && {INJECT_COMMAND}" if name in INJECTING_EVENTS else default
            command = overrides.get(name, command)
            hooks[name] = [{"hooks": [entry | {"command": command, "type": "command"}]}]
        document = {"hooks": hooks}
        self.save_hooks(document, path)
        return document

    def save_hooks(self, document: dict, path: Path | None = None) -> None:
        """Write a hooks document to `path`, else the fixture's hooks file."""
        target = path or self.hooks_file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document), encoding="utf-8")

    def mark_synced(self) -> None:
        """Create the marker a completed sync leaves, as the fixture's `true` SessionStart cannot."""
        marker = marker_path(self.data)
        marker.parent.mkdir(parents=True)
        marker.write_text("", encoding="utf-8")

    def run_main(self, *extra: str, hooks_file: bool = True) -> tuple[int, str]:
        """Run `main` against the fixture with the fixture's flags; return its code and stdout.

        With `hooks_file` false, `--hooks-file` is left to its default.
        """
        argv = [
            "--ceiling",
            FIXTURE_CEILING,
            "--data-dir",
            str(self.data),
            "--events",
            FIXTURE_EVENTS,
            *(["--hooks-file", str(self.hooks_file)] if hooks_file else []),
            *extra,
        ]
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            code = main(argv, self.repo)
        return code, stdout.getvalue()


class P95Tests(unittest.TestCase):
    """Unit tests for ``p95()``."""

    def test_p95_is_nearest_rank(self):
        """Of twenty samples the 95th percentile is the nineteenth, never an interpolation."""
        self.assertEqual(p95([float(i) for i in range(1, 21)]), 19.0)

    def test_p95_of_unsorted_samples(self):
        """Samples arrive in event order, so the rank is taken over the sorted values."""
        self.assertEqual(p95([3.0, 1.0, 2.0]), 3.0)

    def test_p95_of_no_samples_raises(self):
        """An empty sample has no percentile, and must not read as a fast hook."""
        with self.assertRaises(ValueError):
            p95([])


class DefaultEventsTests(unittest.TestCase):
    """Unit tests for ``DEFAULT_EVENTS``."""

    def test_times_at_least_twenty_events_by_default(self):
        """The ceiling is defined over at least twenty timed events (docs/adr/034)."""
        self.assertGreaterEqual(DEFAULT_EVENTS, 20)


class BuildEventTests(unittest.TestCase):
    """Unit tests for ``build_event()``."""

    project = Path("/project")

    def read(self, index: int) -> dict:
        """The `Read` tool call the `index`th PreToolUse makes."""
        path = str(self.project / TOUCHED_PATHS[index])
        return {"tool_input": {"file_path": path}, "tool_name": "Read"}

    def base(self, name: str) -> dict:
        """The fields every event carries."""
        return {"cwd": str(self.project), "hook_event_name": name, "session_id": SESSION_ID}

    def test_cold_session_start(self):
        """The cold SessionStart is a startup, so hook.py snapshots the session's baseline."""
        expected = self.base("SessionStart") | {"source": "startup"}
        self.assertEqual(build_event("SessionStart", self.project, 0, cold=True), expected)

    def test_timed_session_start(self):
        """A timed SessionStart is a compact, which clears what the session has injected."""
        expected = self.base("SessionStart") | {"source": "compact"}
        self.assertEqual(build_event("SessionStart", self.project, 0, cold=False), expected)

    def test_pre_tool_use(self):
        """A PreToolUse is a Read of the indexed path, joined to the project directory."""
        expected = self.base("PreToolUse") | self.read(1)
        self.assertEqual(build_event("PreToolUse", self.project, 1, cold=False), expected)

    def test_post_tool_batch(self):
        """A PostToolBatch carries the Read of the indexed path as its one tool call."""
        expected = self.base("PostToolBatch") | {"tool_calls": [self.read(2)]}
        self.assertEqual(build_event("PostToolBatch", self.project, 2, cold=False), expected)

    def test_stop(self):
        """A Stop carries only the fields every event does."""
        self.assertEqual(build_event("Stop", self.project, 0, cold=False), self.base("Stop"))

    def test_the_index_cycles_the_touched_paths(self):
        """Past the last touched path the reads start again from the first."""
        wrapped = build_event("PreToolUse", self.project, len(TOUCHED_PATHS), cold=False)
        self.assertEqual(wrapped, self.base("PreToolUse") | self.read(0))

    def test_every_touched_path_exists(self):
        """A path missing from the repo would be no first touch of anything a decision binds."""
        missing = [str(path) for path in TOUCHED_PATHS if not (REPO_ROOT / path).exists()]
        self.assertEqual(missing, [])

    def test_the_real_matchers_accept_what_is_sent(self):
        """Each real hooks.json matcher fires for the event built, or the timing skips a hook."""
        hooks = json.loads((REPO_ROOT / DEFAULT_HOOKS_FILE).read_text(encoding="utf-8"))
        matched_fields = {"PreToolUse": "tool_name", "SessionStart": "source"}
        for name in EVENT_CYCLE:
            # The cold SessionStart and the timed ones send different sources; both must match.
            for cold in (True, False):
                event = build_event(name, REPO_ROOT, 0, cold=cold)
                for block in hooks["hooks"][name]:
                    if "matcher" not in block:
                        continue
                    with self.subTest(event=name, cold=cold):
                        self.assertIn(name, matched_fields)
                        field = event[matched_fields[name]]
                        self.assertTrue(re.fullmatch(block["matcher"], field), field)


class CrashPrefixTests(unittest.TestCase):
    """Unit tests for ``CRASH_PREFIX``: the mirror of hook.py's crash text."""

    def test_hook_py_still_opens_its_crash_text_with_the_prefix(self):
        """A reworded crash text would let a crashing hook pass as one that injected."""
        source = (REPO_ROOT / HOOK_PY).read_text(encoding="utf-8")
        self.assertIn(f'CRASH = "{CRASH_PREFIX} ', source)


class MainTests(TimeHooksTestCase):
    """Integration tests: the exit code and table ``main()`` reaches through the fixture hooks."""

    def test_a_fast_hook_passes(self):
        """Hooks well inside the ceiling, with the marker in place, pass."""
        self.write_hooks("true")
        self.mark_synced()
        code, stdout = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("✅ Overall p95", stdout)

    def test_a_slow_hook_fails_the_ceiling(self):
        """Hooks slower than the ceiling fail it."""
        self.write_hooks(SLOW_COMMAND)
        self.mark_synced()
        code, stdout = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn(f"exceeds the {FIXTURE_CEILING} s ceiling", stdout)

    def test_an_unsynced_venv_fails_the_timing(self):
        """No marker after the cold SessionStart means every hook would time its gate alone."""
        self.write_hooks("true")
        code, stdout = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("after the cold SessionStart", stdout)

    def test_a_marker_lost_during_the_run_fails_the_timing(self):
        """A marker gone by the end means the later events timed their gate alone."""
        self.write_hooks("true", Stop=DROP_MARKER_COMMAND)
        self.mark_synced()
        code, stdout = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("after Stop (timed event 4 of 4)", stdout)

    def test_a_marker_lost_and_restored_mid_run_fails_the_timing(self):
        """A re-sync that unmarks the venv for a while fails, though a later one restores it."""
        counter = '"${CLAUDE_PLUGIN_DATA}/session-starts"'
        # Call 1 is the cold run; the first timed call unmarks, the second marks again.
        session_start = (
            f"n=$(($(cat {counter} 2>/dev/null || echo 0) + 1)); echo $n > {counter}; "
            f"case $n in 2) rm -f {MARKER_IN_SHELL} ;; 3) : > {MARKER_IN_SHELL} ;; esac; "
            f"{INJECT_COMMAND}"
        )
        gated = f"if [ -f {MARKER_IN_SHELL} ]; then {INJECT_COMMAND}; fi"
        self.write_hooks(
            "true",
            PostToolBatch=gated,
            PreToolUse=gated,
            SessionStart=session_start,
            Stop=gated,
        )
        self.mark_synced()
        code, stdout = self.run_main("--events", "8")
        self.assertEqual(code, 1)
        self.assertIn("after SessionStart (timed event 1 of 8)", stdout)

    def test_a_silent_pre_tool_use_fails_the_timing(self):
        """A first touch of a scoped path that injects nothing timed only the marker gate."""
        self.write_hooks("true", PreToolUse="true")
        self.mark_synced()
        code, stdout = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("PreToolUse (timed event 2 of 4) printed no additionalContext", stdout)

    def test_a_crashing_hook_fails_the_timing(self):
        """hook.py exits 0 when it crashes, so its crash text must not pass as an injection."""
        self.write_hooks("true", PreToolUse=CRASH_COMMAND)
        self.mark_synced()
        code, stdout = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("PreToolUse (timed event 2 of 4) reported a hook.py crash", stdout)

    def test_output_that_is_not_hook_json_fails_the_timing(self):
        """Stray text on stdout is not context Claude Code could read, so the hook misfired."""
        self.write_hooks("true", PostToolBatch="echo not json")
        self.mark_synced()
        code, stdout = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("PostToolBatch (timed event 3 of 4) printed no hook JSON", stdout)

    def test_a_crash_in_the_cold_session_start_fails_the_timing(self):
        """A cold SessionStart whose hook.py crashed proves nothing about the venv it synced."""
        counter = '"${CLAUDE_PLUGIN_DATA}/session-starts"'
        session_start = (
            f"if [ -f {counter} ]; then {INJECT_COMMAND}; "
            f"else : > {counter}; {CRASH_COMMAND}; fi"
        )
        self.write_hooks("true", SessionStart=session_start)
        self.mark_synced()
        code, stdout = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("SessionStart (cold) reported a hook.py crash", stdout)

    def test_a_failing_hook_fails_the_timing(self):
        """A hook exiting non-zero timed its failure, not its work."""
        self.write_hooks("true", PostToolBatch="exit 3")
        self.mark_synced()
        code, stdout = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("PostToolBatch hook exited 3", stdout)

    def test_every_command_an_event_registers_runs(self):
        """A second block for one event runs too, so its failure is not hidden by the first."""
        document = self.write_hooks("true")
        document["hooks"]["Stop"].append({"hooks": [{"command": "exit 4", "type": "command"}]})
        self.save_hooks(document)
        self.mark_synced()
        code, stdout = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("Stop hook exited 4", stdout)

    def test_an_event_the_timer_does_not_send_is_ignored(self):
        """Only the timed events' hooks run; one registered for any other event is not timed."""
        document = self.write_hooks("true")
        document["hooks"]["SubagentStop"] = [
            {"hooks": [{"command": "exit 9", "type": "command"}]}
        ]
        self.save_hooks(document)
        self.mark_synced()
        # One past the cycle, so a subject running every registered event would reach it.
        code, _ = self.run_main("--events", str(len(EVENT_CYCLE) + 1))
        self.assertEqual(code, 0)

    def test_each_hook_receives_its_own_event(self):
        """The stdin a hook reads names the event it was registered for."""
        overrides = {
            name: f'grep -q \'"hook_event_name": "{name}"\''
            + (f" && {INJECT_COMMAND}" if name in INJECTING_EVENTS else "")
            for name in EVENT_CYCLE
        }
        self.write_hooks("true", **overrides)
        self.mark_synced()
        code, stdout = self.run_main()
        self.assertEqual(code, 0, stdout)

    def test_the_session_opens_with_startup_then_compacts(self):
        """Only the cold SessionStart is a startup; each timed one compacts to re-inject."""
        log = self.tmp / "sources"
        session_start = f'grep -o \'"source": "[a-z]*"\' >> {log} && {INJECT_COMMAND}'
        self.write_hooks("true", SessionStart=session_start)
        self.mark_synced()
        code, stdout = self.run_main("--events", "8")
        self.assertEqual(code, 0, stdout)
        sources = [
            json.loads("{" + line + "}")["source"] for line in log.read_text().splitlines()
        ]
        self.assertEqual(sources, ["startup", "compact", "compact"])

    def test_a_relative_hooks_file_resolves_against_the_repo_root(self):
        """The default hooks file is read from the root given, never the working directory."""
        self.write_hooks("true", path=self.repo / DEFAULT_HOOKS_FILE, Stop="exit 7")
        self.mark_synced()
        code, stdout = self.run_main(hooks_file=False)
        self.assertEqual(code, 1)
        self.assertIn("Stop hook exited 7", stdout)

    def test_an_event_without_a_hook_fails_the_timing(self):
        """An event the hooks file has no command for would time nothing at all."""
        document = self.write_hooks("true")
        del document["hooks"]["Stop"]
        self.save_hooks(document)
        self.mark_synced()
        code, stdout = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("no command for Stop", stdout)

    def test_a_hook_past_its_timeout_fails_the_timing(self):
        """A hook killed at its hooks.json timeout never finished, so its time is no sample."""
        self.write_hooks("true", timeout=0.1, PreToolUse=SLOW_COMMAND)
        self.mark_synced()
        code, stdout = self.run_main("--ceiling", "10")
        self.assertEqual(code, 1)
        self.assertIn("PreToolUse hook ran past its 0.1 s timeout", stdout)

    def test_hooks_never_see_a_redirecting_variable(self):
        """A venv or plugin path leaked from `uv run` or a session must not reach a hook."""
        # The subject sets the CLAUDE_ variables itself, so only these two can show a leak.
        self.write_hooks('[ -z "${UV_PROJECT_ENVIRONMENT+x}${VIRTUAL_ENV+x}" ]')
        self.mark_synced()
        leaked = {name: "/nowhere" for name in STRIPPED_VARIABLES}
        with mock.patch.dict("os.environ", leaked):
            code, _ = self.run_main()
        self.assertEqual(code, 0)

    def test_zero_events_is_refused(self):
        """A run timing no events has no p95 to hold against the ceiling."""
        self.write_hooks("true")
        self.mark_synced()
        with self.assertRaises(SystemExit) as raised:
            self.run_main("--events", "0")
        self.assertEqual(raised.exception.code, 2)

    def test_prints_a_count_per_event_and_overall(self):
        """The table counts each timed event, the untimed cold SessionStart excluded."""
        self.write_hooks("true")
        self.mark_synced()
        _, stdout = self.run_main("--events", "6")
        counts = {
            line.split()[0]: int(line.split()[1])
            for line in stdout.splitlines()
            if line.split() and line.split()[0] in (*EVENT_CYCLE, "overall")
        }
        self.assertEqual(
            counts,
            {"PostToolBatch": 1, "PreToolUse": 2, "SessionStart": 2, "Stop": 1, "overall": 6},
        )


class RepoRootTests(unittest.TestCase):
    """Unit tests for ``REPO_ROOT``: the one path the module resolves for itself."""

    def test_chdir_cannot_redirect_the_anchor(self):
        """The anchor names the tree the module ships in, wherever the caller stands."""
        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            self.assertTrue(REPO_ROOT.is_absolute())
            self.assertFalse(REPO_ROOT.is_relative_to(directory))

    def test_root_is_this_repository(self):
        """The anchor has to reach the real repo, not merely some absolute directory."""
        self.assertTrue(Path(__file__).resolve().is_relative_to(REPO_ROOT))
        self.assertTrue((REPO_ROOT / time_hooks.DEFAULT_HOOKS_FILE).is_file())


if __name__ == "__main__":
    unittest.main()
