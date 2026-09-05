"""Report US spellings for a person to triage. Never edits anything.

Standard library only, so it runs wherever `python3` does and needs no virtualenv.
The skill runs it as `python3 ${CLAUDE_SKILL_DIR}/scan.py`:

    python3 ${CLAUDE_SKILL_DIR}/scan.py [PATH ...]
    python3 ${CLAUDE_SKILL_DIR}/scan.py --verify NAME ...
    python3 ${CLAUDE_SKILL_DIR}/scan.py --self-check
    python3 ${CLAUDE_SKILL_DIR}/scan.py --show-noise

Exit codes follow ripgrep's, which the skill already teaches: 0 nothing to triage, 1
hits needing triage, 2 the run failed. 3 is a usage error, kept separate from 2 because
the skill escalates a 2 as a broken tool and a mistyped argument is not that. 4 is
nothing to check — every given path was missing or excluded, or an empty selection was
given with --no-implicit-cwd — which a pre-commit hook needs told apart from 2: a
healthy commit routinely selects nothing for this tool to do.

Paths are anchored to this file's own directory so the tool finds its fixtures wherever
the plugin is installed; that anchor is read on the `__main__` line only, and every
function below takes the directory it needs, so none of them can reach a tree the caller
did not name. `main` is the one exception and it is deliberate: given no path it sweeps
the working directory, which is what a person at a prompt means by running it with no
arguments.
"""

import argparse
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

EXIT_CLEAN = 0
EXIT_HITS = 1
EXIT_ERROR = 2
EXIT_USAGE = 3
EXIT_NOTHING_TO_CHECK = 4

# The floor the syntax here actually needs (`list | None` in an evaluated annotation).
# Checked rather than assumed: a consumer runs this on whatever `python3` they have, not
# on the version CI pins, and an older one would otherwise die with a SyntaxError before
# a single line of ours runs — reported by the shell as a code this tool never chose.
MINIMUM_PYTHON = (3, 10)
if sys.version_info < MINIMUM_PYTHON:
    sys.stderr.write(
        f"error: this needs Python {'.'.join(map(str, MINIMUM_PYTHON))} or newer; "
        f"found {sys.version.split()[0]}\n"
    )
    raise SystemExit(EXIT_ERROR)

try:
    # Guarded because a missing or broken bundle is a broken tool, and an unguarded
    # ImportError exits 1 — which this tool's own contract reads as "hits to triage".
    # A broken install must never be mistaken for a result.
    from table import CLASS_LABELS, NOISE, ROWS  # noqa: F401  (re-exported for tests)
except ImportError as exc:  # pragma: no cover - exercised by a subprocess test
    sys.stderr.write(f"error: cannot load the substitution table beside this script: {exc}\n")
    raise SystemExit(EXIT_ERROR) from exc

# What a sweep never reads. Lock files are full of external package names; a CHANGELOG
# records text users already received, so respelling one falsifies it.
EXCLUDED_NAMES = frozenset({"CHANGELOG.md"})
EXCLUDED_SUFFIXES = (".lock",)

# The tool's own skill directory, matched as a path segment as well as by __file__.
# __file__ alone is not enough: with the plugin served from a cache and this repo swept,
# the tool sits outside the tree, nothing is excluded, and the word list plus the
# fixtures flood the report.
OWN_SKILL_SEGMENT = ("skills", "nz-english")

# ripgrep's heuristic, so a differential run against it compares like with like.
BINARY_SNIFF_BYTES = 8192

AGENT_INSTRUCTION_NAMES = ("AGENTS.md", "CLAUDE.md")

# The header's provenance label. `files` means every target was a file, so nothing
# needed discovering; `git` and `walk` mean a directory target was swept, filtered or
# not. Distinct from a plain bool so a file-list invocation cannot be reported as
# `walk`, which it neither did nor needed.
SOURCE_FILES = "files"
SOURCE_GIT = "git"
SOURCE_WALK = "walk"

# Hits printed per row before the rest are counted instead. A sweep of a large tree can
# produce hundreds of thousands of hits, and an uncapped report is unusable to a person
# and ruinous to an agent's context. The count is always exact; only the listing is cut,
# and the report says by how much.
DEFAULT_ROW_LIMIT = 50


class ScanError(Exception):
    """The run could not be completed, so no result should be believed."""


class NothingToCheck(Exception):
    """Every path given was missing or excluded — a hook's healthy no-op, not a failure.

    Distinct from ScanError: a hook needs to tell "there was nothing here to check" apart
    from "the tool is broken" by exit code, and the two must never share one.
    """


def compiled_patterns() -> list:
    """Return (row, pattern, compiled regex) for every pattern in the table.

    Case-insensitive, matching the searches this replaces. Case sensitivity would
    silently close the documented blind spot where a camel-cased `dialogUrl` escapes the
    `-og` guard, and the skill's text about that would stop being true.
    """
    compiled = []
    for row in ROWS:
        for pattern in row.patterns:
            compiled.append((row, pattern, re.compile(pattern.regex, re.IGNORECASE)))
    return compiled


def prefilter() -> "re.Pattern":
    """Return one regex matching anything any pattern could match.

    Running all nineteen patterns over every line is quadratic in the wrong things: a
    large tree is overwhelmingly lines that match nothing, and each one paid for
    nineteen scans. One union scan rejects those in a single pass, and the per-pattern
    loop then runs only on lines that can produce a hit.

    Correctness does not depend on this being tight — it is a union of the same
    patterns, so a line it rejects cannot match any of them individually.
    """
    return re.compile(
        "|".join(f"(?:{pattern.regex})" for _row, pattern, _rx in compiled_patterns()),
        re.IGNORECASE,
    )


def is_binary(path: Path) -> bool:
    """Report whether a file holds a NUL byte in its first block."""
    try:
        with path.open("rb") as handle:
            return b"\0" in handle.read(BINARY_SNIFF_BYTES)
    except OSError:
        return True


def under_own_skill(path: Path, own_dir: Path) -> bool:
    """Report whether a path belongs to this skill, by location or by name.

    Both tests are needed and neither is sufficient. `own_dir` catches a sweep of the
    working tree the tool ships from; the name segment catches a sweep of a checkout of
    this repository while the tool runs from an installed copy elsewhere.
    """
    if path == own_dir or own_dir in path.parents:
        return True
    parts = path.parts
    for index in range(len(parts) - 1):
        if parts[index : index + 2] == OWN_SKILL_SEGMENT:
            return True
    return False


def is_excluded(path: Path, own_dir: Path) -> bool:
    """Report whether a discovered path is out of scope for a sweep."""
    if path.name in EXCLUDED_NAMES:
        return True
    if path.suffix in EXCLUDED_SUFFIXES:
        return True
    return under_own_skill(path, own_dir)


def git_files(root: Path) -> list | None:
    """Return the tracked and untracked files under `root`, or None outside a repo.

    `--exclude-standard` is what keeps `node_modules` and `.venv` out without a rule of
    our own, and untracked files are included because a sweep should see work in
    progress. Paths come back relative to the working directory rather than the
    repository root, so every one is resolved before it is used — the name-segment
    exclusion above depends on that.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            capture_output=True,
            cwd=root,
            # A non-zero exit means "not a repository" here, handled below.
            check=False,
            text=True,
        )
    except OSError as exc:
        raise ScanError(f"could not run git: {exc}") from exc

    if result.returncode != 0:
        return None
    return [(root / name).resolve() for name in result.stdout.split("\0") if name]


def walk_files(root: Path) -> list:
    """Return every file under `root`, for a directory that is not a git repository."""
    return sorted(path.resolve() for path in root.rglob("*") if path.is_file())


def common_base(targets: list) -> Path:
    """Return the directory every reported path is shown relative to.

    With one directory target that is the target itself. With one file target it is the
    file's parent — a file is not a directory hits can be shown relative to, and the
    former behaviour of returning the file broke the header's "agent instructions" line,
    which computes `relative_to(base)` and needs a directory to compute it against. With
    several targets it is their common ancestor, so the header names somewhere the swept
    files actually live — taking the working directory instead would print a path that
    was never a target and that none of the hits sit under. Targets on different roots
    have no common ancestor, and then paths are reported absolute.
    """
    resolved = [target.resolve() for target in targets]
    if len(resolved) == 1:
        target = resolved[0]
        return target.parent if target.is_file() else target
    try:
        return Path(os.path.commonpath([str(path) for path in resolved]))
    except ValueError:
        return Path(resolved[0].anchor)


def discover(targets: list, own_dir: Path) -> tuple:
    """Return the files to search and the header's provenance label for how.

    Each target is discovered separately, so two paths in different repositories both
    work. A target that is a file is taken as given rather than walked. A target that no
    longer exists is skipped rather than failing the whole run — the routine shape of a
    staged deletion reaching this tool from a hook that ran `git diff --cached
    --name-only` without `--diff-filter` — so the files that do still exist are still
    checked.

    The provenance is `files` where every target was a file, so no directory was ever
    walked or asked of git; `git` where at least one target was a directory inside a
    repository, so git's `--exclude-standard` filtered it; `walk` where at least one
    target was a directory outside a repository, so nothing was filtered. A target that
    is a file needs neither, so it does not affect which of `git` or `walk` a directory
    target beside it reports.
    """
    found = []
    saw_directory = False
    used_git = False
    for target in targets:
        resolved = target.resolve()
        if not resolved.exists():
            continue
        if resolved.is_file():
            found.append(resolved)
            continue
        saw_directory = True
        from_git = git_files(resolved)
        if from_git is None:
            found.extend(walk_files(resolved))
        else:
            used_git = True
            found.extend(from_git)

    if not saw_directory:
        source = SOURCE_FILES
    elif used_git:
        source = SOURCE_GIT
    else:
        source = SOURCE_WALK

    keep = []
    seen = set()
    for path in found:
        if path in seen or is_excluded(path, own_dir):
            continue
        seen.add(path)
        # git ls-files still lists a tracked file deleted from the worktree, and a
        # submodule arrives as one path that is a directory.
        if not path.is_file():
            continue
        if is_binary(path):
            continue
        keep.append(path)

    # Nothing to search is not a tree with nothing to convert. Point the tool at a lock
    # file, a CHANGELOG, a path that does not exist, or its own directory and every one
    # is skipped or excluded, leaving nothing read — which used to report as a clean
    # sweep over zero files. It is instead a distinct outcome from either a clean sweep
    # or a broken run: for a hook, a commit touching only excluded or deleted paths is
    # healthy, not a misconfiguration, so this is NothingToCheck rather than ScanError.
    if not keep:
        raise NothingToCheck(
            "no files to search: every path was missing, excluded, empty, or not text."
        )
    return sorted(keep), source


def is_noise(token: str) -> bool:
    """Report whether a token is a word the noise list already accounts for.

    A trailing `s` is stripped so a plural matches the singular the list carries —
    `parameters` against `parameter`. Nothing else is normalised: `-ies` and `-es` would
    need guessing at the stem, and a wrong guess suppresses a real hit, which is the
    failure this skill treats as the serious one. An unrecognised plural is reported for
    triage instead, which costs a reader seconds.
    """
    folded = token.casefold()
    if folded in NOISE:
        return True
    return folded.endswith("s") and folded[:-1] in NOISE


def word_at(line: str, start: int, end: int) -> str:
    """Return the run of letters around the matched span.

    Narrower than `token_at`, which keeps `_` and digits: a `liter` match inside
    `test_treats_the_anchor_as_literal_text` gives the token for display but `literal`
    here, which is what the noise list holds. Without this, every noise word embedded in
    a snake_case identifier arrives as a hit to triage.
    """
    left = start
    while left > 0 and line[left - 1].isalpha():
        left -= 1
    right = end
    while right < len(line) and line[right].isalpha():
        right += 1
    return line[left:right]


def token_at(line: str, start: int, end: int) -> str:
    """Return the whole identifier or word the matched span sits inside.

    The span says which row claimed the hit; the token is what a reader triages, and the
    two differ whenever the match is part of a longer name.
    """
    left = start
    while left > 0 and (line[left - 1].isalnum() or line[left - 1] == "_"):
        left -= 1
    right = end
    while right < len(line) and (line[right].isalnum() or line[right] == "_"):
        right += 1
    return line[left:right]


def scan(paths: list, base: Path) -> dict:
    """Return {row: {"hits": [...], "noise": Counter}} for every row in the table.

    Every row is present whether or not it matched, so a caller cannot mistake a row
    that found nothing for a row that never ran.
    """
    patterns = compiled_patterns()
    sieve = prefilter()
    results = {row: {"hits": [], "noise": Counter()} for row in ROWS}

    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise ScanError(f"could not read {path}: {exc}") from exc

        try:
            shown = path.relative_to(base)
        except ValueError:
            shown = path

        for number, line in enumerate(text.splitlines(), start=1):
            # Most lines match nothing; one union scan rejects them before the
            # per-pattern loop runs at all.
            if not sieve.search(line):
                continue
            for row, pattern, regex in patterns:
                for match in regex.finditer(line):
                    span = match.group(0)
                    token = token_at(line, match.start(), match.end())
                    word = word_at(line, match.start(), match.end())
                    # Classified on the letter run, not the whole token: every noise
                    # entry is pure letters, so testing the token as well would be a
                    # second guard that can never fire on its own.
                    if is_noise(word):
                        results[row]["noise"][word] += 1
                        continue
                    results[row]["hits"].append(
                        {
                            "path": str(shown),
                            "line": number,
                            "span": span,
                            "token": token,
                            "judgement": pattern.judgement,
                            "label": pattern.span_label,
                        }
                    )
    return results


def agent_instructions(paths: list, base: Path) -> list:
    """Return the agent-instruction files among the swept paths.

    A stated US English convention overrides this skill, so the reader is told which
    files to read for one. Whether a statement is there, and what it covers, is theirs
    to judge.
    """
    found = []
    for path in paths:
        if path.name in AGENT_INSTRUCTION_NAMES:
            try:
                found.append(str(path.relative_to(base)))
            except ValueError:
                found.append(str(path))
    return sorted(found)


def header_width() -> int:
    """Return the column width the widest row label needs, plus a separating space.

    Computed rather than fixed: a hardcoded width silently runs the counts together with
    the label the moment a row is added whose name is longer than the guess.
    """
    return max(len(f"{row.us} → {row.nz}") for row in ROWS) + 2


def judgement_mark(row) -> str:
    """Return the `*judgement` marker for a row, or "" where none of it needs reading.

    A property of the row, not of what this run happened to find: it says which of the
    row's hits *would* need reading, so it is the same on every run and a reader can
    learn it once. A bare mark covers the whole row; a named span covers only the hits
    whose matched span is that one, which is how `meter` sits on the `-er` row without
    making `centre` a judgement call.
    """
    judgement_patterns = [pattern for pattern in row.patterns if pattern.judgement]
    if not judgement_patterns:
        return ""
    labels = sorted(
        {pattern.span_label for pattern in judgement_patterns if pattern.span_label}
    )
    if len(labels) != len(judgement_patterns):
        # At least one judgement pattern names no span, so the row as a whole needs
        # reading and a partial list would understate it.
        return "  *judgement"
    return f"  *judgement: {', '.join(labels)}"


def format_row_block(row, result: dict, show_noise: bool, limit: int) -> list:
    """Return the report lines for one row, header included when it found nothing.

    `limit` caps the hits listed, never the count in the header: a reader must be able
    to trust the number even when the listing is cut.
    """
    hits = result["hits"]
    noise = result["noise"]
    noise_total = sum(noise.values())

    mark = judgement_mark(row)

    header = f"{row.us} → {row.nz}"
    lines = [f"{header:<{header_width()}}[{len(hits)} to triage, {noise_total} noise]{mark}"]

    shown = hits[:limit]
    width_path = max((len(f"{h['path']}:{h['line']}") for h in shown), default=0)
    width_span = max((len(h["span"]) for h in shown), default=0)
    for hit in shown:
        where = f"{hit['path']}:{hit['line']}"
        lines.append(f"  {where:<{width_path}}  {hit['span']:<{width_span}}  {hit['token']}")
    if len(hits) > limit:
        lines.append(f"  … {len(hits) - limit} more not shown (--limit to raise)")

    if noise_total and show_noise:
        for word, count in sorted(noise.items()):
            lines.append(f"  noise: {word} ×{count}")
    elif noise_total:
        summary = ", ".join(f"{word} ×{count}" for word, count in sorted(noise.items()))
        lines.append(f"  noise ({noise_total}): {summary}")
    return lines


def render(
    results: dict,
    paths: list,
    base: Path,
    source: str,
    show_noise: bool,
    limit: int = DEFAULT_ROW_LIMIT,
) -> str:
    """Return the whole sweep report."""
    instructions = agent_instructions(paths, base)
    file_count = len(paths)
    file_noun = "file" if file_count == 1 else "files"
    lines = [
        f"swept: {base} ({file_count} {file_noun}, {source})",
        "agent instructions: " + (", ".join(instructions) if instructions else "none found"),
        "excluded: *.lock, CHANGELOG.md, own skill directory",
        "",
    ]

    total_hits = 0
    total_noise = 0
    pattern_count = 0
    for row in ROWS:
        pattern_count += len(row.patterns)
        result = results[row]
        total_hits += len(result["hits"])
        total_noise += sum(result["noise"].values())
        lines.extend(format_row_block(row, result, show_noise, limit))

    lines.append("")
    tail = "" if show_noise else " (--show-noise to expand)"
    lines.append(
        f"{len(ROWS)} rows, {pattern_count} patterns, {total_hits} to triage, "
        f"{total_noise} noise suppressed{tail}"
    )
    lines.append(
        "*judgement — read these, don't apply them; a named span marks only those hits"
    )
    return "\n".join(lines)


def guard_for(us_word: str, nz_word: str) -> str:
    """Return the character the NZ spelling adds after the US one, or "".

    A guard is possible only where the US form is a prefix of the NZ form, which across
    the table is true of the `-ogue` family and `program`/`programme` alone. Everywhere
    else the spellings diverge before the end, so a bare search cannot match the
    converted form and needs no guard.
    """
    if nz_word.startswith(us_word) and len(nz_word) > len(us_word):
        return nz_word[len(us_word)]
    return ""


def verify_matches(name: str) -> list:
    """Return (row, matched_span, guard) for every row whose pattern claims `name`.

    Each row is asked with its own regex rather than with a list of literals. That is
    what makes this work for all seventeen rows: a shape row like `-ize` has no literal
    US form to look for, and an alternation row like `-or` would need every member
    duplicated here. Running the row's own pattern reuses the one definition, so a word
    added to a row is verifiable the moment it is searchable.

    The guard comes from `nz_forms`, which only the rows that can have one carry.
    """
    found = []
    for row, _pattern, regex in compiled_patterns():
        match = regex.search(name)
        if not match:
            continue
        span = match.group(0)
        nz_word = row.nz_forms.get(span.casefold(), "")
        guard = guard_for(span.casefold(), nz_word) if nz_word else ""
        found.append((row, span, guard))
    return found


def run_verify(names: list, paths: list, base: Path) -> tuple:
    """Return (report, exit code) for the renamed names given.

    Case-sensitive, unlike the sweep: you know the case of the name you renamed, and
    case-insensitivity is what lets the guard swallow a `dialogUrl`.
    """
    blocks = []
    surviving = 0
    for name in names:
        matches = verify_matches(name)
        if not matches:
            raise Usage(
                f"{name!r} contains no word from the substitution table, so there is "
                f"nothing to search for. Pass the OLD spelling of a name you renamed."
            )
        # One search per name, not one per matching row. The search is for the name
        # itself, so a name two rows both claim would otherwise read every line twice,
        # print each hit twice, and leave a footer that is not a count of references.
        rows = ", ".join(dict.fromkeys(f"{row.us} → {row.nz}" for row, _s, _g in matches))

        # A guard applies only where the table word ends the name: `show_dialog` is a
        # prefix of `show_dialogue`, where `dialog_box` is not a prefix of
        # `dialogue_box`. At most one row can satisfy that for a given name.
        #
        # A lookahead, so the guard never becomes part of the reported line, and so a
        # name at end of line matches without a separate alternative for it.
        guard = next(
            (g for _r, span, g in matches if g and name.casefold().endswith(span.casefold())),
            "",
        )
        regex = re.compile(re.escape(name) + (f"(?!{guard})" if guard else ""))

        hits = []
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                raise ScanError(f"could not read {path}: {exc}") from exc
            try:
                shown = path.relative_to(base)
            except ValueError:
                shown = path
            for number, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    hits.append(f"  {shown}:{number}  {line.strip()}")

        surviving += len(hits)
        guard_note = f" (guarded against a following {guard!r})" if guard else ""
        blocks.append(f"{name} — {rows}{guard_note}: {len(hits)} remaining")
        blocks.extend(hits)

    blocks.append("")
    blocks.append(
        f"{surviving} surviving reference(s). Account for each as one you meant to keep "
        f"or one you missed."
    )
    return "\n".join(blocks), (EXIT_HITS if surviving else EXIT_CLEAN)


class Usage(Exception):
    """The arguments were wrong, which is the caller's error rather than a failure."""


def run_self_check(own_dir: Path) -> tuple:
    """Return (report, exit code) for a run over the bundled fixtures.

    Discovery and exclusion are bypassed deliberately: the fixtures live inside this
    skill's own directory, which a sweep excludes, so routing this through discovery
    would read nothing and report success having checked nothing. The consequence is
    that a green self-check says the patterns still fire and says nothing about whether
    a sweep can find files.

    The assertion is per row rather than a total, because a total passes while one row
    finds nothing and another finds double.
    """
    us_dir = own_dir / "tests" / "fixtures" / "us"
    nz_dir = own_dir / "tests" / "fixtures" / "nz"
    for directory in (us_dir, nz_dir):
        if not directory.is_dir():
            raise ScanError(f"missing bundled fixture: {directory}")

    us_files = sorted(path for path in us_dir.rglob("*") if path.is_file())
    nz_files = sorted(path for path in nz_dir.rglob("*") if path.is_file())

    us_results = scan(us_files, us_dir)
    nz_results = scan(nz_files, nz_dir)

    silent = [row.us for row in ROWS if not us_results[row]["hits"]]
    leaked = {
        row.us: [hit["token"] for hit in nz_results[row]["hits"]]
        for row in ROWS
        if nz_results[row]["hits"]
    }

    lines = [f"self-check: {len(ROWS)} rows against {len(us_files)} US fixture file(s)"]
    if silent:
        lines.append("FAILED — these rows found nothing in the US fixture:")
        lines.extend(f"  {label}" for label in silent)
    if leaked:
        lines.append("FAILED — these rows reported non-noise hits in the NZ fixture:")
        lines.extend(f"  {label}: {', '.join(tokens)}" for label, tokens in leaked.items())
    if silent or leaked:
        return "\n".join(lines), EXIT_ERROR

    lines.append("every row fired against the US fixture; the NZ fixture returned only noise")
    return "\n".join(lines), EXIT_CLEAN


class UsageParser(argparse.ArgumentParser):
    """An argument parser that exits 3 rather than argparse's default 2.

    2 is this tool's "the run failed", which the skill tells a reader to escalate. A
    mistyped flag is the caller's error, and sending them to escalate a working tool is
    the wrong instruction.
    """

    def error(self, message: str):
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser."""
    parser = UsageParser(
        description="Report US spellings for triage. Never edits anything.",
    )
    parser.add_argument(
        "paths", nargs="*", help="paths to sweep (default: the working directory)"
    )
    parser.add_argument(
        "--no-implicit-cwd",
        action="store_true",
        help=(
            "an empty path list is nothing to check (exit 4) rather than the default "
            "working-directory sweep — for a hook, whose file list can genuinely be empty"
        ),
    )
    # One name per flag, repeated, rather than `nargs="+"`: a greedy list swallows the
    # trailing path and then reports it as a name carrying no table word, which reads as
    # the tool rejecting a correct invocation.
    parser.add_argument(
        "--verify",
        action="append",
        metavar="NAME",
        help="old spelling of a name you renamed; repeat for more than one",
    )
    parser.add_argument(
        "--self-check", action="store_true", help="prove the patterns still fire"
    )
    parser.add_argument("--show-noise", action="store_true", help="list every suppressed hit")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_ROW_LIMIT,
        metavar="N",
        help=f"hits listed per row before the rest are counted (default {DEFAULT_ROW_LIMIT})",
    )
    return parser


def main(argv: list, own_dir: Path) -> int:
    """Run the tool and return its exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.self_check:
            if args.verify or args.paths or args.show_noise:
                raise Usage("--self-check takes no other arguments")
            report, code = run_self_check(own_dir)
            print(report)
            return code

        if args.no_implicit_cwd and not args.paths:
            raise NothingToCheck(
                "no paths given, and --no-implicit-cwd disables the default "
                "working-directory sweep"
            )

        targets = [Path(path) for path in args.paths] or [Path.cwd()]
        base = common_base(targets)
        paths, source = discover(targets, own_dir)

        if args.verify:
            if args.show_noise:
                raise Usage(
                    "--show-noise does not apply to --verify: surviving references carry "
                    "no noise classification"
                )
            report, code = run_verify(args.verify, paths, base)
            print(report)
            return code

        results = scan(paths, base)
        print(render(results, paths, base, source, args.show_noise, args.limit))
        return EXIT_HITS if any(results[row]["hits"] for row in ROWS) else EXIT_CLEAN

    except Usage as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except NothingToCheck as exc:
        print(f"nothing to check: {exc}")
        return EXIT_NOTHING_TO_CHECK
    except ScanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as exc:  # noqa: BLE001 - deliberate catch-all, see below
        # Anything unforeseen is a failed run, not a clean one. Without this the
        # traceback exits 1, which this tool's contract reads as "hits to triage" — a
        # broken tool wearing the shape of a result, which is the failure it exists to
        # end. The traceback still reaches stderr for whoever has to fix it.
        import traceback

        traceback.print_exc()
        print(f"error: the run failed: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], Path(__file__).resolve().parent))
