"""Tests for time_hooks.py.

`unittest` rather than pytest, so the suite needs no dependency beyond the declared ones
(ADR 035). Run from the repo root:

    uv run python -m unittest discover -s scripts -t . -p 'test_*.py'

The subject builds its plugin root on the `repo_root` its entry point requires (ADR 027),
so these tests pass a fixture root and never `chdir`. The one test that does change
directory asserts that a `chdir` *cannot* redirect the anchored root, and reads the
constant rather than calling the subject.

The integration fixtures replace every hooks.json command with `true`, `sleep` or an `rm`
of the marker, and pre-create the marker through `--data-dir` wherever the case is not
about it, so the ceiling alone decides the timing cases and no test syncs a venv.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.ci import time_hooks
from scripts.ci.time_hooks import (
    DEFAULT_EVENTS,
    EVENT_CYCLE,
    REPO_ROOT,
    STRIPPED_VARIABLES,
    TIMING_VERSION,
    VENV_MARKER,
    main,
    marker_path,
    p95,
)

# Below the slow fixture's `sleep`, so only a hook that really waits breaches it.
FIXTURE_CEILING = "0.2"
# One of each event in the cycle.
FIXTURE_EVENTS = "4"
SLOW_COMMAND = "sleep 0.3"
DROP_MARKER_COMMAND = f'rm -f "${{CLAUDE_PLUGIN_DATA}}/venvs/{TIMING_VERSION}/{VENV_MARKER}"'


class TimeHooksTestCase(unittest.TestCase):
    """A temp directory holding a fixture repo root, a hooks file and a plugin data directory."""

    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.data = self.tmp / "data"
        self.data.mkdir()
        self.hooks_file = self.tmp / "hooks.json"

    def write_hooks(self, default: str, timeout: float | None = None, **overrides: str) -> None:
        """A hooks file running `default` for every timed event, bar those in `overrides`.

        Each entry carries `timeout` where one is given, as hooks.json's do.
        """
        entry = {} if timeout is None else {"timeout": timeout}
        hooks = {
            name: [
                {
                    "hooks": [
                        entry | {"command": overrides.get(name, default), "type": "command"}
                    ]
                }
            ]
            for name in EVENT_CYCLE
        }
        self.hooks_file.write_text(json.dumps({"hooks": hooks}), encoding="utf-8")

    def mark_synced(self) -> None:
        """Create the marker a completed sync leaves, as the fixture's `true` SessionStart cannot."""
        marker = marker_path(self.data)
        marker.parent.mkdir(parents=True)
        marker.write_text("", encoding="utf-8")

    def run_main(self, *extra: str) -> tuple[int, str]:
        """Run `main` against the fixture with the fixture's flags; return its code and stdout."""
        argv = [
            "--ceiling",
            FIXTURE_CEILING,
            "--data-dir",
            str(self.data),
            "--events",
            FIXTURE_EVENTS,
            "--hooks-file",
            str(self.hooks_file),
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
        self.assertIn("after the timed events", stdout)

    def test_a_failing_hook_fails_the_timing(self):
        """A hook exiting non-zero timed its failure, not its work."""
        self.write_hooks("true", PostToolBatch="exit 3")
        self.mark_synced()
        code, stdout = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("PostToolBatch hook exited 3", stdout)

    def test_an_event_without_a_hook_fails_the_timing(self):
        """An event the hooks file has no command for would time nothing at all."""
        self.write_hooks("true")
        hooks = json.loads(self.hooks_file.read_text(encoding="utf-8"))
        del hooks["hooks"]["Stop"]
        self.hooks_file.write_text(json.dumps(hooks), encoding="utf-8")
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
