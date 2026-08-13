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
import re
import signal
import subprocess
import sys
from pathlib import Path

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


def apply_mutation(path: Path, anchor: str, replacement: str, occurrence: int = 1) -> bytes:
    """Replace one occurrence of `anchor`, returning the file's original bytes.

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
    if occurrence > len(positions):
        raise SystemExit(
            f"Error: --occurrence {occurrence} but {path} holds {len(positions)} of that anchor"
        )
    if len(positions) > 1 and occurrence == 1:
        print(
            f"Warning: the anchor appears {len(positions)} times in {path}; mutating the "
            "first — pass --occurrence to target another",
            file=sys.stderr,
        )

    index = positions[occurrence - 1]
    mutated = text[:index] + replacement + text[index + len(anchor) :]
    path.write_bytes(mutated.encode("utf-8"))
    return original


def run_tests(command: tuple[str, ...]) -> tuple[int, str]:
    """Run the suite, returning its exit code and both streams joined.

    unittest writes its whole result block to stderr, so a caller reading stdout alone
    sees nothing and reports every run as having caught no tests.
    """
    result = subprocess.run(command, capture_output=True, text=True)
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
    occurrence: int = 1,
) -> int:
    """Mutate, test, restore, report. The source is restored however this exits."""
    original = apply_mutation(path, anchor, replacement, occurrence)

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
        "--anchor", required=True, help="exact text to replace, indentation included"
    )
    parser.add_argument(
        "--with", dest="replacement", required=True, help="text to put in the anchor's place"
    )
    parser.add_argument(
        "--occurrence",
        type=int,
        default=1,
        help="which occurrence of the anchor to mutate, counting from 1",
    )
    # REMAINDER rather than nargs="+", so a command carrying its own flags — which most
    # test runners do — is passed through instead of being parsed as this script's.
    parser.add_argument(
        "test_command",
        nargs=argparse.REMAINDER,
        help="command to run instead of the whole suite, last and after a `--`",
    )
    args = parser.parse_args(argv)
    return mutate(
        args.file,
        args.anchor,
        args.replacement,
        resolve_command(args.test_command),
        args.occurrence,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
