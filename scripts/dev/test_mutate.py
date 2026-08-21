"""Tests for mutate.py.

Stdlib `unittest` rather than pytest, so the suite needs no dependency of its own
(ADR 007). Run from the repo root:

    python3 -m unittest discover -s scripts -t . -p 'test_*.py'

`mutate()` takes the file to mutate as an argument and the suite to run as another, so
these tests never chdir and never let it reach the real command: an argumentless run
would mutate this repository and recurse into the suite currently executing.

The stand-in commands below write to **stderr** in the shape unittest really produces —
qualified case names, a docstring line, a traceback. unittest puts its whole result block
on stderr and leaves stdout empty, so a fixture that prints to stdout exercises none of
the parsing this module exists to do.
"""

import contextlib
import io
import os
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from scripts.dev.mutate import (
    DEFAULT_TEST_COMMAND,
    MEMORY_LIMIT_BYTES,
    RECURSION_FLAG,
    apply_mutation,
    find_occurrences,
    guard_against_recursion,
    main,
    mutate,
    report,
    resolve_command,
    run_tests,
)

# A source file small enough to assert whole, carrying the anchor twice so a test can
# tell "replaced the first" from "replaced them all".
SOURCE = "if guard:\n    raise ValueError\nif guard:\n    pass\n"
ANCHOR = "if guard:"
REPLACEMENT = "if False:"

# What unittest actually emits: the case name qualified by module and class, the
# docstring beneath it, and a traceback. All on stderr.
REAL_FAILURE = (
    "FAIL: test_thing_fails (test_demo.DemoTests.test_thing_fails)\n"
    "A scenario.\n"
    "----------------------------------------------------------------------\n"
    "Traceback (most recent call last):\n"
    '  File "test_demo.py", line 5, in test_thing_fails\n'
    "    self.assertEqual(1, 2)\n"
    "AssertionError: 1 != 2\n"
    "\n"
    "Ran 1 test in 0.001s\n"
    "\n"
    "FAILED (failures=1)\n"
)
QUALIFIED_NAME = "test_thing_fails (test_demo.DemoTests.test_thing_fails)"


def emitting(text: str, code: int) -> tuple[str, ...]:
    """A command writing `text` to stderr and exiting with `code`, as unittest does."""
    return ("python3", "-c", f"import sys; sys.stderr.write({text!r}); sys.exit({code})")


PASSES = emitting("OK\n", 0)
FAILS = emitting(REAL_FAILURE, 1)
FAILS_TWICE = emitting(
    "FAIL: test_a (m.C.test_a)\nERROR: test_b (m.C.test_b)\nFAILED (failures=2)\n", 1
)
UNIMPORTABLE_OUTPUT = (
    "ERROR: test_demo (unittest.loader._FailedTest.test_demo)\n"
    "ImportError: Failed to import test module: test_demo\n"
)
UNIMPORTABLE = emitting(UNIMPORTABLE_OUTPUT, 1)

# A suite that fails *because a test raised ImportError* — caught, not uncollectable.
IMPORT_ERROR_OUTPUT = (
    "ERROR: test_optional (m.C.test_optional)\nImportError: no such optional dependency\n"
)
RAISES_IMPORT_ERROR = emitting(IMPORT_ERROR_OUTPUT, 1)


class SourceFileTestCase(unittest.TestCase):
    """A throwaway source file for a mutation to be applied to and restored."""

    def setUp(self) -> None:
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(directory) / "subject.py"
        self.path.write_bytes(SOURCE.encode("utf-8"))

    def source(self) -> str:
        """Read the subject back as text."""
        return self.path.read_text(encoding="utf-8")


class FindOccurrencesTests(unittest.TestCase):
    """Unit tests for ``find_occurrences()``."""

    def test_returns_the_index_of_each_match(self):
        """The caller indexes into this list, so the positions must be the real ones."""
        self.assertEqual(find_occurrences("abcabc", "abc"), [0, 3])

    def test_does_not_count_overlaps(self):
        """`count()` skips overlaps, and a disagreement would misnumber the occurrences."""
        self.assertEqual(find_occurrences("aaaa", "aa"), [0, 2])

    def test_returns_nothing_when_absent(self):
        """The empty list is what the caller turns into its mistyped-anchor error."""
        self.assertEqual(find_occurrences("abc", "xyz"), [])

    def test_returns_nothing_for_an_empty_needle(self):
        """`find` matches it everywhere and advances by zero, so the search would not end."""
        self.assertEqual(find_occurrences("abc", ""), [])


class ApplyMutationTests(SourceFileTestCase):
    """Unit tests for ``apply_mutation()``."""

    def test_replaces_the_one_match(self):
        """The artefact is asserted entire: a stray second replacement would show here."""
        apply_mutation(self.path, "raise ValueError", "pass")
        self.assertEqual(self.source(), f"{ANCHOR}\n    pass\n{ANCHOR}\n    pass\n")

    def test_replaces_a_match_identified_by_surrounding_lines(self):
        """Disambiguating by context is the whole alternative to an occurrence index."""
        apply_mutation(self.path, f"{ANCHOR}\n    pass\n", "if False:\n    pass\n")
        self.assertEqual(self.source(), f"{ANCHOR}\n    raise ValueError\nif False:\n    pass\n")

    def test_returns_the_original_bytes_for_restoring(self):
        """The restore is held in memory, so an interrupted run leaves no stray backup."""
        original = apply_mutation(self.path, "raise ValueError", "pass")
        self.assertEqual(original, SOURCE.encode("utf-8"))

    def test_rejects_an_ambiguous_anchor(self):
        """Mutating the first would test a check the caller never named, and still report."""
        with self.assertRaises(SystemExit) as raised:
            apply_mutation(self.path, ANCHOR, REPLACEMENT)
        self.assertIn("appears 2 times", str(raised.exception))
        self.assertIn("surrounding lines", str(raised.exception))
        self.assertEqual(self.source(), SOURCE)

    def test_rejects_an_anchor_that_is_absent(self):
        """A mistyped anchor would otherwise run the suite unmutated and report CAUGHT."""
        with self.assertRaises(SystemExit) as raised:
            apply_mutation(self.path, "if missing:", REPLACEMENT)
        self.assertIn("does not contain the anchor", str(raised.exception))
        self.assertEqual(self.source(), SOURCE)

    def test_rejects_an_empty_anchor(self):
        """An empty needle matches at every position and would insert at the file's head."""
        with self.assertRaises(SystemExit) as raised:
            apply_mutation(self.path, "", REPLACEMENT)
        self.assertIn("--anchor is empty", str(raised.exception))

    def test_rejects_a_replacement_identical_to_the_anchor(self):
        """A no-op mutation always reports MISSED, sending someone after a test that exists."""
        with self.assertRaises(SystemExit) as raised:
            apply_mutation(self.path, ANCHOR, ANCHOR)
        self.assertIn("identical", str(raised.exception))

    def test_rejects_a_path_that_is_not_a_file(self):
        """A mistyped path should read like the other refusals, not a bare traceback."""
        with self.assertRaises(SystemExit) as raised:
            apply_mutation(self.path.parent / "absent.py", ANCHOR, REPLACEMENT)
        self.assertIn("is not a file", str(raised.exception))

    def test_says_nothing_when_the_anchor_is_unique(self):
        """A unique anchor is the ordinary case and must not print advice nobody needs."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            apply_mutation(self.path, "raise ValueError", "pass")
        self.assertEqual(err.getvalue(), "")

    def test_preserves_line_endings_it_did_not_touch(self):
        """Text mode would rewrite every CRLF, so restoring would not return the file."""
        self.path.write_bytes(b"if guard:\r\n    raise ValueError\r\n")
        original = apply_mutation(self.path, "raise ValueError", "pass")
        self.assertEqual(self.path.read_bytes(), b"if guard:\r\n    pass\r\n")
        self.assertEqual(original, b"if guard:\r\n    raise ValueError\r\n")

    def test_treats_the_anchor_as_literal_text(self):
        """`str.replace`, not a regex — a later refactor to `re.sub` would break this."""
        self.path.write_bytes(b"value = a.*b\n")
        apply_mutation(self.path, "a.*b", "c")
        self.assertEqual(self.source(), "value = c\n")


class RunTestsTests(unittest.TestCase):
    """Unit tests for ``run_tests()``."""

    def test_returns_the_exit_code(self):
        """The verdict turns on this code, so a swallowed failure reads as a pass."""
        code, _ = run_tests(PASSES)
        self.assertEqual(code, 0)

    def test_captures_stderr_where_unittest_writes_its_results(self):
        """unittest leaves stdout empty; reading it alone reports every run as catching none."""
        _, output = run_tests(FAILS)
        self.assertIn(QUALIFIED_NAME, output)

    def test_captures_stdout_as_well(self):
        """A runner that reports on stdout must not be invisible to the parsing."""
        _, output = run_tests(("python3", "-c", "print('on stdout')"))
        self.assertIn("on stdout", output)

    def test_stops_a_suite_that_will_not_finish(self):
        """Disabling a loop guard is a normal mutation, and the suite then never returns."""
        code, output = run_tests(("python3", "-c", "import time; time.sleep(30)"), timeout=1)
        self.assertEqual(code, -1)
        self.assertIn("timed out", output)

    def test_marks_the_child_as_being_inside_a_run(self):
        """Without the flag reaching the child, the recursion guard can never fire."""
        _, output = run_tests(
            ("python3", "-c", f"import os; print(os.environ.get({RECURSION_FLAG!r}))")
        )
        self.assertIn("1", output)

    def test_caps_the_memory_the_suite_may_take(self):
        """Unbounded, a runaway mutation ends in an OOM kill — the one signal restore misses.

        The child reports its own limit rather than allocating: a test that proved the cap
        by exhausting memory would, with the cap mutated away, do exactly the damage the
        cap prevents.
        """
        _, output = run_tests(
            ("python3", "-c", "import resource; print(resource.getrlimit(resource.RLIMIT_AS)[0])")
        )
        self.assertIn(str(MEMORY_LIMIT_BYTES), output)


class GuardAgainstRecursionTests(unittest.TestCase):
    """Unit tests for ``guard_against_recursion()``.

    Tested here rather than through ``run_tests``, because a test that reaches the
    subprocess to prove the guard would, with the guard mutated away, run the whole
    suite from inside the suite — the fork bomb the guard exists to prevent.
    """

    def test_refuses_the_default_command_inside_a_run(self):
        """The default is this suite, so a nested one spawns copies without end."""
        with unittest.mock.patch.dict(os.environ, {RECURSION_FLAG: "1"}):
            with self.assertRaises(SystemExit) as raised:
                guard_against_recursion(DEFAULT_TEST_COMMAND)
        self.assertIn("refusing to run the whole suite", str(raised.exception))

    def test_allows_the_default_command_outside_a_run(self):
        """The ordinary invocation is the default command, and must not be refused."""
        with unittest.mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(guard_against_recursion(DEFAULT_TEST_COMMAND))

    def test_allows_an_explicit_command_inside_a_run(self):
        """These tests pass harmless commands from inside exactly this situation."""
        with unittest.mock.patch.dict(os.environ, {RECURSION_FLAG: "1"}):
            self.assertIsNone(guard_against_recursion(PASSES))


class ResolveCommandTests(unittest.TestCase):
    """Unit tests for ``resolve_command()``."""

    def test_falls_back_to_the_whole_suite(self):
        """The documented invocation names no command, so the default must survive parsing."""
        self.assertEqual(resolve_command([]), DEFAULT_TEST_COMMAND)

    def test_drops_the_separator_argparse_leaves_in_front(self):
        """REMAINDER keeps the `--`, which would reach the shell as a command name."""
        self.assertEqual(resolve_command(["--", "pytest"]), ("pytest",))

    def test_keeps_a_later_separator_for_the_command_it_belongs_to(self):
        """`pytest -- path` passes its own separator through; only the first is ours."""
        self.assertEqual(resolve_command(["--", "pytest", "--", "tests"]), ("pytest", "--", "tests"))


class ReportTests(unittest.TestCase):
    """Unit tests for ``report()``: the verdict a maintainer copies into a pull request."""

    def verdict(self, code: int, output: str) -> tuple[int, str]:
        """Return report()'s exit code with what it printed."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = report(code, output)
        return result, out.getvalue()

    def test_calls_a_passing_suite_missed(self):
        """Nothing failed without the check, so nothing was testing it."""
        result, printed = self.verdict(0, "OK")
        self.assertEqual(result, 1)
        self.assertIn("MISSED", printed)

    def test_calls_a_failing_suite_caught(self):
        """The exit code is what a scripted sequence of mutations keys on."""
        result, printed = self.verdict(1, REAL_FAILURE)
        self.assertEqual(result, 0)
        self.assertIn("CAUGHT", printed)

    def test_names_the_failing_case_in_full(self):
        """A bare method name cannot tell two classes apart in a pull request."""
        _, printed = self.verdict(1, REAL_FAILURE)
        self.assertIn(QUALIFIED_NAME, printed)

    def test_names_every_failing_test(self):
        """One name would hide the rest, and a count disagreeing with the list is worse."""
        _, printed = self.verdict(1, "FAIL: test_a (m.C.test_a)\nERROR: test_b (m.C.test_b)\n")
        self.assertIn("2 failing test(s)", printed)
        self.assertIn("test_a (m.C.test_a)", printed)
        self.assertIn("test_b (m.C.test_b)", printed)

    def test_will_not_call_an_unattributable_failure_caught(self):
        """A killed or crashed suite would otherwise report the check as covered by nothing."""
        result, printed = self.verdict(1, "Killed\n")
        self.assertEqual(result, 1)
        self.assertIn("UNKNOWN", printed)

    def test_calls_an_uncollectable_suite_invalid(self):
        """A mutation that breaks the import proves nothing about the check it replaced."""
        result, printed = self.verdict(1, UNIMPORTABLE_OUTPUT)
        self.assertEqual(result, 1)
        self.assertIn("INVALID", printed)

    def test_does_not_call_a_test_raising_importerror_invalid(self):
        """Matching the bare exception would invert the exit code on a genuine catch."""
        result, printed = self.verdict(1, IMPORT_ERROR_OUTPUT)
        self.assertEqual(result, 0)
        self.assertIn("CAUGHT", printed)


class MutateTests(SourceFileTestCase):
    """Integration tests: mutate, run, restore, report through the real entry point."""

    def run_mutate(self, command: tuple[str, ...]) -> tuple[int, str]:
        """Run mutate() against the fixture, returning its exit code and output."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = mutate(self.path, "raise ValueError", "pass", command)
        return code, out.getvalue()

    def test_restores_the_source_after_a_caught_mutation(self):
        """The next command is usually a commit, so a mutated file must not survive the run."""
        code, printed = self.run_mutate(FAILS)
        self.assertEqual(code, 0)
        self.assertIn("CAUGHT", printed)
        self.assertEqual(self.source(), SOURCE)

    def test_restores_the_source_after_a_missed_mutation(self):
        """Restoration cannot depend on the verdict, which is the interesting half."""
        code, printed = self.run_mutate(PASSES)
        self.assertEqual(code, 1)
        self.assertIn("MISSED", printed)
        self.assertEqual(self.source(), SOURCE)

    def test_restores_byte_for_byte(self):
        """Text-mode restoration would return a CRLF file with every line ending changed."""
        self.path.write_bytes(b"if guard:\r\n    raise ValueError\r\n")
        self.run_mutate(PASSES)
        self.assertEqual(self.path.read_bytes(), b"if guard:\r\n    raise ValueError\r\n")

    def test_restores_the_source_when_the_test_command_cannot_run(self):
        """A crash between mutating and restoring is what leaves a broken check behind."""
        with self.assertRaises(FileNotFoundError):
            with contextlib.redirect_stdout(io.StringIO()):
                mutate(self.path, "raise ValueError", "pass", ("definitely-not-a-command",))
        self.assertEqual(self.source(), SOURCE)

    def test_reports_an_unimportable_mutation_as_invalid(self):
        """Told apart from MISSED, which would send someone hunting for a missing test."""
        code, printed = self.run_mutate(UNIMPORTABLE)
        self.assertEqual(code, 1)
        self.assertIn("INVALID", printed)

    def test_reports_a_test_raising_importerror_as_caught(self):
        """The suite failed for a real reason; calling that invalid inverts the exit code."""
        code, printed = self.run_mutate(RAISES_IMPORT_ERROR)
        self.assertEqual(code, 0)
        self.assertIn("CAUGHT", printed)

    def test_leaves_the_source_alone_when_the_anchor_is_absent(self):
        """The fixture that every other case mutates must be recoverable untouched."""
        with self.assertRaises(SystemExit):
            mutate(self.path, "if missing:", REPLACEMENT, PASSES)
        self.assertEqual(self.source(), SOURCE)


class MainTests(SourceFileTestCase):
    """Integration tests for ``main()``: the invocation the testing rule tells you to run."""

    def run_main(self, *extra: str) -> tuple[int, str]:
        """Run main() against the fixture with the documented flags, plus `extra`."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = main(
                ["--file", str(self.path), "--anchor", "raise ValueError", "--with", "pass", *extra]
            )
        return code, out.getvalue()

    def test_passes_the_arguments_through_to_a_verdict(self):
        """The documented command line must reach the same result as calling mutate()."""
        code, printed = self.run_main("--", *FAILS_TWICE)
        self.assertEqual(code, 0)
        self.assertIn("2 failing test(s)", printed)
        self.assertEqual(self.source(), SOURCE)

    def test_refuses_an_ambiguous_anchor_from_the_command_line(self):
        """The refusal must reach the caller, not just the function it guards.

        The harmless command is not decoration. Without it this test relies on the guard
        raising before the command is chosen, so breaking that guard sends the run to
        `DEFAULT_TEST_COMMAND` — the whole suite, which contains this test, which spawns
        the suite again. A test must not fork-bomb the machine when its subject breaks.
        """
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(
                    ["--file", str(self.path), "--anchor", ANCHOR, "--with", REPLACEMENT, "--"]
                    + list(PASSES)
                )
        self.assertIn("appears 2 times", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
