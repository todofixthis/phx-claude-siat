"""Disable one check in place, run the suite, and report whether a test caught it.

Run from the repo root (ADR 011):

    python3 -m scripts.dev.mutate --file scripts/adr/generate_index.py \
        --anchor 'if not target.exists():' --with 'if False:'

Exits 0 when the mutation is KILLED (some test failed, so the check is guarded) and 1
when it SURVIVED (every test passed without it, so nothing tests it). That mapping lets
a sequence of mutations be scripted and checked by exit code rather than read by eye.

`.agents/rules/testing.md` requires this after adding a check. Doing it by hand is four
shell lines that must not be got wrong: the file is restored in a `finally`, because a
crash between mutate and restore leaves a deliberately broken check in the working tree,
and the next thing to run is usually a commit.

Stdlib-only, like everything under scripts/ (ADR 007).
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
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

# unittest names each failing case on its own line, which is the useful half of the
# output: "which test caught this" is what the pull request has to report.
RE_FAILING_TEST = re.compile(r"^(?:FAIL|ERROR): (\S+)", re.MULTILINE)

# A suite that cannot even be collected proves nothing about the check, so a mutation
# producing one is reported apart from a mutation a test caught.
RE_COLLECTION_ERROR = re.compile(r"^(?:SyntaxError|IndentationError|ImportError)", re.MULTILINE)


def apply_mutation(path: Path, anchor: str, replacement: str) -> str:
    """Replace the first occurrence of `anchor`, returning the original text.

    Returning the original rather than writing a backup file keeps the restore in
    memory, so an interrupted run cannot leave a stray `.bak` beside the source.
    """
    original = path.read_text(encoding="utf-8")
    occurrences = original.count(anchor)
    if occurrences == 0:
        raise SystemExit(
            f"Error: {path} does not contain the anchor; copy it exactly from the source, "
            "including indentation"
        )
    if occurrences > 1:
        print(
            f"Warning: the anchor appears {occurrences} times in {path}; mutating the first",
            file=sys.stderr,
        )
    path.write_text(original.replace(anchor, replacement, 1), encoding="utf-8")
    return original


def run_tests(command: tuple[str, ...]) -> tuple[int, str]:
    """Run the suite, returning its exit code and both streams joined."""
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def report(code: int, output: str) -> int:
    """Print the verdict and return the exit code the caller should use."""
    if RE_COLLECTION_ERROR.search(output):
        print("INVALID  the mutated source does not import; the mutation is not a check")
        return 1
    if code == 0:
        print("SURVIVED every test passed without the check, so no test covers it")
        return 1
    caught = RE_FAILING_TEST.findall(output)
    print(f"KILLED   {len(caught)} failing test(s)")
    for name in caught:
        print(f"         {name}")
    return 0


def mutate(
    path: Path,
    anchor: str,
    replacement: str,
    command: tuple[str, ...] = DEFAULT_TEST_COMMAND,
) -> int:
    """Mutate, test, restore, report. The source is restored however this exits."""
    original = apply_mutation(path, anchor, replacement)
    try:
        code, output = run_tests(command)
    finally:
        path.write_text(original, encoding="utf-8")
    return report(code, output)


def main(argv: list[str]) -> int:
    """Parse arguments and run one mutation."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", required=True, type=Path, help="source file to mutate")
    parser.add_argument("--anchor", required=True, help="exact text to replace, indentation included")
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
    command = [word for word in args.test_command if word != "--"]
    return mutate(args.file, args.anchor, args.replacement, tuple(command) or DEFAULT_TEST_COMMAND)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
