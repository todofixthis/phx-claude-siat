"""Tests for `adr.py` — parsing, findings, the index, root resolution and the commands.

Unit classes call one function directly; `MainTests` reaches the tool through its entry
point and covers only what emerges from the composition: exit codes, what is left on disk,
which file an error is attributed to.

The module acts on the caller's tree and resolves its root from the path it is given
(the testing rule's caller's-tree stance), so it has no anchor of its own. Every test
passes a fixture root explicitly and never changes the working directory; the
`ResolveRootTests` cover resolution from a nested path, a worktree-shaped tree and a
subdirectory with no managed corpus above it.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from adr import (
    ADR_DIR,
    EMPTY_NOTE,
    HIDDEN_STATUSES,
    INDEX_FILENAME,
    INDEX_HEADER,
    REVISIT_DISCHARGED_BY_FIELD,
    REVISIT_WHEN_FIELD,
    SCOPE_FIELD,
    STATUS_FIELDS,
    TABLE_HEADER,
    TAGS_FIELD,
    binding,
    cell,
    inspect,
    is_managed,
    main,
    parse_adr,
    reconcile,
    relative_to_root,
    render_index,
    resolve_root,
    scope_matches,
    scope_problems,
)

SCOPED_FILE = "README.md"

# A trigger short enough to read inside an asserted row, and recognisably a condition.
TRIGGER = "A second plugin joins the marketplace."

ROWS = {
    "001-first.md": (
        f"| [001](001-first.md) | Accepted | Do the thing | {SCOPED_FILE} | A summary. |  |\n"
    ),
    "002-second.md": (
        f"| [002](002-second.md) | Accepted | Do another thing | {SCOPED_FILE} | A summary. |  |\n"
    ),
    "002-supersedes-001.md": (
        f"| [002](002-supersedes-001.md) | Accepted | Do another thing | {SCOPED_FILE} "
        "| A summary. |  |\n"
    ),
}


def adr_text(status: str | None = "Accepted", title: str = "1: Do the thing", **fields) -> str:
    """Build an ADR file body with the given frontmatter and title.

    Passing None for a field omits its line entirely, which is how a test covers a key
    being absent rather than holding the text "None".
    """
    fields = {"status": status} | fields
    lines = ["date: 2026-08-01", f"scope: [{SCOPED_FILE}]", "summary: A summary."]
    for key, value in fields.items():
        lines = [line for line in lines if not line.startswith(f"{key}:")]
        if value is not None:
            lines.append(f"{key}: {value}")
    return "---\n" + "\n".join(lines) + f"\n---\n\n# {title}\n\nBody.\n"


class RepoTestCase(unittest.TestCase):
    """A temp repository with a `docs/adr` inside it, living for the whole test.

    The scoped file sits at the repository root, outside the ADR directory, where it
    would otherwise read as a misfiled document.
    """

    def setUp(self) -> None:
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.repo_root = Path(directory).resolve()
        self.adr_dir = self.repo_root / ADR_DIR
        self.adr_dir.mkdir(parents=True)
        (self.repo_root / SCOPED_FILE).write_text("", encoding="utf-8")

    def write(self, name: str, content: str) -> None:
        """Place a file in the ADR directory."""
        (self.adr_dir / name).write_text(content, encoding="utf-8")

    def write_scoped(self, name: str) -> None:
        """Create a path at the repository root for a scope entry to name."""
        target = self.repo_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")

    def manage(self) -> None:
        """Write a managed index, as `index` would, so hooks and resolution treat the corpus as the tool's."""
        rows, findings = inspect(self.repo_root)
        assert not findings, findings
        (self.adr_dir / INDEX_FILENAME).write_text(render_index(rows), encoding="utf-8")

    def index(self) -> str:
        """Read the generated index."""
        return (self.adr_dir / INDEX_FILENAME).read_text(encoding="utf-8")

    def run_main(self, *argv: str, cwd: Path | None = None) -> tuple[int, str, str]:
        """Run the entry point against the fixture, returning its exit code with both streams."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv), cwd or self.repo_root)
        return code, out.getvalue(), err.getvalue()


class ParseAdrTests(unittest.TestCase):
    """Unit tests for ``parse_adr()``: every rule an ADR document must satisfy."""

    def problems(self, content: str) -> list:
        """Return only the problems parse_adr found in one document."""
        return parse_adr(content)[3]

    def test_returns_no_problems_for_a_valid_adr(self):
        """The fields every other case mutates must themselves parse clean."""
        fields, title, _, problems = parse_adr(adr_text())
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
        _, title, _, _ = parse_adr(adr_text(title="7: Keep repo scripts stdlib-only"))
        self.assertEqual(title, "Keep repo scripts stdlib-only")

    def test_keeps_a_title_that_has_no_number_prefix(self):
        """A title written without a number is left as it stands."""
        _, title, _, _ = parse_adr(adr_text(title="Keep repo scripts stdlib-only"))
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
        fields, title, _, _ = parse_adr(content)
        self.assertEqual((fields, title), ({"status": "Accepted"}, "Title"))

    def test_the_first_heading_wins(self):
        """A later level-one heading cannot displace the ADR's own title."""
        content = "---\nstatus: Accepted\n---\n\n# 1: Real title\n\n# Later heading\n"
        _, title, _, _ = parse_adr(content)
        self.assertEqual(title, "Real title")

    def test_rejects_an_unrecognised_status(self):
        """A status outside the vocabulary must not reach the index as a literal."""
        problem = self.problems(adr_text(status="Draft"))[0]
        self.assertIn("'Draft'", problem)
        self.assertIn("Accepted, Archived, Superseded", problem)

    def test_rejects_a_status_in_the_wrong_case(self):
        """Matching is exact, so `archived` cannot quietly hide an ADR."""
        self.assertIn("'archived'", self.problems(adr_text(status="archived"))[0])

    def test_rejects_a_missing_status(self):
        """An ADR with no status has no place in the index either way."""
        self.assertIn("None", self.problems(adr_text(status=None))[0])

    def test_requires_the_field_each_status_owns(self):
        """Archived and Superseded each carry a field saying why; neither is optional."""
        for status, field in STATUS_FIELDS.items():
            with self.subTest(status=status):
                self.assertIn(
                    f"is {status} but declares no `{field}`",
                    self.problems(adr_text(status=status)),
                )

    def test_rejects_an_empty_value_for_a_status_field(self):
        """A key present with nothing after it explains as little as no key at all."""
        problems = self.problems(adr_text(status="Archived", **{"archived-because": ""}))
        self.assertIn("is Archived but declares no `archived-because`", problems)

    def test_rejects_a_status_field_its_status_does_not_own(self):
        """A field left behind by a status change would otherwise read as current."""
        problems = self.problems(adr_text(**{"archived-because": "A comment."}))
        self.assertIn(
            "declares `archived-because` but its status is 'Accepted', not Archived", problems
        )

    def test_accepts_a_status_carrying_its_own_field(self):
        """The pairing is required, so the valid combination must pass cleanly."""
        self.assertEqual(
            self.problems(adr_text(status="Superseded", **{"superseded-by": "12"})), []
        )

    def test_accepts_a_revisit_trigger_on_its_own(self):
        """A live trigger is the ordinary case: it needs no discharge until one arrives."""
        self.assertEqual(self.problems(adr_text(**{REVISIT_WHEN_FIELD: TRIGGER})), [])

    def test_accepts_a_discharge_paired_with_the_trigger_it_spent(self):
        """The pairing is required, so the valid combination must pass cleanly."""
        fields = {REVISIT_WHEN_FIELD: TRIGGER, REVISIT_DISCHARGED_BY_FIELD: "12"}
        self.assertEqual(self.problems(adr_text(**fields)), [])

    def test_rejects_a_discharge_with_no_trigger(self):
        """A discharge alone records that something was spent without saying what."""
        self.assertIn(
            f"declares `{REVISIT_DISCHARGED_BY_FIELD}` but no `{REVISIT_WHEN_FIELD}` to spend",
            self.problems(adr_text(**{REVISIT_DISCHARGED_BY_FIELD: "12"})),
        )

    def test_rejects_the_field_scope_replaced(self):
        """A stale `tags` must fail, or a half-finished migration passes unnoticed."""
        problem = self.problems(adr_text(**{TAGS_FIELD: "[alpha, beta]"}))[0]
        self.assertIn(f"declares `{TAGS_FIELD}`", problem)
        self.assertIn(f"`{SCOPE_FIELD}` replaced", problem)

    def test_rejects_a_missing_scope(self):
        """Required, so that an absent field cannot pass for a decision binding no path."""
        self.assertIn(
            f"declares no `{SCOPE_FIELD}`; list the paths it binds, or `[]` where it binds none",
            self.problems(adr_text(**{SCOPE_FIELD: None})),
        )

    def test_accepts_a_scope_binding_no_path(self):
        """`[]` is the answer for a decision whose subject has no file, not an omission."""
        self.assertEqual(self.problems(adr_text(**{SCOPE_FIELD: "[]"})), [])

    def test_rejects_a_scope_written_as_a_scalar(self):
        """One bare path parses as a string, which would iterate character by character."""
        self.assertIn(
            f"declares `{SCOPE_FIELD}` as a scalar",
            self.problems(adr_text(**{SCOPE_FIELD: "scripts/"}))[0],
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
        kind, entry, message = scope_problems(["scripts/gone.py"], self.root)[0]
        self.assertEqual((kind, entry), ("dangling", "scripts/gone.py"))
        self.assertIn("scopes `scripts/gone.py`, which nothing matches", message)

    def test_reports_a_directory_written_without_its_slash(self):
        """Without the slash nothing beneath the directory matches, so it silently binds one path."""
        self.assertEqual(
            scope_problems(["scripts"], self.root),
            [("malformed", "scripts", "scopes `scripts`, a directory; write it as `scripts/`")],
        )

    def test_reports_an_entry_written_as_a_glob(self):
        """A glob is the natural thing to reach for, and 'nothing matches' would misdiagnose it."""
        kind, _, message = scope_problems(["scripts/**/*.py"], self.root)[0]
        self.assertEqual(kind, "malformed")
        self.assertIn("which reads as a glob", message)

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


class RelativeToRootTests(unittest.TestCase):
    """Unit tests for ``relative_to_root()``."""

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_leaves_a_relative_path_alone(self):
        """Scope entries are written repo-relative, so that form is already the answer."""
        self.assertEqual(
            relative_to_root("scripts/ci/versions.py", self.root), "scripts/ci/versions.py"
        )

    def test_converts_an_absolute_path_inside_the_root(self):
        """An editor or an agent hands you an absolute path, which matches no scope entry."""
        absolute = str(self.root / "scripts" / "ci" / "versions.py")
        self.assertEqual(relative_to_root(absolute, self.root), "scripts/ci/versions.py")

    def test_returns_none_for_a_path_outside_the_root(self):
        """A false "nothing binds this" for a file the lookup cannot even see is worse than no answer."""
        self.assertIsNone(relative_to_root("/etc/hosts", self.root))


class IsManagedTests(RepoTestCase):
    """Unit tests for ``is_managed()``: the header line is the whole test."""

    def test_a_missing_index_is_unmanaged(self):
        """A docs/adr with no INDEX.md is not the tool's corpus."""
        self.assertFalse(is_managed(self.repo_root))

    def test_a_hand_written_index_is_unmanaged(self):
        """An index that does not open with the tool's header is somebody else's."""
        (self.adr_dir / INDEX_FILENAME).write_text("# ADR Index\n", encoding="utf-8")
        self.assertFalse(is_managed(self.repo_root))

    def test_a_generated_index_is_managed(self):
        """An index opening with the header line marks the corpus as managed."""
        self.write("001-first.md", adr_text())
        self.manage()
        self.assertTrue(is_managed(self.repo_root))


class ResolveRootTests(RepoTestCase):
    """Unit tests for ``resolve_root()``: the path in hand, then .git, then the start."""

    def test_an_explicit_root_wins(self):
        """--repo-root is taken as given, whatever lies above the path."""
        elsewhere = self.repo_root / "elsewhere"
        elsewhere.mkdir()
        self.assertEqual(resolve_root(self.repo_root / "src", elsewhere), elsewhere)

    def test_finds_the_managed_corpus_above_a_nested_file(self):
        """A file deep in the tree resolves to the managed root above it."""
        self.write("001-first.md", adr_text())
        self.manage()
        nested = self.repo_root / "src" / "pkg" / "mod.py"
        nested.parent.mkdir(parents=True)
        nested.write_text("", encoding="utf-8")
        self.assertEqual(resolve_root(nested), self.repo_root)

    def test_the_innermost_managed_corpus_wins(self):
        """A managed corpus inside another resolves to the inner one for paths beneath it."""
        self.write("001-first.md", adr_text())
        self.manage()
        inner = self.repo_root / "packages" / "app"
        (inner / ADR_DIR).mkdir(parents=True)
        (inner / SCOPED_FILE).write_text("", encoding="utf-8")
        (inner / ADR_DIR / "001-inner.md").write_text(adr_text(), encoding="utf-8")
        rows, _ = inspect(inner)
        (inner / ADR_DIR / INDEX_FILENAME).write_text(render_index(rows), encoding="utf-8")
        self.assertEqual(resolve_root(inner / "src" / "x.py"), inner)
        self.assertEqual(resolve_root(self.repo_root / "other.py"), self.repo_root)

    def test_a_worktree_resolves_to_itself_not_the_checkout_it_sits_in(self):
        """A managed worktree under .worktrees/ is its own root, not the launch directory's."""
        self.write("001-first.md", adr_text())
        self.manage()
        worktree = self.repo_root / ".worktrees" / "feature"
        (worktree / ADR_DIR).mkdir(parents=True)
        (worktree / SCOPED_FILE).write_text("", encoding="utf-8")
        (worktree / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        (worktree / ADR_DIR / "001-first.md").write_text(adr_text(), encoding="utf-8")
        rows, _ = inspect(worktree)
        (worktree / ADR_DIR / INDEX_FILENAME).write_text(render_index(rows), encoding="utf-8")
        self.assertEqual(resolve_root(worktree / "src" / "x.py"), worktree)

    def test_stops_at_the_first_git_directory(self):
        """A submodule with its own .git is its own root even under a managed superproject."""
        self.write("001-first.md", adr_text())
        self.manage()
        submodule = self.repo_root / "vendor" / "lib"
        submodule.mkdir(parents=True)
        (submodule / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        self.assertEqual(resolve_root(submodule / "x.py"), submodule)

    def test_falls_back_to_the_git_root_for_an_unmanaged_tree(self):
        """With no managed corpus above, the nearest .git names the root, so `new` lands there."""
        (self.repo_root / ".git").mkdir()
        deep = self.repo_root / "a" / "b"
        deep.mkdir(parents=True)
        self.assertEqual(resolve_root(deep), self.repo_root)

    def test_falls_back_to_the_start_when_nothing_is_above_it(self):
        """A bare directory with no corpus and no .git resolves to itself."""
        bare = self.repo_root / "bare"
        bare.mkdir()
        self.assertFalse(any((p / ".git").exists() for p in (bare, *bare.parents)))
        self.assertEqual(resolve_root(bare), bare)


class InspectTests(RepoTestCase):
    """Unit tests for ``inspect()``: rows for the index and findings keyed by what must change."""

    def test_a_dangling_scope_entry_is_keyed_by_the_entry(self):
        """A scope naming nothing on disk yields a dangling finding whose value is the entry."""
        self.write("001-first.md", adr_text(scope="[gone/]"))
        _, findings = inspect(self.repo_root)
        self.assertEqual(
            [(f.kind, f.value, f.adr) for f in findings], [("dangling", "gone/", "001")]
        )

    def test_a_malformed_adr_is_keyed_by_its_file(self):
        """A frontmatter fault yields one malformed finding per file, keyed by the filename."""
        self.write("001-first.md", adr_text(status="Bogus"))
        _, findings = inspect(self.repo_root)
        self.assertEqual([(f.kind, f.value) for f in findings], [("malformed", "001-first.md")])

    def test_a_collision_is_keyed_by_the_number(self):
        """Two ADRs sharing a number yield a collision finding keyed by the bare number."""
        self.write("001-first.md", adr_text())
        self.write("1-second.md", adr_text(title="1: Do another thing"))
        _, findings = inspect(self.repo_root)
        self.assertEqual([(f.kind, f.value) for f in findings], [("collision", "1")])

    def test_a_missing_directory_is_a_finding_not_an_error(self):
        """A root with no docs/adr reports one finding rather than raising."""
        root = self.repo_root / "empty"
        root.mkdir()
        rows, findings = inspect(root)
        self.assertEqual(rows, [])
        self.assertEqual([f.kind for f in findings], ["missing"])

    def test_leaves_the_scope_of_a_superseded_adr_alone(self):
        """Editing a superseded ADR is forbidden, so checking one could only deadlock the build."""
        fields = {"superseded-by": "12", SCOPE_FIELD: "[scripts/gone.py]"}
        self.write("001-superseded.md", adr_text(status="Superseded", **fields))
        _, findings = inspect(self.repo_root)
        self.assertEqual(findings, [])


class RenderIndexTests(RepoTestCase):
    """Integration tests: the text render_index() produces for a corpus that validates."""

    def write_adrs(self, *names: str) -> None:
        """Place one valid ADR per name, titled to match the row expected for it."""
        for index, name in enumerate(names, start=1):
            title = "Do the thing" if index == 1 else "Do another thing"
            self.write(name, adr_text(title=f"{index}: {title}"))

    def rendered(self) -> str:
        """Run inspect() then render_index() over the fixture, requiring a clean pass."""
        rows, findings = inspect(self.repo_root)
        self.assertEqual(findings, [])
        return render_index(rows)

    def assert_index_lists(self, *names: str) -> None:
        """Assert the whole rendered text, not merely that it contains a row."""
        rows = "".join(ROWS[name] for name in names)
        self.assertEqual(self.rendered(), f"{INDEX_HEADER}\n{TABLE_HEADER}{rows}")

    def test_writes_a_row_for_each_accepted_adr(self):
        """Two ADRs prove the loop covers the directory rather than stopping at the first."""
        self.write_adrs("001-first.md", "002-second.md")
        self.assert_index_lists("001-first.md", "002-second.md")

    def test_excludes_hidden_statuses_but_keeps_their_neighbours(self):
        """A hidden ADR leaves the index while an accepted sibling stays in it."""
        for status in HIDDEN_STATUSES:
            with self.subTest(status=status):
                self.write_adrs("001-first.md")
                self.write(
                    "002-hidden.md",
                    adr_text(
                        status=status,
                        title="2: Do another thing",
                        **{STATUS_FIELDS[status]: "12"},
                    ),
                )
                self.assert_index_lists("001-first.md")

    def test_orders_rows_by_file_number(self):
        """Zero-padded numbers sort as strings, so 009 must precede 010."""
        self.write("010-later.md", adr_text(title="10: Do the thing"))
        self.write("009-earlier.md", adr_text(title="9: Do the thing"))
        rows = [line for line in self.rendered().splitlines() if line.startswith("| [")]
        self.assertEqual([row.split("]")[0] for row in rows], ["| [009", "| [010"])

    def test_ignores_the_index_and_dot_files(self):
        """The index must not list itself, and tooling debris is not a misfiled document."""
        self.write_adrs("001-first.md")
        self.write(INDEX_FILENAME, "untouched\n")
        self.write(".DS_Store", "")
        self.assert_index_lists("001-first.md")

    def test_says_so_when_there_are_no_adrs(self):
        """An empty table reads as a truncated file, so the empty state is spelt out."""
        self.assertEqual(self.rendered(), f"{INDEX_HEADER}\n{EMPTY_NOTE}")

    def test_carries_a_revisit_trigger_into_its_own_column(self):
        """The index is where a trigger reaches someone who never opens the ADR."""
        self.write("001-first.md", adr_text(**{REVISIT_WHEN_FIELD: TRIGGER}))
        self.assertEqual(
            self.rendered(),
            f"{INDEX_HEADER}\n{TABLE_HEADER}| [001](001-first.md) | Accepted "
            f"| Do the thing | {SCOPED_FILE} | A summary. | {TRIGGER} |\n",
        )

    def test_omits_a_discharged_trigger_from_its_column(self):
        """A spent condition stops costing context, there being nothing left to act on."""
        fields = {REVISIT_WHEN_FIELD: TRIGGER, REVISIT_DISCHARGED_BY_FIELD: "12"}
        self.write("001-first.md", adr_text(**fields))
        self.assert_index_lists("001-first.md")

    def test_leaves_the_scope_cell_empty_for_a_decision_binding_no_path(self):
        """An empty cell is a statement — nothing you edit will surface this decision."""
        self.write("001-first.md", adr_text(**{SCOPE_FIELD: "[]"}))
        self.assertEqual(
            self.rendered(),
            f"{INDEX_HEADER}\n{TABLE_HEADER}| [001](001-first.md) | Accepted "
            "| Do the thing |  | A summary. |  |\n",
        )

    def test_lists_every_scope_entry_in_one_cell(self):
        """A decision binding several paths must show all of them, not the first."""
        self.write_scoped("CHANGELOG.md")
        self.write("001-first.md", adr_text(**{SCOPE_FIELD: f"[{SCOPED_FILE}, CHANGELOG.md]"}))
        self.assertIn(f"| {SCOPED_FILE}, CHANGELOG.md |", self.rendered())

    def test_a_number_inside_a_slug_is_not_a_collision(self):
        """Only the filename's leading number identifies an ADR; one in a slug names another."""
        self.write("001-first.md", adr_text(title="1: Do the thing"))
        self.write("002-supersedes-001.md", adr_text(title="2: Do another thing"))
        self.assert_index_lists("001-first.md", "002-supersedes-001.md")

    def test_padding_is_not_a_disagreement_between_heading_and_filename(self):
        """`ADR 1` names one decision however many zeros pad either spelling of it."""
        self.write("001-first.md", adr_text(title="1: Do the thing"))
        self.assert_index_lists("001-first.md")

    def test_an_unnumbered_heading_is_left_to_the_existing_rules(self):
        """With no number in the heading there is nothing to disagree with the filename."""
        self.write("001-first.md", adr_text(title="Do the thing"))
        self.assert_index_lists("001-first.md")


class InspectFailureTests(RepoTestCase):
    """Integration tests: what inspect() reports for a corpus with a fault, per fault."""

    def findings(self) -> list[str]:
        """Return the messages inspect() found for the fixture."""
        return [f.message for f in inspect(self.repo_root)[1]]

    def test_rejects_a_file_that_is_not_an_adr(self):
        """The directory holds ADRs and the index only; anything else is misfiled."""
        self.write("001-first.md", adr_text())
        self.write("notes.md", "# Notes\n")
        self.assertIn(f"notes.md is neither an ADR nor {INDEX_FILENAME}", self.findings()[0])

    def test_rejects_an_adr_whose_filename_breaks_the_convention(self):
        """An unnumbered ADR is a real decision that would drop out of the index silently."""
        self.write("keep-scripts-stdlib-only.md", adr_text())
        self.assertIn("rename it NNN-slug.md", self.findings()[0])

    def test_reports_a_problem_against_the_file_that_holds_it(self):
        """A parse problem names its file, since inspect() reports every file at once."""
        self.write("001-bad.md", adr_text(status="Draft"))
        self.assertIn("001-bad.md has status 'Draft'", self.findings()[0])

    def test_reports_every_bad_file(self):
        """Two broken ADRs produce two findings, so one fix does not reveal the next."""
        self.write("001-bad.md", adr_text(status="Draft"))
        self.write("002-bad.md", adr_text(status="Nope"))
        findings = " ".join(self.findings())
        self.assertIn("001-bad.md", findings)
        self.assertIn("002-bad.md", findings)

    def test_a_valid_sibling_does_not_mask_the_fault(self):
        """A good file's row does not stand in for the finding a bad sibling still owes."""
        self.write("001-first.md", adr_text())
        self.write("002-bad.md", adr_text(status="Draft"))
        self.assertIn("002-bad.md has status 'Draft'", self.findings()[0])

    def test_rejects_a_scope_naming_something_that_is_gone(self):
        """A path that moved must fail here rather than rot unnoticed in the index."""
        self.write("001-first.md", adr_text(scope="[scripts/gone.py]"))
        self.assertIn(
            "001-first.md scopes `scripts/gone.py`, which nothing matches", self.findings()[0]
        )

    def test_checks_the_scope_of_an_archived_adr(self):
        """Archived means out of the index, not out of force; its paths rot the same way."""
        fields = {"archived-because": "A comment.", SCOPE_FIELD: "[scripts/gone.py]"}
        self.write("001-first.md", adr_text(status="Archived", **fields))
        self.assertIn("001-first.md scopes `scripts/gone.py`", self.findings()[0])

    def test_rejects_two_adrs_sharing_a_number(self):
        """Concurrent branches allocate the same number, and every reference is by number."""
        self.write("001-first.md", adr_text(title="1: Do the thing"))
        self.write("001-second.md", adr_text(title="1: Do another thing"))
        self.assertIn(
            "001-second.md shares its number with 001-first.md; renumber whichever number "
            "nothing cites yet, since a number already cited cannot move",
            self.findings(),
        )

    def test_every_later_claimant_names_the_first(self):
        """Three on one number is two findings against the original, not a chain of blame."""
        for name in ("001-first.md", "001-second.md", "001-third.md"):
            self.write(name, adr_text(title="1: Do the thing"))
        findings = self.findings()
        self.assertTrue(
            any("001-second.md shares its number with 001-first.md" in f for f in findings)
        )
        self.assertTrue(
            any("001-third.md shares its number with 001-first.md" in f for f in findings)
        )

    def test_a_collision_masks_none_of_the_files_own_problems(self):
        """The collision is a separate finding, not raised in place of the file's own faults."""
        self.write("001-first.md", adr_text(title="1: Do the thing"))
        self.write("001-second.md", adr_text(status="Draft", title="1: Do another thing"))
        findings = self.findings()
        self.assertTrue(any("001-second.md has status 'Draft'" in f for f in findings))
        self.assertTrue(
            any("001-second.md shares its number with 001-first.md" in f for f in findings)
        )

    def test_padding_does_not_hide_a_collision(self):
        """`ADR 1` names one decision however its file spells the number."""
        self.write("001-first.md", adr_text(title="1: Do the thing"))
        self.write("1-second.md", adr_text(title="1: Do another thing"))
        self.assertIn("1-second.md shares its number with 001-first.md", self.findings()[0])

    def test_detects_a_collision_with_an_adr_the_index_hides(self):
        """A hidden ADR leaves the index but keeps its number, so the clash still stands."""
        for status in HIDDEN_STATUSES:
            with self.subTest(status=status):
                self.write(
                    "001-hidden.md",
                    adr_text(
                        status=status, title="1: Do the thing", **{STATUS_FIELDS[status]: "12"}
                    ),
                )
                self.write("001-visible.md", adr_text(title="1: Do another thing"))
                self.assertIn(
                    "001-visible.md shares its number with 001-hidden.md", self.findings()[0]
                )

    def test_rejects_a_heading_numbered_differently_from_its_filename(self):
        """Renumbering is two edits, and the index takes the number and the title from each."""
        self.write("002-second.md", adr_text(title="1: Do another thing"))
        self.assertIn(
            "002-second.md is numbered 002 by its filename and 1 by its heading; make them "
            "agree, since the index takes the number from one and the title from the other",
            self.findings(),
        )


class ReconcileTests(RepoTestCase):
    """Unit tests for ``reconcile()``: staleness is a finding without --write and never with it."""

    def test_reports_a_stale_index_without_write(self):
        """A missing or outdated index is a stale-index finding when not writing."""
        self.write("001-first.md", adr_text())
        findings = reconcile(self.repo_root, write=False)
        self.assertEqual([f.kind for f in findings], ["stale-index"])
        self.assertFalse((self.adr_dir / INDEX_FILENAME).exists())

    def test_writes_the_index_with_write(self):
        """With --write a valid corpus gets its index regenerated and no staleness reported."""
        self.write("001-first.md", adr_text())
        self.assertEqual(reconcile(self.repo_root, write=True), [])
        self.assertTrue(self.index().startswith(INDEX_HEADER))

    def test_does_not_write_while_any_finding_stands(self):
        """A dangling entry stops the write and leaves whatever index was there."""
        self.write("001-first.md", adr_text(scope="[gone/]"))
        (self.adr_dir / INDEX_FILENAME).write_text("untouched\n", encoding="utf-8")
        findings = reconcile(self.repo_root, write=True)
        self.assertEqual([f.kind for f in findings], ["dangling"])
        self.assertEqual(self.index(), "untouched\n")

    def test_is_silent_for_a_clean_current_corpus(self):
        """A valid corpus whose index is current yields no findings either way."""
        self.write("001-first.md", adr_text())
        self.manage()
        self.assertEqual(reconcile(self.repo_root, write=False), [])
        self.assertEqual(reconcile(self.repo_root, write=True), [])


class BindingTests(RepoTestCase):
    """Unit tests for ``binding()``: the reverse lookup, Archived included, directories slashed."""

    def test_matches_a_directory_token_with_or_without_its_slash(self):
        """`scripts/adr` finds an entry `scripts/adr/`, since a directory token is slashed."""
        self.write_scoped("scripts/adr/x.py")
        self.write("001-first.md", adr_text(scope="[scripts/adr/]"))
        self.assertEqual([r.number for r in binding(self.repo_root, ["scripts/adr"])], ["001"])
        self.assertEqual(
            [r.number for r in binding(self.repo_root, ["scripts/adr/x.py"])], ["001"]
        )

    def test_reports_an_archived_decision(self):
        """Archived decisions are in force, so the lookup names them."""
        self.write(
            "001-first.md",
            adr_text(status="Archived", **{"archived-because": "A comment names it."}),
        )
        self.assertEqual(
            [r.status for r in binding(self.repo_root, [SCOPED_FILE])], ["Archived"]
        )

    def test_an_absolute_path_inside_the_root_matches(self):
        """An absolute path, as a hook receives it, is made repo-relative before matching."""
        self.write("001-first.md", adr_text())
        absolute = str(self.repo_root / SCOPED_FILE)
        self.assertEqual([r.number for r in binding(self.repo_root, [absolute])], ["001"])

    def test_a_path_outside_the_root_binds_nothing(self):
        """A path under no managed root is the answer "nothing binds this", not an error."""
        self.write("001-first.md", adr_text())
        self.assertEqual(binding(self.repo_root, ["/nowhere/else.py"]), [])

    def test_warns_that_an_unreadable_adr_binds_nothing(self):
        """This is the only place the lookup speaks, so a silent gap reads as 'nothing binds it'."""
        self.write("001-bad.md", adr_text(status="Draft"))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(binding(self.repo_root, [SCOPED_FILE]), [])
        self.assertIn("001-bad.md could not be read, so it binds nothing here", err.getvalue())

    def test_stays_silent_for_a_path_nothing_binds(self):
        """Most files are bound by nothing, so the common case must not cry wolf."""
        self.write("001-first.md", adr_text())
        self.assertEqual(binding(self.repo_root, ["docs/unrelated.md"]), [])

    def test_omits_a_superseded_decision(self):
        """A replaced decision binds nothing, so surfacing it would be noise."""
        self.write(
            "001-superseded.md", adr_text(status="Superseded", **{"superseded-by": "12"})
        )
        self.assertEqual(binding(self.repo_root, [SCOPED_FILE]), [])

    def test_reports_every_decision_binding_the_path(self):
        """Two ADRs can bind one path, and stopping at the first would hide the second."""
        self.write("001-first.md", adr_text(title="1: Do the thing"))
        self.write("002-second.md", adr_text(title="2: Do another thing"))
        self.assertEqual(len(binding(self.repo_root, [SCOPED_FILE])), 2)

    def test_matches_any_of_several_paths(self):
        """The hook passes every staged path at once, so one match in the set is enough."""
        self.write("001-first.md", adr_text())
        result = binding(self.repo_root, ["docs/unrelated.md", SCOPED_FILE])
        self.assertEqual([r.number for r in result], ["001"])


class MainTests(RepoTestCase):
    """Integration tests through the entry point: exit codes and what is left on disk."""

    def test_check_exits_one_on_a_stale_index_and_writes_nothing(self):
        """`check` is CI's gate: a stale index fails it and the tree is untouched."""
        self.write("001-first.md", adr_text())
        code, _, err = self.run_main("check")
        self.assertEqual(code, 1)
        self.assertIn("stale", err)
        self.assertFalse((self.adr_dir / INDEX_FILENAME).exists())

    def test_index_writes_and_exits_zero(self):
        """`index` regenerates and reports the row count."""
        self.write("001-first.md", adr_text())
        code, out, _ = self.run_main("index")
        self.assertEqual(code, 0)
        self.assertIn("(1 entries)", out)

    def test_reconcile_prints_findings_as_json(self):
        """`reconcile` is the hooks' command and speaks JSON."""
        self.write("001-first.md", adr_text(scope="[gone/]"))
        code, out, _ = self.run_main("reconcile")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual([f["kind"] for f in payload["findings"]], ["dangling"])

    def test_for_names_the_decision_binding_a_path(self):
        """`for` prints one line per binding decision with number, status, title and path."""
        self.write("001-first.md", adr_text())
        code, out, _ = self.run_main("for", SCOPED_FILE)
        self.assertEqual(code, 0)
        self.assertEqual(out, "001 (Accepted): Do the thing — docs/adr/001-first.md\n")

    def test_repo_root_overrides_the_working_directory(self):
        """--repo-root points every command at the given tree."""
        self.write("001-first.md", adr_text())
        elsewhere = Path(self.enterContext(tempfile.TemporaryDirectory()))
        code, out, _ = self.run_main(
            "--repo-root", str(self.repo_root), "for", SCOPED_FILE, cwd=elsewhere
        )
        self.assertEqual(code, 0)
        self.assertIn("001", out)


if __name__ == "__main__":
    unittest.main()
