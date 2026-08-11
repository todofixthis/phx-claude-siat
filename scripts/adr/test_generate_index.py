"""Tests for generate_index.py.

Stdlib `unittest` rather than pytest, so the suite needs no dependency of its own
(ADR 007). Run from the repo root:

    python3 -m unittest discover -s scripts -t . -p 'test_*.py'

`generate()` takes its directories as arguments, so these tests never chdir and never
call it without them: the defaults resolve from the module (ADR 015), so an argumentless
call rewrites the real docs/adr/INDEX.md whatever the working directory is. The one test
that does chdir asserts precisely that — that moving cwd cannot redirect the defaults —
and never calls `generate()`.
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.adr.generate_index import (
    ADR_DIR,
    ADR_INDEX_FILENAME,
    EMPTY_NOTE,
    HIDDEN_STATUSES,
    INDEX_HEADER,
    REPO_ROOT,
    REVISIT_DISCHARGED_BY_FIELD,
    REVISIT_WHEN_FIELD,
    SCOPE_FIELD,
    STATUS_FIELDS,
    TABLE_HEADER,
    TAGS_FIELD,
    cell,
    generate,
    main,
    parse_adr,
    report_scoped_to,
    scope_matches,
    scope_problems,
)

# Written into the index before a run that must fail, then asserted unchanged: it is
# how a test tells "left alone" apart from "rewritten with the same content".
SENTINEL = "untouched\n"

# A file the fixture creates at the repo root, so the default scope names something that
# exists. It sits outside the ADR directory, where it would read as a misfiled document.
SCOPED_FILE = "README.md"

ROWS = {
    "001-first.md": (
        f"| [001](001-first.md) | Accepted | Do the thing | {SCOPED_FILE} | A summary. |  |\n"
    ),
    "002-second.md": (
        f"| [002](002-second.md) | Accepted | Do another thing | {SCOPED_FILE} | A summary. |  |\n"
    ),
}

# A trigger short enough to read inside an asserted row, and recognisably a condition.
TRIGGER = "A second plugin joins the marketplace."


def adr(status: str | None = "Accepted", title: str = "1: Do the thing", **fields) -> str:
    """Build an ADR file body with the given frontmatter and title.

    Passing None for a field omits its line entirely, which is how a test covers a
    key being absent rather than holding the text "None".
    """
    fields = {"status": status} | fields
    lines = ["date: 2026-08-01", f"scope: [{SCOPED_FILE}]", "summary: A summary."]
    for key, value in fields.items():
        lines = [line for line in lines if not line.startswith(f"{key}:")]
        if value is not None:
            lines.append(f"{key}: {value}")
    return "---\n" + "\n".join(lines) + f"\n---\n\n# {title}\n\nBody.\n"


class AdrDirTestCase(unittest.TestCase):
    """A temp repo with a docs/adr inside it, living for the whole test.

    The two directories are separate because scope entries resolve against the repo
    root: a scoped file placed in the ADR directory would be read as a misfiled
    document, so the fixture cannot collapse them into one.
    """

    def setUp(self) -> None:
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.repo_root = Path(directory)
        self.root = self.repo_root / "docs" / "adr"
        self.root.mkdir(parents=True)
        (self.repo_root / SCOPED_FILE).write_text("", encoding="utf-8")

    def write(self, name: str, content: str) -> None:
        """Place a file in the fixture directory."""
        (self.root / name).write_text(content, encoding="utf-8")

    def write_scoped(self, name: str) -> None:
        """Create a path at the repo root for a scope entry to name."""
        target = self.repo_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")

    def write_adrs(self, *names: str) -> None:
        """Place one valid ADR per name, titled to match the row expected for it."""
        for index, name in enumerate(names, start=1):
            title = "Do the thing" if index == 1 else "Do another thing"
            self.write(name, adr(title=f"{index}: {title}"))

    def run_generate(self) -> tuple[int, str, str]:
        """Run generate() against the fixture, returning its exit code with both streams."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = generate(self.root, self.repo_root)
        return code, out.getvalue(), err.getvalue()

    def index(self) -> str:
        """Read the generated index."""
        return (self.root / ADR_INDEX_FILENAME).read_text(encoding="utf-8")

    def assert_index_lists(self, *names: str) -> None:
        """Assert the whole index file, not merely that it contains a row."""
        rows = "".join(ROWS[name] for name in names)
        self.assertEqual(self.index(), f"{INDEX_HEADER}\n{TABLE_HEADER}{rows}")


class ParseAdrTests(unittest.TestCase):
    """Unit tests for ``parse_adr()``: every rule an ADR document must satisfy."""

    def problems(self, content: str) -> list:
        """Return only the problems parse_adr found in one document."""
        return parse_adr(content)[2]

    def test_returns_no_problems_for_a_valid_adr(self):
        """The fields every other case mutates must themselves parse clean."""
        fields, title, problems = parse_adr(adr())
        self.assertEqual(problems, [])
        self.assertEqual(title, "Do the thing")
        self.assertEqual(fields["status"], "Accepted")

    def test_reports_a_missing_frontmatter_block(self):
        """A file with no frontmatter is reported, not silently omitted from the index."""
        self.assertEqual(self.problems("# 1: Title\n\nBody.\n"), ["has no frontmatter block"])

    def test_reports_a_missing_title(self):
        """A file with no level-one heading has no title to put in the index."""
        content = "---\nstatus: Accepted\n---\n\nBody with no heading.\n"
        self.assertIn("has no level-one title heading", self.problems(content))

    def test_strips_the_number_prefix_from_the_title(self):
        """The index column carries the title alone; the number is already its own column."""
        _, title, _ = parse_adr(adr(title="7: Keep repo scripts stdlib-only"))
        self.assertEqual(title, "Keep repo scripts stdlib-only")

    def test_keeps_a_title_that_has_no_number_prefix(self):
        """A title written without a number is left as it stands."""
        _, title, _ = parse_adr(adr(title="Keep repo scripts stdlib-only"))
        self.assertEqual(title, "Keep repo scripts stdlib-only")

    def test_propagates_frontmatter_problems(self):
        """Problems from the shared parser reach the caller rather than being swallowed."""
        content = "---\nstatus: Accepted\nnonsense\n---\n\n# 1: Title\n\nBody.\n"
        self.assertIn("is not `key: value`: 'nonsense'", self.problems(content))

    def test_reports_a_wrapped_frontmatter_value(self):
        """The truncation the shared parser catches is a problem here too, not a short row."""
        content = (
            "---\nstatus: Accepted\nsummary: Something long\n  and its remainder\n"
            "---\n\n# 1: Title\n\nBody.\n"
        )
        self.assertIn(
            "continued onto another line; wrap it onto one: 'and its remainder'",
            self.problems(content),
        )

    def test_a_horizontal_rule_does_not_extend_the_frontmatter(self):
        """Frontmatter ends at its own closing fence, not at a rule further down."""
        content = "---\nstatus: Accepted\n---\n\n# 1: Title\n\n---\n\nMore body.\n"
        fields, title, _ = parse_adr(content)
        self.assertEqual((fields, title), ({"status": "Accepted"}, "Title"))

    def test_the_first_heading_wins(self):
        """A later level-one heading cannot displace the ADR's own title."""
        content = "---\nstatus: Accepted\n---\n\n# 1: Real title\n\n# Later heading\n"
        _, title, _ = parse_adr(content)
        self.assertEqual(title, "Real title")

    def test_rejects_an_unrecognised_status(self):
        """A status outside the vocabulary must not reach the index as a literal."""
        problem = self.problems(adr(status="Draft"))[0]
        self.assertIn("'Draft'", problem)
        self.assertIn("Accepted, Archived, Superseded", problem)

    def test_rejects_a_status_in_the_wrong_case(self):
        """Matching is exact, so `archived` cannot quietly hide an ADR."""
        self.assertIn("'archived'", self.problems(adr(status="archived"))[0])

    def test_rejects_a_missing_status(self):
        """An ADR with no status has no place in the index either way."""
        self.assertIn("None", self.problems(adr(status=None))[0])

    def test_requires_the_field_each_status_owns(self):
        """Archived and Superseded each carry a field saying why; neither is optional."""
        for status, field in STATUS_FIELDS.items():
            with self.subTest(status=status):
                self.assertIn(
                    f"is {status} but declares no `{field}`", self.problems(adr(status=status))
                )

    def test_rejects_an_empty_value_for_a_status_field(self):
        """A key present with nothing after it explains as little as no key at all."""
        problems = self.problems(adr(status="Archived", **{"archived-because": ""}))
        self.assertIn("is Archived but declares no `archived-because`", problems)

    def test_rejects_a_status_field_its_status_does_not_own(self):
        """A field left behind by a status change would otherwise read as current."""
        problems = self.problems(adr(**{"archived-because": "A comment."}))
        self.assertIn(
            "declares `archived-because` but its status is 'Accepted', not Archived", problems
        )

    def test_accepts_a_status_carrying_its_own_field(self):
        """The pairing is required, so the valid combination must pass cleanly."""
        self.assertEqual(self.problems(adr(status="Superseded", **{"superseded-by": "12"})), [])

    def test_accepts_a_revisit_trigger_on_its_own(self):
        """A live trigger is the ordinary case: it needs no discharge until one arrives."""
        self.assertEqual(self.problems(adr(**{REVISIT_WHEN_FIELD: TRIGGER})), [])

    def test_accepts_a_discharge_paired_with_the_trigger_it_spent(self):
        """The pairing is required, so the valid combination must pass cleanly."""
        fields = {REVISIT_WHEN_FIELD: TRIGGER, REVISIT_DISCHARGED_BY_FIELD: "12"}
        self.assertEqual(self.problems(adr(**fields)), [])

    def test_rejects_a_discharge_with_no_trigger(self):
        """A discharge alone records that something was spent without saying what."""
        self.assertIn(
            f"declares `{REVISIT_DISCHARGED_BY_FIELD}` but no `{REVISIT_WHEN_FIELD}` to spend",
            self.problems(adr(**{REVISIT_DISCHARGED_BY_FIELD: "12"})),
        )

    def test_rejects_the_field_scope_replaced(self):
        """A stale `tags` must fail, or a half-finished migration passes unnoticed."""
        problem = self.problems(adr(**{TAGS_FIELD: "[alpha, beta]"}))[0]
        self.assertIn(f"declares `{TAGS_FIELD}`", problem)
        self.assertIn(f"`{SCOPE_FIELD}` replaced", problem)

    def test_rejects_a_missing_scope(self):
        """Required, so that an absent field cannot pass for a decision binding no path."""
        self.assertIn(
            f"declares no `{SCOPE_FIELD}`; list the paths it binds, or `[]` where it binds none",
            self.problems(adr(**{SCOPE_FIELD: None})),
        )

    def test_accepts_a_scope_binding_no_path(self):
        """`[]` is the answer for a decision whose subject has no file, not an omission."""
        self.assertEqual(self.problems(adr(**{SCOPE_FIELD: "[]"})), [])

    def test_rejects_a_scope_written_as_a_scalar(self):
        """One bare path parses as a string, which would iterate character by character."""
        self.assertIn(
            f"declares `{SCOPE_FIELD}` as a scalar",
            self.problems(adr(**{SCOPE_FIELD: "scripts/"}))[0],
        )

    def test_collects_every_problem_in_one_pass(self):
        """One fix must not be the thing that reveals the next."""
        content = "---\nstatus: Draft\nnonsense\n---\n\nNo heading.\n"
        self.assertEqual(len(self.problems(content)), 4)


class ScopeProblemsTests(unittest.TestCase):
    """Unit tests for ``scope_problems()``: the one rule needing the filesystem."""

    def setUp(self) -> None:
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(directory)
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "versions.py").write_text("", encoding="utf-8")

    def test_accepts_entries_that_resolve(self):
        """A file and a directory prefix both name something; neither is a problem."""
        self.assertEqual(scope_problems(["scripts/versions.py", "scripts/"], self.root), [])

    def test_reports_an_entry_matching_nothing(self):
        """A path that moved leaves a scope naming code that is no longer there."""
        problem = scope_problems(["scripts/gone.py"], self.root)[0]
        self.assertIn("scopes `scripts/gone.py`, which nothing matches", problem)

    def test_reports_a_directory_written_without_its_slash(self):
        """Without the slash nothing beneath the directory matches, so it silently binds one path."""
        self.assertIn(
            "scopes `scripts`, a directory; write it as `scripts/`",
            scope_problems(["scripts"], self.root),
        )

    def test_reports_an_entry_written_as_a_glob(self):
        """A glob is the natural thing to reach for, and 'nothing matches' would misdiagnose it."""
        problem = scope_problems(["scripts/**/*.py"], self.root)[0]
        self.assertIn("which reads as a glob", problem)

    def test_reports_every_bad_entry(self):
        """One scope may hold several paths, and one fix must not reveal the next."""
        self.assertEqual(len(scope_problems(["a.py", "b.py"], self.root)), 2)


class ScopeMatchesTests(unittest.TestCase):
    """Unit tests for ``scope_matches()``."""

    def test_matches_the_file_itself(self):
        """An entry naming one file covers that file."""
        self.assertTrue(scope_matches("scripts/versions.py", "scripts/versions.py"))

    def test_matches_anything_beneath_a_directory(self):
        """A trailing slash is what makes an entry cover a subtree rather than one path."""
        self.assertTrue(scope_matches("scripts/", "scripts/ci/versions.py"))

    def test_does_not_match_a_sibling_sharing_a_prefix(self):
        """`scripts/` must not reach `scripts-old/`, which shares its opening characters."""
        self.assertFalse(scope_matches("scripts/", "scripts-old/versions.py"))

    def test_opens_a_subtree_only_for_an_entry_ending_in_a_slash(self):
        """Bare string prefixing would let `scripts` swallow `scripts-old/`; the slash is the guard."""
        self.assertFalse(scope_matches("scripts", "scripts-old/versions.py"))

    def test_does_not_match_an_unrelated_path(self):
        """The common case: most decisions bind nothing the file in hand touches."""
        self.assertFalse(scope_matches("scripts/", "docs/adr/001-first.md"))


class CellTests(unittest.TestCase):
    """Unit tests for ``cell()``."""

    def test_joins_a_list_with_commas(self):
        """Tags render as one comma-separated cell."""
        self.assertEqual(cell(["ci", "adr"]), "ci, adr")

    def test_escapes_pipes_in_a_scalar(self):
        """An unescaped pipe would silently split the row into extra columns."""
        self.assertEqual(cell("Use mypy | not ty"), "Use mypy \\| not ty")

    def test_escapes_pipes_inside_a_list(self):
        """Escaping happens after joining, so a pipe in one item is caught too."""
        self.assertEqual(cell(["a|b", "c"]), "a\\|b, c")


class GenerateTests(AdrDirTestCase):
    """Integration tests: the file generate() writes for a directory that validates."""

    def test_writes_a_row_for_each_accepted_adr(self):
        """Two ADRs prove the loop covers the directory rather than stopping at the first."""
        self.write_adrs("001-first.md", "002-second.md")
        code, out, _ = self.run_generate()
        self.assertEqual(code, 0)
        self.assert_index_lists("001-first.md", "002-second.md")
        self.assertIn("(2 entries)", out)

    def test_excludes_hidden_statuses_but_keeps_their_neighbours(self):
        """A hidden ADR leaves the index while an accepted sibling stays in it."""
        for status in HIDDEN_STATUSES:
            with self.subTest(status=status):
                self.write_adrs("001-first.md")
                self.write("002-hidden.md", adr(status=status, **{STATUS_FIELDS[status]: "12"}))
                code, out, _ = self.run_generate()
                self.assertEqual(code, 0)
                self.assert_index_lists("001-first.md")
                self.assertIn("(1 entries)", out)

    def test_orders_rows_by_file_number(self):
        """Zero-padded numbers sort as strings, so 009 must precede 010."""
        self.write("010-later.md", adr())
        self.write("009-earlier.md", adr())
        self.run_generate()
        rows = [line for line in self.index().splitlines() if line.startswith("| [")]
        self.assertEqual([row.split("]")[0] for row in rows], ["| [009", "| [010"])

    def test_ignores_the_index_and_dot_files(self):
        """The index must not list itself, and tooling debris is not a misfiled document."""
        self.write_adrs("001-first.md")
        self.write(ADR_INDEX_FILENAME, SENTINEL)
        self.write(".DS_Store", "")
        code, _, err = self.run_generate()
        self.assertEqual((code, err), (0, ""))
        self.assert_index_lists("001-first.md")

    def test_says_so_when_there_are_no_adrs(self):
        """An empty table reads as a truncated file, so the empty state is spelt out."""
        code, out, _ = self.run_generate()
        self.assertEqual(code, 0)
        self.assertEqual(self.index(), f"{INDEX_HEADER}\n{EMPTY_NOTE}")
        self.assertIn("(0 entries)", out)

    def test_carries_a_revisit_trigger_into_its_own_column(self):
        """The index is where a trigger reaches someone who never opens the ADR."""
        self.write("001-first.md", adr(**{REVISIT_WHEN_FIELD: TRIGGER}))
        self.run_generate()
        self.assertEqual(
            self.index(),
            f"{INDEX_HEADER}\n{TABLE_HEADER}| [001](001-first.md) | Accepted "
            f"| Do the thing | {SCOPED_FILE} | A summary. | {TRIGGER} |\n",
        )

    def test_omits_a_discharged_trigger_from_its_column(self):
        """A spent condition stops costing context, there being nothing left to act on."""
        fields = {REVISIT_WHEN_FIELD: TRIGGER, REVISIT_DISCHARGED_BY_FIELD: "12"}
        self.write("001-first.md", adr(**fields))
        self.run_generate()
        self.assert_index_lists("001-first.md")

    def test_leaves_the_scope_cell_empty_for_a_decision_binding_no_path(self):
        """An empty cell is a statement — nothing you edit will surface this decision."""
        self.write("001-first.md", adr(**{SCOPE_FIELD: "[]"}))
        self.run_generate()
        self.assertEqual(
            self.index(),
            f"{INDEX_HEADER}\n{TABLE_HEADER}| [001](001-first.md) | Accepted "
            "| Do the thing |  | A summary. |  |\n",
        )

    def test_lists_every_scope_entry_in_one_cell(self):
        """A decision binding several paths must show all of them, not the first."""
        self.write_scoped("CHANGELOG.md")
        self.write("001-first.md", adr(**{SCOPE_FIELD: f"[{SCOPED_FILE}, CHANGELOG.md]"}))
        self.run_generate()
        self.assertIn(f"| {SCOPED_FILE}, CHANGELOG.md |", self.index())

    def test_is_idempotent(self):
        """The CI check diffs this file, so a second run must reproduce it exactly."""
        self.write_adrs("001-first.md", "002-second.md")
        self.run_generate()
        first = self.index()
        self.run_generate()
        self.assertEqual(self.index(), first)


class GenerateFailureTests(AdrDirTestCase):
    """Integration tests: on any error the index must be left exactly as it was found."""

    def assert_rejected(self, *expected: str) -> None:
        """Run against the fixture and assert the exit code, message, and untouched index."""
        self.write(ADR_INDEX_FILENAME, SENTINEL)
        code, _, err = self.run_generate()
        self.assertEqual(code, 1)
        for fragment in expected:
            self.assertIn(fragment, err)
        self.assertIn("Fix the errors above before committing.", err)
        self.assertEqual(self.index(), SENTINEL)

    def test_rejects_a_file_that_is_not_an_adr(self):
        """The directory holds ADRs and the index only; anything else is misfiled."""
        self.write_adrs("001-first.md")
        self.write("notes.md", "# Notes\n")
        self.assert_rejected(f"notes.md is neither an ADR nor {ADR_INDEX_FILENAME}")

    def test_rejects_an_adr_whose_filename_breaks_the_convention(self):
        """An unnumbered ADR is a real decision that would drop out of the index silently."""
        self.write("keep-scripts-stdlib-only.md", adr())
        self.assert_rejected("rename it NNN-slug.md")

    def test_reports_a_problem_against_the_file_that_holds_it(self):
        """A parse problem names its file, since the run reports every file at once."""
        self.write("001-bad.md", adr(status="Draft"))
        self.assert_rejected("001-bad.md has status 'Draft'")

    def test_reports_every_bad_file(self):
        """Two broken ADRs produce two errors, so one fix does not reveal the next."""
        self.write("001-bad.md", adr(status="Draft"))
        self.write("002-bad.md", adr(status="Nope"))
        self.assert_rejected("001-bad.md", "002-bad.md")

    def test_a_valid_sibling_does_not_rescue_the_run(self):
        """One bad file fails the whole run rather than yielding a partial index."""
        self.write_adrs("001-first.md")
        self.write("002-bad.md", adr(status="Draft"))
        self.assert_rejected("002-bad.md")

    def test_rejects_a_scope_naming_something_that_is_gone(self):
        """A path that moved must fail here rather than rot unnoticed in the index."""
        self.write("001-first.md", adr(**{SCOPE_FIELD: "[scripts/gone.py]"}))
        self.assert_rejected("001-first.md scopes `scripts/gone.py`, which nothing matches")

    def test_checks_the_scope_of_an_archived_adr(self):
        """Archived means out of the index, not out of force; its paths rot the same way."""
        fields = {"archived-because": "A comment.", SCOPE_FIELD: "[scripts/gone.py]"}
        self.write("001-first.md", adr(status="Archived", **fields))
        self.assert_rejected("001-first.md scopes `scripts/gone.py`")

    def test_leaves_the_scope_of_a_superseded_adr_alone(self):
        """Editing a superseded ADR is forbidden, so checking one could only deadlock the build."""
        fields = {"superseded-by": "12", SCOPE_FIELD: "[scripts/gone.py]"}
        self.write("001-superseded.md", adr(status="Superseded", **fields))
        code, _, err = self.run_generate()
        self.assertEqual((code, err), (0, ""))


class ReportScopedToTests(AdrDirTestCase):
    """Integration tests: the `--for` lookup from a path back to the decisions binding it."""

    def report(self, *paths: str) -> tuple[int, str]:
        """Run report_scoped_to() against the fixture, returning its code and output."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = report_scoped_to(list(paths), self.root)
        return code, out.getvalue()

    def test_warns_that_an_unreadable_adr_binds_nothing(self):
        """This is the only place the lookup speaks, so a silent gap reads as 'nothing binds it'."""
        self.write("001-bad.md", adr(status="Draft"))
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            report_scoped_to(["scripts/versions.py"], self.root)
        self.assertIn("001-bad.md could not be read, so it binds nothing here", err.getvalue())

    def test_names_the_decision_binding_the_path(self):
        """The question a code author holds: what binds the file in front of me?"""
        self.write_scoped("scripts/versions.py")
        self.write("001-first.md", adr(**{SCOPE_FIELD: "[scripts/]"}))
        code, out = self.report("scripts/versions.py")
        self.assertEqual(code, 0)
        self.assertEqual(out, "001 (Accepted): Do the thing — docs/adr/001-first.md\n")

    def test_stays_silent_for_a_path_nothing_binds(self):
        """Most files are bound by nothing, so the common case must not cry wolf."""
        self.write_adrs("001-first.md")
        self.assertEqual(self.report("docs/unrelated.md"), (0, ""))

    def test_reports_an_archived_decision(self):
        """Archived ADRs are out of the index by design; this is where they resurface."""
        self.write_scoped("scripts/versions.py")
        fields = {"archived-because": "A comment.", SCOPE_FIELD: "[scripts/]"}
        self.write("001-first.md", adr(status="Archived", **fields))
        self.assertIn("001 (Archived)", self.report("scripts/versions.py")[1])

    def test_omits_a_superseded_decision(self):
        """A replaced decision binds nothing, so surfacing it would be noise."""
        self.write_scoped("scripts/versions.py")
        fields = {"superseded-by": "12", SCOPE_FIELD: "[scripts/]"}
        self.write("001-superseded.md", adr(status="Superseded", **fields))
        self.assertEqual(self.report("scripts/versions.py"), (0, ""))

    def test_reports_every_decision_binding_the_path(self):
        """Two ADRs can bind one path, and stopping at the first would hide the second."""
        self.write_scoped("scripts/versions.py")
        for name in ("001-first.md", "002-second.md"):
            self.write(name, adr(**{SCOPE_FIELD: "[scripts/]"}))
        self.assertEqual(len(self.report("scripts/versions.py")[1].splitlines()), 2)

    def test_matches_any_of_several_paths(self):
        """The hook passes every staged path at once, so one match in the set is enough."""
        self.write_scoped("scripts/versions.py")
        self.write("001-first.md", adr(**{SCOPE_FIELD: "[scripts/]"}))
        self.assertIn("001", self.report("README.md", "scripts/versions.py")[1])


class ArgumentTests(unittest.TestCase):
    """Unit tests for ``main()``: which mode each invocation selects."""

    def test_rejects_for_with_no_path(self):
        """`--for` with nothing after it would otherwise report against an empty set."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["--for"])
        self.assertEqual(code, 1)
        self.assertIn("--for needs at least one path", err.getvalue())

    def test_rejects_an_unrecognised_argument(self):
        """A typo must fail rather than silently regenerating the index instead."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["--wat"])
        self.assertEqual(code, 1)
        self.assertIn("unrecognised arguments", err.getvalue())


class DefaultDirectoryTests(unittest.TestCase):
    """Integration test: what the no-argument invocation resolves to."""

    def test_a_working_directory_holding_its_own_docs_adr_cannot_capture_the_defaults(self):
        """A relative default resolves against the caller's tree, silently editing it instead."""
        directory = self.enterContext(tempfile.TemporaryDirectory())
        (Path(directory) / "docs" / "adr").mkdir(parents=True)
        with contextlib.chdir(directory):
            self.assertTrue(ADR_DIR.is_absolute())
            self.assertFalse(ADR_DIR.is_relative_to(directory))

    def test_the_root_is_the_repo_rather_than_the_package_inside_it(self):
        """One `.parent` too few lands on scripts/, where docs/adr does not exist."""
        self.assertEqual(ADR_DIR, REPO_ROOT / "docs" / "adr")
        self.assertTrue(ADR_DIR.is_dir())
        self.assertTrue(Path(__file__).resolve().is_relative_to(REPO_ROOT))


if __name__ == "__main__":
    unittest.main()
