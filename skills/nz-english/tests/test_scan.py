"""Tests for `scan.py` — discovery, classification, the report, and the exit codes.

Unit classes call one function directly; `MainTests` reaches the whole tool through its
entry point and covers only what emerges from the composition, chiefly which exit code a
run produces.

The module resolves its own directory from `__file__` so it finds the fixtures it ships
with wherever the plugin is installed, and every function below takes the directory it
works on. No test changes the working directory, and none can reach the real repository
by omitting a path — the argument is required. This follows the anchoring rule the repo
applies to `scripts/`, one step further out: the anchor is read on the `__main__` line
alone, and `own_dir` is threaded below it.

Both anchor tests that rule asks for are written here, the second in the form the rule
gives for a module shipped under `skills/`: the anchor names the files the skill bundles.
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import scan
from table import ROWS

OWN_DIR = Path(__file__).resolve().parents[1]


def write(root: Path, name: str, text: str) -> Path:
    """Create a file under `root`, parents included, and return it."""
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def git_init(root: Path) -> None:
    """Turn `root` into a git repository, ignoring the developer's global config.

    A `core.excludesFile` or `GIT_CONFIG_GLOBAL` in the environment can make
    `--exclude-standard` drop fixture files, which passes locally and fails in CI, or the
    reverse.
    """
    env = {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(root),
    }
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=env)


class TempTreeTestCase(unittest.TestCase):
    """A temporary directory standing in for a swept tree, living for one test."""

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)


class TokenAtTests(unittest.TestCase):
    """Unit tests for ``token_at()``."""

    def test_returns_the_whole_snake_case_identifier(self):
        """A match inside an identifier must report the identifier a reader would rename."""
        line = "def show_dialog(x):"
        self.assertEqual(scan.token_at(line, 9, 15), "show_dialog")

    def test_returns_the_bare_word_when_it_stands_alone(self):
        """A word with no surrounding identifier characters is its own token."""
        self.assertEqual(scan.token_at("the color red", 4, 9), "color")

    def test_includes_digits(self):
        """`gray400` is one name, so the digits belong to the token."""
        self.assertEqual(scan.token_at("text-gray400", 5, 9), "gray400")


class WordAtTests(unittest.TestCase):
    """Unit tests for ``word_at()``."""

    def test_stops_at_an_underscore(self):
        """The noise list holds words, so an underscore must end the run."""
        line = "test_anchor_as_literal_text"
        start = line.index("liter")
        self.assertEqual(scan.word_at(line, start, start + 5), "literal")

    def test_stops_at_a_digit(self):
        """`gray400` contains the word `gray`, not `gray400`."""
        self.assertEqual(scan.word_at("text-gray400", 5, 9), "gray")


class IsNoiseTests(unittest.TestCase):
    """Unit tests for ``is_noise()``."""

    def test_accepts_a_listed_word(self):
        """A word on the list is noise."""
        self.assertTrue(scan.is_noise("literal"))

    def test_is_case_folded(self):
        """`Literal` at the start of a sentence must classify like `literal`."""
        self.assertTrue(scan.is_noise("Literal"))

    def test_accepts_a_simple_plural(self):
        """A trailing `s` is stripped, so `parameters` matches the listed `parameter`."""
        self.assertTrue(scan.is_noise("parameters"))

    def test_rejects_a_real_hit_hiding_among_the_noise(self):
        """`colorist` keeps its `u` in NZ English, so it must never be suppressed."""
        self.assertFalse(scan.is_noise("colorist"))

    def test_rejects_the_other_documented_trap(self):
        """`behaviorist` is the second word the skill warns is a hit, not noise."""
        self.assertFalse(scan.is_noise("behaviorist"))


class UnderOwnSkillTests(unittest.TestCase):
    """Unit tests for ``under_own_skill()``."""

    def test_matches_a_descendant_of_the_given_directory(self):
        """A sweep of the tree the tool ships from must exclude the tool."""
        self.assertTrue(scan.under_own_skill(OWN_DIR / "table.py", OWN_DIR))

    def test_matches_by_path_segment_from_elsewhere(self):
        """A cached copy sweeping a checkout must still exclude that checkout's copy."""
        elsewhere = Path("/somewhere/else/skills/nz-english")
        target = Path("/home/dev/repo/skills/nz-english/SKILL.md")
        self.assertTrue(scan.under_own_skill(target, elsewhere))

    def test_leaves_an_unrelated_path_alone(self):
        """A file outside the skill must not be excluded."""
        self.assertFalse(scan.under_own_skill(Path("/home/dev/repo/src/app.py"), OWN_DIR))


class IsExcludedTests(TempTreeTestCase):
    """Unit tests for ``is_excluded()``."""

    def test_excludes_a_lock_file(self):
        """Lock files hold external package names, which are not ours to respell."""
        self.assertTrue(scan.is_excluded(self.root / "uv.lock", OWN_DIR))

    def test_excludes_the_changelog(self):
        """A changelog records text users already received, so respelling one falsifies it."""
        self.assertTrue(scan.is_excluded(self.root / "CHANGELOG.md", OWN_DIR))

    def test_keeps_an_ordinary_file(self):
        """Anything else is in scope."""
        self.assertFalse(scan.is_excluded(self.root / "README.md", OWN_DIR))


class DiscoverTests(TempTreeTestCase):
    """Unit tests for ``discover()`` — two files everywhere, so a partial pass shows."""

    def test_uses_git_inside_a_repository(self):
        """Discovery must go through git where it can, so `.gitignore` is honoured."""
        git_init(self.root)
        write(self.root, "a.md", "color")
        write(self.root, "b.md", "color")
        paths, used_git = scan.discover([self.root], OWN_DIR)
        self.assertTrue(used_git)
        self.assertEqual([path.name for path in paths], ["a.md", "b.md"])

    def test_honours_gitignore(self):
        """An ignored file must not reach the report, or `node_modules` floods it."""
        git_init(self.root)
        write(self.root, ".gitignore", "skipme.md\n")
        write(self.root, "keep.md", "color")
        write(self.root, "skipme.md", "color")
        paths, _ = scan.discover([self.root], OWN_DIR)
        self.assertEqual([path.name for path in paths], [".gitignore", "keep.md"])

    def test_falls_back_to_a_walk_outside_a_repository(self):
        """A directory that is not a repository must still be swept."""
        write(self.root, "a.md", "color")
        write(self.root, "b.md", "color")
        paths, used_git = scan.discover([self.root], OWN_DIR)
        self.assertFalse(used_git)
        self.assertEqual([path.name for path in paths], ["a.md", "b.md"])

    def test_accepts_a_file_as_a_target(self):
        """A path that is a file is taken as given rather than walked."""
        target = write(self.root, "a.md", "color")
        paths, _ = scan.discover([target], OWN_DIR)
        self.assertEqual(paths, [target.resolve()])

    def test_skips_a_binary_file(self):
        """A NUL byte marks a file whose contents are not prose."""
        (self.root / "bin.dat").write_bytes(b"color\0color")
        write(self.root, "a.md", "color")
        paths, _ = scan.discover([self.root], OWN_DIR)
        self.assertEqual([path.name for path in paths], ["a.md"])

    def test_reports_a_missing_path(self):
        """A path that does not exist is an error, never an empty clean result."""
        with self.assertRaises(scan.ScanError):
            scan.discover([self.root / "nope"], OWN_DIR)


class ScanFunctionTests(TempTreeTestCase):
    """Unit tests for ``scan()``."""

    def test_every_row_is_present_even_with_no_hits(self):
        """A row that found nothing must still appear, or silence looks like absence."""
        path = write(self.root, "a.md", "nothing to see")
        results = scan.scan([path], self.root)
        self.assertEqual(set(results), set(ROWS))

    def test_attributes_one_token_to_every_matching_row(self):
        """`colorize` needs both conversions, so it must appear under both rows."""
        path = write(self.root, "a.md", "colorize")
        results = scan.scan([path], self.root)
        claimed = [row.us for row in ROWS if results[row]["hits"]]
        self.assertEqual(claimed, ["-ize / -ization", "-or endings"])

    def test_records_the_span_and_the_token_separately(self):
        """The span says which row claimed the hit; the token is what a reader renames."""
        path = write(self.root, "a.md", "def show_dialog(x):")
        results = scan.scan([path], self.root)
        row = next(row for row in ROWS if row.us == "-og endings")
        hit = results[row]["hits"][0]
        self.assertEqual((hit["span"], hit["token"]), ("dialog", "show_dialog"))

    def test_counts_noise_without_reporting_it_as_a_hit(self):
        """Documented noise is suppressed from triage but never dropped from the count."""
        path = write(self.root, "a.md", "a literal thing")
        results = scan.scan([path], self.root)
        row = next(row for row in ROWS if row.us == "-er endings (root words)")
        self.assertEqual(
            (results[row]["hits"], dict(results[row]["noise"])), ([], {"literal": 1})
        )

    def test_the_og_guard_lets_the_correct_form_through(self):
        """`catalogue` is already correct, so the guard must keep it out of the report."""
        path = write(self.root, "a.md", "catalogue")
        results = scan.scan([path], self.root)
        row = next(row for row in ROWS if row.us == "-og endings")
        self.assertEqual(results[row]["hits"], [])

    def test_the_og_guard_still_catches_an_inflection(self):
        """Anchoring the right end would drop `cataloged`, which is why the guard is a class."""
        path = write(self.root, "a.md", "cataloged")
        results = scan.scan([path], self.root)
        row = next(row for row in ROWS if row.us == "-og endings")
        self.assertEqual([hit["token"] for hit in results[row]["hits"]], ["cataloged"])

    def test_scans_two_files(self):
        """A subject that read only the first path would pass every other test here."""
        first = write(self.root, "a.md", "gray")
        second = write(self.root, "b.md", "gray")
        results = scan.scan([first, second], self.root)
        row = next(row for row in ROWS if row.us == "gray")
        self.assertEqual([hit["path"] for hit in results[row]["hits"]], ["a.md", "b.md"])

    def test_reports_the_line_a_hit_is_on(self):
        """The line number is the whole navigational value, and line 1 hides an off-by-one."""
        path = write(self.root, "a.md", "nothing\nnothing\nthe gray thing\n")
        results = scan.scan([path], self.root)
        row = next(row for row in ROWS if row.us == "gray")
        self.assertEqual([hit["line"] for hit in results[row]["hits"]], [3])

    def test_restarts_line_numbering_for_each_file(self):
        """A counter that failed to reset would number the second file from the first's end."""
        first = write(self.root, "a.md", "nothing\ngray\n")
        second = write(self.root, "b.md", "gray\n")
        results = scan.scan([first, second], self.root)
        row = next(row for row in ROWS if row.us == "gray")
        self.assertEqual([hit["line"] for hit in results[row]["hits"]], [2, 1])

    def test_finds_a_us_spelling_whatever_its_case(self):
        """The sweep is case-insensitive, which is what the `-og` blind spot depends on."""
        path = write(self.root, "a.md", "Gray")
        results = scan.scan([path], self.root)
        row = next(row for row in ROWS if row.us == "gray")
        self.assertEqual([hit["token"] for hit in results[row]["hits"]], ["Gray"])

    def test_catches_a_camel_cased_og_name(self):
        """`dialogUrl` needs converting, and the guard is case-sensitive so it is reported.

        The hand-run version of this skill could not reach this shape and documented it
        as a permanent miss. Pinned so a "simplification" of the guard to a plain `(?!u)`
        reopens it visibly.
        """
        path = write(self.root, "a.py", "dialogUrl = 1")
        results = scan.scan([path], self.root)
        row = next(row for row in ROWS if row.us == "-og endings")
        self.assertEqual([hit["token"] for hit in results[row]["hits"]], ["dialogUrl"])

    def test_still_leaves_the_correct_lowercase_form_alone(self):
        """The guard's whole job is letting `catalogue` through; case-sensitivity must not
        cost that."""
        path = write(self.root, "a.md", "catalogue and Catalogue")
        results = scan.scan([path], self.root)
        row = next(row for row in ROWS if row.us == "-og endings")
        self.assertEqual(results[row]["hits"], [])

    def test_reports_a_screaming_case_form_as_the_accepted_cost(self):
        """`DIALOGUE` is already correct but comes back, which is the trade the guard makes."""
        path = write(self.root, "a.py", "DIALOGUE = 1")
        results = scan.scan([path], self.root)
        row = next(row for row in ROWS if row.us == "-og endings")
        self.assertEqual([hit["token"] for hit in results[row]["hits"]], ["DIALOGUE"])

    def test_a_decode_error_does_not_stop_the_run(self):
        """A stray non-UTF-8 byte must not exit 2, which the skill escalates as a breakage."""
        (self.root / "a.md").write_bytes(b"the color \xff red")
        results = scan.scan([self.root / "a.md"], self.root)
        row = next(row for row in ROWS if row.us == "-or endings")
        self.assertEqual([hit["token"] for hit in results[row]["hits"]], ["color"])


class RenderTests(TempTreeTestCase):
    """Unit tests for ``render()`` — the text a maintainer actually reads."""

    def test_prints_every_row(self):
        """All seventeen rows print, so the footer is never the only evidence one ran."""
        path = write(self.root, "a.md", "nothing")
        report = scan.render(scan.scan([path], self.root), [path], self.root, False, False)
        for row in ROWS:
            with self.subTest(row=row.us):
                self.assertIn(f"{row.us} → {row.nz}", report)

    def test_the_footer_totals_match_the_rows(self):
        """The footer must equal the sum of the row headers a reader can see above it.

        Summed by parsing those headers, not by recomputing from the same results the
        renderer was handed — otherwise this asserts the renderer's arithmetic against
        itself and a wrong per-row count passes.
        """
        path = write(self.root, "a.md", "colorize and a literal gray")
        report = scan.render(scan.scan([path], self.root), [path], self.root, False, False)
        counted = re.findall(r"\[(\d+) to triage, (\d+) noise\]", report)
        self.assertTrue(counted, "no row headers found to sum")
        hits = sum(int(pair[0]) for pair in counted)
        noise = sum(int(pair[1]) for pair in counted)
        self.assertIn(f"{hits} to triage, {noise} noise suppressed", report)

    def test_marks_a_whole_judgement_row(self):
        """`license` needs reading whichever pattern matched, so the mark carries no span."""
        path = write(self.root, "a.md", "the license")
        report = scan.render(scan.scan([path], self.root), [path], self.root, False, False)
        header = next(line for line in report.splitlines() if line.startswith("license (noun)"))
        self.assertTrue(header.endswith("*judgement"), header)

    def test_names_the_span_on_a_mixed_row(self):
        """Only `meter` needs reading on the `-er` row, so the mark must name it."""
        path = write(self.root, "a.md", "a kilometer")
        report = scan.render(scan.scan([path], self.root), [path], self.root, False, False)
        self.assertIn("*judgement: meter", report)

    def test_collapses_noise_by_default(self):
        """The default report names the noise words and their counts on one line."""
        path = write(self.root, "a.md", "a literal literal thing")
        report = scan.render(scan.scan([path], self.root), [path], self.root, False, False)
        self.assertIn("noise (2): literal ×2", report)

    def test_expands_noise_on_request(self):
        """`--show-noise` lists each suppressed word so a suspected hit can be checked."""
        path = write(self.root, "a.md", "a literal thing")
        report = scan.render(scan.scan([path], self.root), [path], self.root, False, True)
        self.assertIn("noise: literal ×1", report)

    def test_names_the_agent_instructions_it_found(self):
        """A stated US convention overrides the skill, so the reader is told what to read.

        Two files, and a nested one, because the skill tells the reader to look for both
        names and for any nested file covering the subtree being swept.
        """
        first = write(self.root, "AGENTS.md", "nothing")
        second = write(self.root, "sub/CLAUDE.md", "nothing")
        paths = [first, second]
        report = scan.render(scan.scan(paths, self.root), paths, self.root, False, False)
        self.assertIn("agent instructions: AGENTS.md, sub/CLAUDE.md", report)

    def test_caps_the_hits_it_lists(self):
        """An uncapped report is ruinous to read, so the listing is cut past the limit."""
        path = write(self.root, "a.md", "\n".join(["gray"] * 5))
        report = scan.render(scan.scan([path], self.root), [path], self.root, False, False, 2)
        self.assertIn("… 3 more not shown", report)

    def test_the_capped_row_still_counts_every_hit(self):
        """Only the listing is cut; a reader must be able to trust the number."""
        path = write(self.root, "a.md", "\n".join(["gray"] * 5))
        report = scan.render(scan.scan([path], self.root), [path], self.root, False, False, 2)
        self.assertIn("[5 to triage, 0 noise]", report)

    def test_reports_how_many_files_it_read_and_how(self):
        """The file count is the only signal separating a clean tree from an unread one."""
        path = write(self.root, "a.md", "nothing")
        report = scan.render(scan.scan([path], self.root), [path], self.root, True, False)
        self.assertIn(f"swept: {self.root} (1 files, git)", report)

    def test_says_so_when_no_agent_instructions_exist(self):
        """Absence must be stated, not left as a blank a reader reads as an error."""
        path = write(self.root, "a.md", "nothing")
        report = scan.render(scan.scan([path], self.root), [path], self.root, False, False)
        self.assertIn("agent instructions: none found", report)


class VerifyMatchesTests(unittest.TestCase):
    """Unit tests for ``verify_matches()``."""

    def test_finds_the_row_and_guard_for_a_dialog_name(self):
        """A renamed `-ogue` name must resolve to its row and the `u` it added."""
        matches = scan.verify_matches("show_dialog")
        self.assertEqual(
            [(row.us, word, guard) for row, word, guard in matches],
            [("-og endings", "dialog", "u")],
        )

    def test_finds_program_with_its_own_guard(self):
        """`programme` adds an `m`, which must not be copied from the `-ogue` family."""
        matches = scan.verify_matches("run_program")
        self.assertEqual([guard for _, _, guard in matches], ["m"])

    def test_returns_nothing_for_an_unknown_name(self):
        """An unrecognised name must yield no search, so the caller can refuse to run one."""
        self.assertEqual(scan.verify_matches("frobnicate"), [])

    def test_every_row_is_reachable(self):
        """Verify must work for all seventeen rows, not the few with a literal pattern.

        A row nothing can reach makes the tool refuse a correct rename as a typo, which
        it did for `-re`, `-or`, `-ize` and most others before the lookup ran each row's
        own regex.
        """
        sample = {
            "-ize / -ization": "old_colorize",
            "-yze": "old_analyze",
            "-or endings": "color_map",
            "-er endings (root words)": "old_center",
            "-og endings": "show_dialog",
            "-eled / -eling / -eler": "labeled_item",
            "gray": "gray_scale",
            "defense / offense / pretense": "defense_layer",
            "skeptic": "skeptic_mode",
            "judgment / acknowledgment": "judgment_call",
            "license (noun)": "license_key",
            "practice (verb)": "practice_run",
            "program": "program_id",
            "aluminum / artifact / aging": "artifact_store",
            "fulfill / enroll": "fulfill_order",
            "fulfillment / enrollment": "fulfillment_id",
            "sizable": "sizable_chunk",
        }
        unreachable = []
        for row in ROWS:
            name = sample[row.us]
            if not any(hit is row for hit, _span, _guard in scan.verify_matches(name)):
                unreachable.append(f"{row.us} (via {name})")
        self.assertEqual(unreachable, [], "rows --verify cannot reach")

    def test_a_name_claimed_by_two_rows_reports_both(self):
        """`catalog_program` sits in two rows, and both must be named."""
        matches = scan.verify_matches("catalog_program")
        self.assertEqual([row.us for row, _s, _g in matches], ["-og endings", "program"])


class RunVerifyTests(TempTreeTestCase):
    """Unit tests for ``run_verify()`` — the report, not just the exit code."""

    def test_reports_one_block_for_a_name_two_rows_claim(self):
        """One search per name: two rows must not print the same line twice."""
        path = write(self.root, "a.py", "catalog_program()\n")
        report, _code = scan.run_verify(["catalog_program"], [path], self.root)
        self.assertEqual(report.count("a.py:1"), 1)

    def test_counts_each_surviving_reference_once(self):
        """The footer is a count of references, so a two-row name must not double it."""
        path = write(self.root, "a.py", "catalog_program()\n")
        report, _code = scan.run_verify(["catalog_program"], [path], self.root)
        self.assertIn("1 surviving reference(s).", report)

    def test_names_every_row_that_claimed_the_name(self):
        """A reader needs to know which substitutions the name is subject to."""
        path = write(self.root, "a.py", "catalog_program()\n")
        report, _code = scan.run_verify(["catalog_program"], [path], self.root)
        self.assertIn("-og endings → -ogue, program → programme", report)

    def test_says_when_a_guard_was_applied(self):
        """The guard is why a correct conversion is absent, so the report must say so."""
        path = write(self.root, "a.py", "show_dialog(x)\n")
        report, _code = scan.run_verify(["show_dialog"], [path], self.root)
        self.assertIn("guarded against a following 'u'", report)

    def test_searches_two_files(self):
        """A reference in the second file must be found, not just the first."""
        first = write(self.root, "a.py", "show_dialog(x)\n")
        second = write(self.root, "b.py", "show_dialog(y)\n")
        report, _code = scan.run_verify(["show_dialog"], [first, second], self.root)
        self.assertIn("2 surviving reference(s).", report)


class RunSelfCheckTests(TempTreeTestCase):
    """Unit tests for ``run_self_check()`` — the text it prints and the code it returns."""

    def test_reports_success_against_the_bundled_fixtures(self):
        """The shipped control must pass and say which way it passed."""
        report, code = scan.run_self_check(OWN_DIR)
        self.assertEqual(code, scan.EXIT_CLEAN)
        self.assertIn("every row fired against the US fixture", report)

    def test_reports_a_missing_fixture_rather_than_passing(self):
        """A broken install must fail loudly; a silent pass is the failure to avoid."""
        with self.assertRaises(scan.ScanError):
            scan.run_self_check(self.root)


class JudgementMarkTests(unittest.TestCase):
    """Unit tests for ``judgement_mark()``."""

    def test_marks_a_whole_row_where_no_span_is_named(self):
        """`license` needs reading whichever pattern matched, so the mark names no span."""
        row = next(row for row in ROWS if row.us == "license (noun)")
        self.assertEqual(scan.judgement_mark(row), "  *judgement")

    def test_names_the_span_on_a_mixed_row(self):
        """Only `meter` needs reading on the `-er` row, so the mark must say which."""
        row = next(row for row in ROWS if row.us == "-er endings (root words)")
        self.assertEqual(scan.judgement_mark(row), "  *judgement: meter")

    def test_leaves_an_ordinary_row_unmarked(self):
        """A row nothing needs read on carries no mark."""
        row = next(row for row in ROWS if row.us == "gray")
        self.assertEqual(scan.judgement_mark(row), "")


class CommonBaseTests(TempTreeTestCase):
    """Unit tests for ``common_base()``."""

    def test_a_single_target_is_its_own_base(self):
        """One target means every path is shown relative to it."""
        self.assertEqual(scan.common_base([self.root]), self.root)

    def test_two_targets_use_their_common_ancestor(self):
        """The header must name somewhere the swept files live, not the working directory."""
        (self.root / "one").mkdir()
        (self.root / "two").mkdir()
        self.assertEqual(scan.common_base([self.root / "one", self.root / "two"]), self.root)


class OwnDirAnchorTests(unittest.TestCase):
    """Unit tests for the anchor `__main__` passes as `own_dir`.

    These read the anchor rather than calling the subject, because what is under test is
    the expression itself.
    """

    def test_a_moved_working_directory_cannot_redirect_it(self):
        """The anchor is absolute and independent of cwd, so a chdir cannot rebase it."""
        anchor = Path(scan.__file__).resolve().parent
        with TemporaryDirectory() as tmp:
            import os

            here = os.getcwd()
            os.chdir(tmp)
            self.addCleanup(os.chdir, here)
            self.assertTrue(anchor.is_absolute())
            self.assertNotEqual(anchor, Path(tmp).resolve())

    def test_the_anchor_holds_the_bundled_files(self):
        """The anchor must name the directory the fixtures and the table actually live in."""
        anchor = Path(scan.__file__).resolve().parent
        self.assertTrue((anchor / "table.py").is_file())
        self.assertTrue((anchor / "tests" / "fixtures" / "us").is_dir())


class MainTests(TempTreeTestCase):
    """Integration tests: the exit code a whole run produces."""

    def test_a_clean_tree_exits_zero(self):
        """Nothing to triage is exit 0."""
        write(self.root, "a.md", "nothing here")
        self.assertEqual(scan.main([str(self.root)], OWN_DIR), scan.EXIT_CLEAN)

    def test_a_noise_only_tree_exits_zero(self):
        """Documented noise needs no decision, so it is not a reason to exit 1."""
        write(self.root, "a.md", "a literal thing")
        self.assertEqual(scan.main([str(self.root)], OWN_DIR), scan.EXIT_CLEAN)

    def test_a_tree_with_hits_exits_one(self):
        """Anything needing triage is exit 1."""
        write(self.root, "a.md", "gray")
        self.assertEqual(scan.main([str(self.root)], OWN_DIR), scan.EXIT_HITS)

    def test_a_judgement_only_tree_exits_one(self):
        """Judgement hits need reading, and reading is triage."""
        write(self.root, "a.md", "the license")
        self.assertEqual(scan.main([str(self.root)], OWN_DIR), scan.EXIT_HITS)

    def test_a_missing_path_exits_two(self):
        """A failed run is exit 2, which the skill escalates rather than believes."""
        self.assertEqual(scan.main([str(self.root / "nope")], OWN_DIR), scan.EXIT_ERROR)

    def test_an_unknown_verify_name_exits_three(self):
        """A mistyped name is the caller's error, not a broken tool."""
        write(self.root, "a.md", "nothing")
        code = scan.main(["--verify", "frobnicate", str(self.root)], OWN_DIR)
        self.assertEqual(code, scan.EXIT_USAGE)

    def test_verify_with_show_noise_exits_three(self):
        """Surviving references carry no noise, so the flag is refused rather than ignored."""
        write(self.root, "a.md", "nothing")
        code = scan.main(["--verify", "show_dialog", "--show-noise", str(self.root)], OWN_DIR)
        self.assertEqual(code, scan.EXIT_USAGE)

    def test_verify_finds_a_missed_reference(self):
        """The name that was not renamed must come back."""
        write(self.root, "a.py", "show_dialogue(x)\nshow_dialog(y)\n")
        code = scan.main(["--verify", "show_dialog", str(self.root)], OWN_DIR)
        self.assertEqual(code, scan.EXIT_HITS)

    def test_verify_ignores_the_conversions_it_made(self):
        """A tree where every reference moved must come back clean, not full of successes."""
        write(self.root, "a.py", "show_dialogue(x)\nshow_dialogue(y)\n")
        code = scan.main(["--verify", "show_dialog", str(self.root)], OWN_DIR)
        self.assertEqual(code, scan.EXIT_CLEAN)

    def test_self_check_passes_against_the_bundled_fixtures(self):
        """The shipped control must pass, or every negative test above means nothing."""
        self.assertEqual(scan.main(["--self-check"], OWN_DIR), scan.EXIT_CLEAN)

    def test_self_check_refuses_other_arguments(self):
        """`--self-check` reads its own fixtures, so a path alongside it is a mistake."""
        code = scan.main(["--self-check", "--show-noise"], OWN_DIR)
        self.assertEqual(code, scan.EXIT_USAGE)

    def test_a_tree_with_nothing_readable_exits_two(self):
        """Zero files searched is a failed run, not a clean one — the whole point of this tool."""
        write(self.root, "CHANGELOG.md", "gray")
        self.assertEqual(scan.main([str(self.root / "CHANGELOG.md")], OWN_DIR), scan.EXIT_ERROR)

    def test_a_broken_bundle_exits_two_not_one(self):
        """A missing table.py must escalate, not arrive wearing the shape of a hit count.

        Run as a subprocess because the failure is at import time, which cannot happen
        twice in one interpreter.
        """
        stand_in = self.root / "scan.py"
        stand_in.write_bytes((OWN_DIR / "scan.py").read_bytes())
        result = subprocess.run(
            [sys.executable, str(stand_in), str(self.root)],
            capture_output=True,
            # The non-zero exit is the assertion; raising on it would defeat the test.
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, scan.EXIT_ERROR)

    def test_a_mistyped_flag_exits_three_not_two(self):
        """argparse exits 2 by default, which this tool reserves for a failed run."""
        result = subprocess.run(
            [sys.executable, str(OWN_DIR / "scan.py"), "--verifyy", "x"],
            capture_output=True,
            # As above: the exit code is what is under test.
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, scan.EXIT_USAGE)

    def test_self_check_exits_two_when_a_fixture_is_missing(self):
        """A broken install is a failure to escalate, not a tree with nothing to convert."""
        self.assertEqual(scan.main(["--self-check"], self.root), scan.EXIT_ERROR)


if __name__ == "__main__":
    unittest.main()
