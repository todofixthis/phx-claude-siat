"""Tests for mutate.py.

Stdlib `unittest` rather than pytest, so the suite needs no dependency of its own
(ADR 007). Run from the repo root:

    python3 -m unittest discover -s scripts -t . -p 'test_*.py'

`mutate()` takes the file to mutate as an argument and the suite to run as another, so
these tests never chdir and never let it reach the real command: an argumentless run
would mutate this repository and recurse into the suite currently executing.
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.dev.mutate import apply_mutation, main, mutate, report

# A source file small enough to assert whole, carrying the anchor twice so a test can
# tell "replaced the first" from "replaced them all".
SOURCE = "if guard:\n    raise ValueError\nif guard:\n    pass\n"
ANCHOR = "if guard:"
REPLACEMENT = "if False:"

# Commands standing in for the suite. The killed one prints what unittest prints, since
# that text is what the verdict is parsed out of.
SURVIVES = ("python3", "-c", "import sys; sys.exit(0)")
KILLED = ("python3", "-c", "print('FAIL: test_a'); import sys; sys.exit(1)")
KILLED_TWICE = ("python3", "-c", "print('FAIL: test_a\\nERROR: test_b'); import sys; sys.exit(1)")
UNIMPORTABLE = ("python3", "-c", "print('SyntaxError: bad'); import sys; sys.exit(1)")


class SourceFileTestCase(unittest.TestCase):
    """A throwaway source file for a mutation to be applied to and restored."""

    def setUp(self) -> None:
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(directory) / "subject.py"
        self.path.write_text(SOURCE, encoding="utf-8")

    def source(self) -> str:
        """Read the subject back."""
        return self.path.read_text(encoding="utf-8")


class ApplyMutationTests(SourceFileTestCase):
    """Unit tests for ``apply_mutation()``."""

    def test_replaces_only_the_first_occurrence(self):
        """Mutating every match would disable several checks and blame one test."""
        with contextlib.redirect_stderr(io.StringIO()):
            apply_mutation(self.path, ANCHOR, REPLACEMENT)
        self.assertEqual(self.source(), f"{REPLACEMENT}\n    raise ValueError\n{ANCHOR}\n    pass\n")

    def test_returns_the_original_text_for_restoring(self):
        """The restore is held in memory, so an interrupted run leaves no stray backup."""
        with contextlib.redirect_stderr(io.StringIO()):
            original = apply_mutation(self.path, ANCHOR, REPLACEMENT)
        self.assertEqual(original, SOURCE)

    def test_rejects_an_anchor_that_is_absent(self):
        """A mistyped anchor would otherwise run the suite unmutated and report KILLED."""
        with self.assertRaises(SystemExit) as raised:
            apply_mutation(self.path, "if missing:", REPLACEMENT)
        self.assertIn("does not contain the anchor", str(raised.exception))
        self.assertEqual(self.source(), SOURCE)

    def test_warns_when_the_anchor_is_ambiguous(self):
        """Two matches mean the mutation is not the one the caller described."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            apply_mutation(self.path, ANCHOR, REPLACEMENT)
        self.assertIn("appears 2 times", err.getvalue())

    def test_says_nothing_when_the_anchor_is_unique(self):
        """The warning must mean something, so the ordinary case has to be silent."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            apply_mutation(self.path, "raise ValueError", "pass")
        self.assertEqual(err.getvalue(), "")


class ReportTests(unittest.TestCase):
    """Unit tests for ``report()``: the verdict a maintainer copies into a pull request."""

    def verdict(self, code: int, output: str) -> tuple[int, str]:
        """Return report()'s exit code with what it printed."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = report(code, output)
        return result, out.getvalue()

    def test_calls_a_passing_suite_survived(self):
        """Nothing failed without the check, so nothing was testing it."""
        result, printed = self.verdict(0, "OK")
        self.assertEqual(result, 1)
        self.assertIn("SURVIVED", printed)

    def test_calls_a_failing_suite_killed_and_names_the_test(self):
        """The pull request has to say what caught each mutation, so the name is the output."""
        result, printed = self.verdict(1, "FAIL: test_a\nFAILED (failures=1)")
        self.assertEqual(result, 0)
        self.assertIn("KILLED", printed)
        self.assertIn("test_a", printed)

    def test_names_every_failing_test(self):
        """One name would hide the rest, and a count disagreeing with the list is worse."""
        _, printed = self.verdict(1, "FAIL: test_a\nERROR: test_b\nFAILED (failures=2)")
        self.assertIn("2 failing test(s)", printed)
        self.assertIn("test_a", printed)
        self.assertIn("test_b", printed)

    def test_calls_an_uncollectable_suite_invalid(self):
        """A mutation that breaks the import proves nothing about the check it replaced."""
        result, printed = self.verdict(1, "SyntaxError: invalid syntax")
        self.assertEqual(result, 1)
        self.assertIn("INVALID", printed)


class MutateTests(SourceFileTestCase):
    """Integration tests: mutate, run, restore, report through the real entry point."""

    def run_mutate(self, command: tuple[str, ...]) -> tuple[int, str]:
        """Run mutate() against the fixture, returning its exit code and output."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = mutate(self.path, "raise ValueError", "pass", command)
        return code, out.getvalue()

    def test_restores_the_source_after_a_killed_mutation(self):
        """The next command is usually a commit, so a mutated file must not survive the run."""
        code, printed = self.run_mutate(KILLED)
        self.assertEqual(code, 0)
        self.assertIn("KILLED", printed)
        self.assertEqual(self.source(), SOURCE)

    def test_restores_the_source_after_a_surviving_mutation(self):
        """Restoration cannot depend on the verdict, which is the interesting half."""
        code, printed = self.run_mutate(SURVIVES)
        self.assertEqual(code, 1)
        self.assertIn("SURVIVED", printed)
        self.assertEqual(self.source(), SOURCE)

    def test_restores_the_source_when_the_test_command_cannot_run(self):
        """A crash between mutating and restoring is what leaves a broken check behind."""
        with self.assertRaises(FileNotFoundError):
            with contextlib.redirect_stdout(io.StringIO()):
                mutate(self.path, "raise ValueError", "pass", ("definitely-not-a-command",))
        self.assertEqual(self.source(), SOURCE)

    def test_reports_an_unimportable_mutation_as_invalid(self):
        """Told apart from SURVIVED, which would send someone hunting for a missing test."""
        code, printed = self.run_mutate(UNIMPORTABLE)
        self.assertEqual((code, "INVALID" in printed), (1, True))

    def test_leaves_the_source_alone_when_the_anchor_is_absent(self):
        """The fixture that every other case mutates must be recoverable untouched."""
        with self.assertRaises(SystemExit):
            mutate(self.path, "if missing:", REPLACEMENT, SURVIVES)
        self.assertEqual(self.source(), SOURCE)


class ArgumentTests(SourceFileTestCase):
    """Integration tests for ``main()``: the invocation the testing rule tells you to run."""

    def test_passes_the_arguments_through_to_a_verdict(self):
        """The documented command line must reach the same result as calling mutate()."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = main(
                [
                    "--file", str(self.path),
                    "--anchor", "raise ValueError",
                    "--with", "pass",
                    "--", *KILLED_TWICE,
                ]
            )
        self.assertEqual(code, 0)
        self.assertIn("2 failing test(s)", out.getvalue())
        self.assertEqual(self.source(), SOURCE)

    def test_falls_back_to_the_whole_suite_when_no_command_is_given(self):
        """The documented invocation omits the command, so the default must survive parsing."""
        with self.assertRaises(SystemExit):
            main(["--file", str(self.path), "--anchor", "if missing:", "--with", "pass"])
        self.assertEqual(self.source(), SOURCE)


if __name__ == "__main__":
    unittest.main()
