"""Disable one check in place, run the suite, and report whether a test caught it.

Run from the repo root (ADR 011):

    python3 -m scripts.dev.mutate --file scripts/adr/generate_index.py \
        --anchor 'if not target.exists():' --with 'if False:'

Exits 0 when the mutation is CAUGHT (some test failed, so the check is guarded) and 1
when it is MISSED (every test passed without it, so nothing tests it). That mapping lets
a sequence of mutations be scripted and checked by exit code rather than read by eye.

`.agents/rules/testing.md` requires this after adding a check. Doing it by hand is four
shell lines that must not be got wrong: the source is restored in a `finally` and on the
signals a shell sends, because a mutated file left behind is the input to whatever runs
next, and that is usually a commit. A hard kill — SIGKILL, a segfault — cannot be caught
from inside the process; recovery is `git restore <file>`, and since the mutation is one
anchor replaced once, `git diff` shows exactly what to undo.

Stdlib-only, like everything under scripts/ (ADR 007).
"""

import argparse
import os
import re
import resource
import signal
import subprocess
import sys
from pathlib import Path

# A suite that has not finished by now is not going to: the mutation broke a loop guard
# or an exit condition. Generous enough that a slow real suite still reports honestly.
DEFAULT_TIMEOUT_SECONDS = 300.0

# Enough for any suite here, and far below what it takes to trouble the machine.
MEMORY_LIMIT_BYTES = 2 * 1024 * 1024 * 1024

# Set in the child's environment; its presence means a mutation run is already in
# progress, and a nested one would be this module testing itself recursively.
RECURSION_FLAG = "MUTATE_IN_PROGRESS"

DEFAULT_TEST_COMMAND = (
    "python3",
    "-m",
    "unittest",
    "discover",
    "-s",
    "scripts",
    "-t",
    ".",
    "-p",
    "test_*.py",
)

# Restored on the signals a shell or a timeout sends. SIGINT already arrives as
# KeyboardInterrupt, which the `finally` handles.
RESTORE_SIGNALS = (signal.SIGTERM, signal.SIGHUP)

# unittest names each failing case on its own line. The whole identity is captured, not
# the leading word: two failures can share a method name across classes, and the
# maintainer pasting this into a pull request needs to know which one caught the change.
RE_FAILING_TEST = re.compile(r"^(?:FAIL|ERROR): (.+)$", re.MULTILINE)

# unittest's own wording when a module will not import, which is what a mutation breaking
# the syntax produces. Matching the bare exception name instead would call a *passing*
# mutation invalid whenever a test legitimately raises ImportError.
RE_COLLECTION_ERROR = re.compile(r"Failed to import test module")


def find_occurrences(haystack: str, needle: str) -> list[int]:
    """Return the start index of each non-overlapping occurrence of `needle`.

    An empty needle returns nothing rather than looping: `find` matches it at every
    position and advances by its length, so the search would never terminate. The
    caller rejects one with a better message, and this keeps that guard from being the
    only thing standing between a typo and a hang.
    """
    if not needle:
        return []
    positions = []
    start = haystack.find(needle)
    while start != -1:
        positions.append(start)
        start = haystack.find(needle, start + len(needle))
    return positions


def apply_mutation(path: Path, anchor: str, replacement: str) -> bytes:
    """Replace the anchor, which must match exactly once, returning the original bytes.

    Uniqueness is required rather than offering an index to pick between matches, for
    the reason the edit tools take the same line: an index is derived from a count the
    caller made separately, so miscounting mutates a different check and the run still
    prints a plausible verdict. An ambiguous anchor fails instead, and the caller adds
    surrounding lines until it identifies one place.

    Bytes rather than text, so the restore is exact: reading and writing as text
    translates line endings, which would silently rewrite every line of a CRLF file
    the tool promised only to put back.
    """
    if not anchor:
        raise SystemExit("Error: --anchor is empty; give the exact text to replace")
    if anchor == replacement:
        raise SystemExit(
            "Error: --anchor and --with are identical, so the run would report MISSED "
            "against a source that never changed"
        )
    if not path.is_file():
        raise SystemExit(f"Error: {path} is not a file")

    original = path.read_bytes()
    text = original.decode("utf-8")
    positions = find_occurrences(text, anchor)
    if not positions:
        raise SystemExit(
            f"Error: {path} does not contain the anchor; copy it exactly from the source, "
            "including indentation"
        )
    if len(positions) > 1:
        raise SystemExit(
            f"Error: the anchor appears {len(positions)} times in {path}; extend it with "
            "surrounding lines until it identifies one place, as you would for an edit"
        )

    index = positions[0]
    mutated = text[:index] + replacement + text[index + len(anchor) :]
    path.write_bytes(mutated.encode("utf-8"))
    return original


def guard_against_recursion(command: tuple[str, ...]) -> None:
    """Refuse to run the *whole suite* from inside a mutation run.

    The default command is this repository's suite, which includes the tests for this
    module. If one of those reaches `run_tests` with the default — because a guard it
    relied on has just been mutated away — the suite spawns the suite, and each copy
    spawns more. That is a fork bomb produced by testing a guard, so it is stopped here
    rather than left to every test to remember.

    Only the default is refused. An explicit command is a deliberate choice, and the
    tests in this module pass harmless ones from inside exactly this situation.
    """
    if command == DEFAULT_TEST_COMMAND and os.environ.get(RECURSION_FLAG):
        raise SystemExit(
            "Error: refusing to run the whole suite from inside a mutation run; pass an "
            "explicit command after `--` if this is deliberate"
        )


def bound_child() -> None:
    """Cap the child's address space, so a runaway mutation cannot take the machine.

    Mutating this away reports MISSED rather than CAUGHT, and the test is still worth
    keeping. A mutation run is itself capped, so its child inherits the same limit and a
    grandchild reports it either way — the effect is unobservable from inside an already
    capped process. Run standalone the test does catch removal, and the cap was verified
    directly: a child asking for 3 GiB raises MemoryError instead of taking the host.
    """
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))


def run_tests(command: tuple[str, ...], timeout: float = DEFAULT_TIMEOUT_SECONDS) -> tuple[int, str]:
    """Run the suite, returning its exit code and both streams joined.

    unittest writes its whole result block to stderr, so a caller reading stdout alone
    sees nothing and reports every run as having caught no tests.

    Bounded in both time and memory, because the mutation being tested is by definition
    a deliberate breakage: disabling a loop guard is a normal thing to try, and the
    result is a suite that never returns. Unbounded, that ends as an out-of-memory kill
    — which is a SIGKILL, the one signal the restore cannot catch, so the run that most
    needs the source put back is the one that leaves it mutated.
    """
    guard_against_recursion(command)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            preexec_fn=bound_child,
            env=os.environ | {RECURSION_FLAG: "1"},
        )
    except subprocess.TimeoutExpired:
        return -1, f"timed out after {timeout:g}s without finishing"
    return result.returncode, result.stdout + result.stderr


def report(code: int, output: str) -> int:
    """Print the verdict and return the exit code the caller should use."""
    if RE_COLLECTION_ERROR.search(output):
        print("INVALID  the mutated source does not import; the mutation is not a check")
        return 1
    if code == 0:
        print("MISSED   every test passed without the check, so no test covers it")
        return 1
    caught = RE_FAILING_TEST.findall(output)
    if not caught:
        # The suite failed without naming a case: it was killed, it crashed, or it is
        # not unittest. Calling that CAUGHT would report the check as covered on the
        # strength of a timeout, so it exits 1 — nothing was proven either way.
        print(f"UNKNOWN  the suite exited {code} but named no failing test; read its output")
        return 1
    print(f"CAUGHT   {len(caught)} failing test(s)")
    for name in caught:
        print(f"         {name}")
    return 0


def resolve_command(words: list[str]) -> tuple[str, ...]:
    """Turn the trailing command-line words into the command to run.

    argparse leaves the `--` separator on the front of REMAINDER; only that first one is
    dropped, since a later `--` belongs to the command being passed through.
    """
    if words and words[0] == "--":
        words = words[1:]
    return tuple(words) or DEFAULT_TEST_COMMAND


def mutate(
    path: Path,
    anchor: str,
    replacement: str,
    command: tuple[str, ...] = DEFAULT_TEST_COMMAND,
) -> int:
    """Mutate, test, restore, report. The source is restored however this exits."""
    original = apply_mutation(path, anchor, replacement)

    def restore_and_resume(number, _frame):
        """Put the file back, then let the signal do what it would have done."""
        path.write_bytes(original)
        signal.signal(number, signal.SIG_DFL)
        signal.raise_signal(number)

    previous = {number: signal.signal(number, restore_and_resume) for number in RESTORE_SIGNALS}
    try:
        code, output = run_tests(command)
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
        path.write_bytes(original)
    return report(code, output)


def main(argv: list[str]) -> int:
    """Parse arguments and run one mutation."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", required=True, type=Path, help="source file to mutate")
    parser.add_argument(
        "--anchor", required=True, help="exact text to replace; must match once, indentation included"
    )
    parser.add_argument(
        "--with", dest="replacement", required=True, help="text to put in the anchor's place"
    )
    # REMAINDER rather than nargs="+", so a command carrying its own flags — which most
    # test runners do — is passed through instead of being parsed as this script's.
    parser.add_argument(
        "test_command",
        nargs=argparse.REMAINDER,
        help="command to run instead of the whole suite, last and after a `--`",
    )
    args = parser.parse_args(argv)
    return mutate(args.file, args.anchor, args.replacement, resolve_command(args.test_command))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
