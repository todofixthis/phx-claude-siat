"""Unit tests for the coupling between `table.py` and `SKILL.md`'s substitution table.

The skill's rule is that a row and its search ship together. While the table and the
searches sat adjacent in one file that held itself; now the patterns live in code, so
these are what fail when the two drift.

Three assertions, because each closes a hole the others leave: every row must fire
against the US fixture, the row counts must match, and every literal in the skill's US
column must exist in the code.
"""

import re
import unittest
from pathlib import Path

import scan
from table import CLASS_LABELS, ROWS

SKILL_FILE = Path(__file__).resolve().parents[1] / "SKILL.md"
US_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "us"
NZ_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "nz"

RE_TABLE_ROW = re.compile(r"^\|")
RE_BACKTICKED = re.compile(r"`([^`]+)`")
RE_MEMBER = re.compile(r"[a-z]{3,}")


def skill_table_lines() -> list:
    """Return the pipe-prefixed lines of SKILL.md's Substitutions table.

    Structural rather than prose parsing: the section heading bounds it, and the rows are
    the only lines starting with a pipe. The header and its separator are included, and
    the callers below subtract them.
    """
    lines = []
    inside = False
    for line in SKILL_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Substitutions"):
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside and RE_TABLE_ROW.match(line):
            lines.append(line)
    return lines


def skill_data_rows() -> list:
    """Return the table's data rows, without the header and separator."""
    return skill_table_lines()[2:]


class SkillTableParsingTests(unittest.TestCase):
    """Unit tests for the SKILL.md table reader the assertions below depend on."""

    def test_finds_the_table(self):
        """The reader must locate a table at all, or every assertion below passes vacuously."""
        self.assertGreater(len(skill_table_lines()), 2)

    def test_drops_the_header_and_separator(self):
        """Data rows must exclude the two lines that are not substitutions."""
        self.assertEqual(len(skill_data_rows()), len(skill_table_lines()) - 2)


class RowCoverageTests(unittest.TestCase):
    """Unit tests: every row in the code must be reachable by its own pattern."""

    def test_every_row_fires_against_the_us_fixture(self):
        """A row whose pattern is missing or wrong finds nothing, and must fail here."""
        files = sorted(path for path in US_FIXTURE.rglob("*") if path.is_file())
        results = scan.scan(files, US_FIXTURE)
        silent = [row.us for row in ROWS if not results[row]["hits"]]
        self.assertEqual(silent, [], "rows that found nothing in the US fixture")

    def test_the_nz_fixture_yields_only_noise(self):
        """An already-correct tree must produce nothing to triage, or a pattern over-converts."""
        files = sorted(path for path in NZ_FIXTURE.rglob("*") if path.is_file())
        results = scan.scan(files, NZ_FIXTURE)
        leaked = {
            row.us: [hit["token"] for hit in results[row]["hits"]]
            for row in ROWS
            if results[row]["hits"]
        }
        self.assertEqual(leaked, {}, "rows reporting non-noise hits on correct spellings")


class RowCountTests(unittest.TestCase):
    """Unit tests: the code's row count against the skill's.

    This is what catches a row added to SKILL.md with neither a pattern nor a fixture
    word — the case the coverage test above passes happily.
    """

    def test_row_counts_match(self):
        """A row added to one and not the other must fail, whichever side moved."""
        self.assertEqual(len(ROWS), len(skill_data_rows()))


class UsColumnTests(unittest.TestCase):
    """Unit tests: every literal the skill names must exist in the code's table."""

    def test_every_us_literal_is_known(self):
        """A backticked US token must be a class label or appear in some pattern."""
        haystack = " ".join(pattern.regex for row in ROWS for pattern in row.patterns)
        unknown = []
        for line in skill_data_rows():
            us_cell = line.split("|")[1]
            for token in RE_BACKTICKED.findall(us_cell):
                if token in CLASS_LABELS or token in haystack:
                    continue
                unknown.append(token)
        self.assertEqual(unknown, [], "US-column tokens with no counterpart in table.py")

    def test_the_class_label_set_is_used(self):
        """At least two class labels must actually appear, or the allowance hides a gap."""
        cells = " ".join(line.split("|")[1] for line in skill_data_rows())
        present = [label for label in CLASS_LABELS if f"`{label}`" in cells]
        self.assertGreaterEqual(len(present), 2)


class MemberCoverageTests(unittest.TestCase):
    """Integration tests: every word an alternation names must be in the US control.

    Row-level coverage is not enough for the three enumerated rows. `-or`, `-re` and
    `-og` name classes no pattern can express, so their members exist only inside the
    regex — and `SKILL.md` puts them in the NZ column, which nothing parses. Without
    this, most of those words could be deleted from `table.py` and every other test
    would stay green.
    """

    def member_words(self) -> list:
        """Return (row, word) for every literal word an alternation enumerates."""
        found = []
        for row in ROWS:
            for pattern in row.patterns:
                # `\w` is a shape, not a word; strip it before looking for literals.
                for word in RE_MEMBER.findall(pattern.regex.replace(r"\w", "")):
                    found.append((row, word))
        return found

    def test_the_extractor_finds_members(self):
        """The extractor must find words at all, or the assertion below checks nothing."""
        self.assertGreater(len(self.member_words()), 40)

    def test_every_member_appears_in_the_us_fixture(self):
        """A word deleted from an alternation must fail here, not pass unnoticed."""
        text = (US_FIXTURE / "prose.md").read_text(encoding="utf-8").casefold()
        missing = [f"{row.us}: {word}" for row, word in self.member_words() if word not in text]
        self.assertEqual(missing, [], "alternation members absent from the US control")


class GuardTests(unittest.TestCase):
    """Unit tests for ``guard_for()``."""

    def test_returns_the_added_character_for_a_prefix(self):
        """Where the NZ form extends the US one, the guard is the character it adds."""
        self.assertEqual(scan.guard_for("dialog", "dialogue"), "u")

    def test_returns_the_added_character_for_program(self):
        """`programme` adds an `m`, so copying the `-ogue` family's `u` would be wrong."""
        self.assertEqual(scan.guard_for("program", "programme"), "m")

    def test_returns_nothing_where_the_forms_diverge(self):
        """`colour` is not `color` plus a suffix, so no guard is possible."""
        self.assertEqual(scan.guard_for("color", "colour"), "")

    def test_returns_nothing_where_the_nz_form_is_shorter(self):
        """`fulfil` is shorter than `fulfill`, so there is no added character."""
        self.assertEqual(scan.guard_for("fulfill", "fulfil"), "")

    def test_every_table_guard_is_a_single_character(self):
        """A guard longer than one character would not fit the `[^x]` shape that uses it."""
        for row in ROWS:
            for us_word, nz_word in row.nz_forms.items():
                with self.subTest(us=us_word):
                    self.assertIn(len(scan.guard_for(us_word, nz_word)), (0, 1))


if __name__ == "__main__":
    unittest.main()
