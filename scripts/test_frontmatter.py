"""Unit tests for ``parse_frontmatter()``.

`unittest` rather than pytest, so the suite needs no dependency beyond the declared ones
(ADR 035). The module under test is reached through the `scripts/frontmatter.py`
symlink to `skills/writing-adrs/frontmatter.py`, which ships the same tests as its
own `uv run pytest` suite. Run from the repo root:

    uv run python -m unittest discover -s scripts -t . -p 'test_*.py'
"""

import unittest
from unittest import mock

import yaml

from scripts import frontmatter
from scripts.frontmatter import parse_frontmatter


class ParserTestCase(unittest.TestCase):
    """Base for tests of ``parse_frontmatter()``, run once under each loader.

    A subclass sets ``loader`` to patch ``frontmatter.LOADER`` for the whole test;
    ``None`` keeps the loader the module chose, libyaml's where it is built in. The
    bottom of this module adds a ``BaseLoader`` twin of every test class, so CI's libyaml
    never leaves the pure-Python fallback unexercised.
    """

    loader: type | None = None

    def setUp(self) -> None:
        if self.loader is not None:
            patcher = mock.patch.object(frontmatter, "LOADER", self.loader)
            patcher.start()
            self.addCleanup(patcher.stop)


class ScalarTests(ParserTestCase):
    """Scalar values, the shape almost every field takes."""

    def test_parses_scalars_and_ignores_blank_lines(self):
        """A block of `key: value` lines parses cleanly, blank lines and all."""
        fields, problems = parse_frontmatter("status: Accepted\n\n   \ndate: 2026-08-01")
        self.assertEqual(fields, {"status": "Accepted", "date": "2026-08-01"})
        self.assertEqual(problems, [])

    def test_a_colon_space_in_a_plain_value_is_a_problem(self):
        """`: ` inside a plain value is a YAML error, so the value must be quoted."""
        fields, problems = parse_frontmatter("summary: Use mypy, not ty: prefer it")
        self.assertEqual(fields, {})
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("field summary is not valid YAML"), problems)

    def test_strips_whitespace_around_key_and_value(self):
        """Surrounding whitespace belongs to the formatting, not to the value."""
        fields, problems = parse_frontmatter("status :   Accepted   ")
        self.assertEqual(fields, {"status": "Accepted"})
        self.assertEqual(problems, [])


class InlineListTests(ParserTestCase):
    """`scope: [a, b]`, the only inline list any frontmatter here uses."""

    def test_parses_an_inline_list_into_stripped_items(self):
        """`scope: [a, b]` becomes a list, which is the only list-valued field in use."""
        fields, problems = parse_frontmatter("scope: [scripts/,  CHANGELOG.md , docs/adr/]")
        self.assertEqual(fields, {"scope": ["scripts/", "CHANGELOG.md", "docs/adr/"]})
        self.assertEqual(problems, [])

    def test_parses_an_empty_list_as_empty(self):
        """`scope: []` yields no entries rather than one empty entry, which is a real value."""
        fields, problems = parse_frontmatter("scope: []")
        self.assertEqual(fields, {"scope": []})
        self.assertEqual(problems, [])


class WrappedValueTests(ParserTestCase):
    """The silent truncation this parser exists to catch, in each shape it takes."""

    def test_flags_an_indented_continuation_carrying_a_colon(self):
        """An indented wrap whose prose holds a colon must not become a second field."""
        fields, problems = parse_frontmatter(
            "summary: Use mypy, not ty; revisit when\n  ty reaches 1.0: it is not ready"
        )
        self.assertEqual(fields, {"summary": "Use mypy, not ty; revisit when"})
        self.assertEqual(
            problems,
            [
                "continued onto another line; wrap it onto one: 'ty reaches 1.0: it is not ready'"
            ],
        )

    def test_flags_an_indented_continuation_without_a_colon(self):
        """An indented wrap with no colon is a continuation just the same."""
        _, problems = parse_frontmatter("summary: Something long\n  and its remainder")
        self.assertEqual(
            problems, ["continued onto another line; wrap it onto one: 'and its remainder'"]
        )

    def test_flags_an_unindented_continuation_carrying_a_colon(self):
        """A column-0 wrap is caught by its key holding whitespace, not by indentation."""
        fields, problems = parse_frontmatter(
            "summary: Use mypy, not ty; revisit when\nty reaches 1.0: it is not ready"
        )
        self.assertEqual(fields, {"summary": "Use mypy, not ty; revisit when"})
        self.assertEqual(
            problems,
            [
                (
                    "has a key containing whitespace, so it reads as a wrapped line: "
                    "'ty reaches 1.0'"
                )
            ],
        )

    def test_flags_a_line_that_is_not_a_key_value_pair(self):
        """A colon-free line at column 0 is junk, and never silently skipped."""
        _, problems = parse_frontmatter("status: Accepted\nnonsense")
        self.assertEqual(problems, ["is not `key: value`: 'nonsense'"])

    def test_collects_every_problem_rather_than_the_first(self):
        """Two bad lines produce two problems, so one fix does not hide the next."""
        _, problems = parse_frontmatter("nonsense\nalso bad")
        self.assertEqual(
            problems, ["is not `key: value`: 'nonsense'", "is not `key: value`: 'also bad'"]
        )


class BlockSequenceTests(ParserTestCase):
    """Indented `- item` lines, which installed skills use for `allowed-tools`."""

    def test_parses_an_indented_block_sequence(self):
        """Installed skills declare `allowed-tools` this way, so it must not read as a wrap."""
        fields, problems = parse_frontmatter(
            "name: access\nallowed-tools:\n  - Read\n  - Bash(ls *)\ndescription: A skill.\n"
        )
        self.assertEqual(
            fields,
            {
                "name": "access",
                "allowed-tools": ["Read", "Bash(ls *)"],
                "description": "A skill.",
            },
        )
        self.assertEqual(problems, [])

    def test_a_bare_key_with_nothing_under_it_stays_empty(self):
        """A key with no value and no items is empty, not an empty list."""
        fields, problems = parse_frontmatter("description:\n")
        self.assertEqual((fields, problems), ({"description": ""}, []))

    def test_a_wrap_after_a_sequence_key_is_still_caught(self):
        """Only `- item` continues a sequence; prose under the key is still a wrap."""
        _, problems = parse_frontmatter("tools:\n  - Read\nsummary: Long\n  and more\n")
        self.assertEqual(
            problems, ["continued onto another line; wrap it onto one: 'and more'"]
        )


class CommentTests(ParserTestCase):
    """YAML comments, which are legal and must not block a commit."""

    def test_ignores_comments_wherever_they_sit(self):
        """A YAML comment is legal frontmatter and must not block a commit."""
        fields, problems = parse_frontmatter(
            "# why this exists\nstatus: Accepted\n  # an indented note\n"
        )
        self.assertEqual((fields, problems), ({"status": "Accepted"}, []))


class BlockScalarTests(ParserTestCase):
    """`>` and `|`, which open a block this line parser cannot read."""

    def test_flags_every_block_scalar_indicator(self):
        """`>` and `|`, bare or chomped, all open a block this parser cannot read."""
        for indicator in (">", "|", ">-", "|-", ">+", "|+"):
            with self.subTest(indicator=indicator):
                fields, problems = parse_frontmatter(f"summary: {indicator}")
                self.assertEqual(fields, {})
                self.assertEqual(
                    problems, ["field summary uses a block scalar; put it on one line"]
                )

    def test_quoting_a_value_starting_with_an_indicator_reads_it(self):
        """A quoted `> 25 ADRs` is prose, not a block scalar — the pattern is anchored."""
        fields, problems = parse_frontmatter('summary: "> 25 ADRs and counting"')
        self.assertEqual(fields, {"summary": "> 25 ADRs and counting"})
        self.assertEqual(problems, [])


class DuplicateKeyTests(ParserTestCase):
    """A key set twice, where the loser decides nothing but looks like it does."""

    def test_flags_a_repeated_key_and_keeps_the_first(self):
        """A leftover second `status:` would otherwise silently decide the ADR's fate."""
        fields, problems = parse_frontmatter("status: Accepted\nstatus: Archived")
        self.assertEqual(fields, {"status": "Accepted"})
        self.assertEqual(problems, ["sets field status twice; the first value stands"])


class YamlValueTests(ParserTestCase):
    """Values PyYAML decides, which the line rules leave alone."""

    def test_unquotes_a_quoted_flow_sequence_entry(self):
        """A templated path must be quoted in YAML; the parsed entry carries no quotes."""
        fields, problems = parse_frontmatter(
            "scope: ['{{ cookiecutter.github_project_name }}/', docs/]"
        )
        self.assertEqual(
            fields, {"scope": ["{{ cookiecutter.github_project_name }}/", "docs/"]}
        )
        self.assertEqual(problems, [])

    def test_keeps_a_comma_inside_a_quoted_entry(self):
        """A quoted entry holding a comma stays one entry rather than splitting in two."""
        fields, _ = parse_frontmatter('scope: ["a, b/", c/]')
        self.assertEqual(fields, {"scope": ["a, b/", "c/"]})

    def test_resolves_no_types(self):
        """BaseLoader: numbers, booleans and dates stay strings."""
        fields, _ = parse_frontmatter("a: 34\nb: yes\nc: 2026-10-08\nd: [12, 3]")
        self.assertEqual(fields, {"a": "34", "b": "yes", "c": "2026-10-08", "d": ["12", "3"]})

    def test_reports_invalid_yaml_against_its_field(self):
        """`: ` inside a plain value is a YAML error; only that field is lost."""
        fields, problems = parse_frontmatter("status: Accepted\nsummary: Use X: not Y")
        self.assertEqual(fields, {"status": "Accepted"})
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("field summary is not valid YAML"), problems)

    def test_reports_an_unquoted_template_as_invalid_yaml(self):
        """An unquoted `{{` inside a flow sequence is a YAML error, reported against its field."""
        fields, problems = parse_frontmatter("scope: [{{ x }}/]")
        self.assertEqual(fields, {})
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("field scope is not valid YAML"), problems)

    def test_reports_a_mapping_value(self):
        """A mapping loads cleanly but is not text, so the message names it."""
        fields, problems = parse_frontmatter("scope: {a: b}")
        self.assertEqual(fields, {})
        self.assertEqual(
            problems, ["field scope holds a mapping, not text or a list of text; quote it"]
        )

    def test_reports_a_non_text_list_item(self):
        """A nested list is not text, so the message names the item rather than the list."""
        fields, problems = parse_frontmatter("scope: [[a]]")
        self.assertEqual(fields, {})
        self.assertEqual(
            problems,
            [
                (
                    "field scope holds a list holding a non-text item, "
                    "not text or a list of text; quote it"
                )
            ],
        )

    def test_reports_a_quoted_key_rather_than_raising(self):
        """YAML strips a key's quotes, so the field is dropped with a problem, never a KeyError."""
        for line, key in (("'status': Accepted", "'status'"), ('"a": b', '"a"')):
            with self.subTest(line=line):
                self.assertEqual(
                    parse_frontmatter(line),
                    ({}, [f"field {key} has a quoted key; write the key unquoted"]),
                )

    def test_reports_an_inline_comment(self):
        """YAML drops ` #…` without a word, the silent truncation this module exists to catch."""
        for line in ("summary: Issue #12 closes.", "scope: [a/, b/] # note"):
            with self.subTest(line=line):
                fields, problems = parse_frontmatter(line)
                self.assertEqual(fields, {})
                self.assertEqual(len(problems), 1)
                self.assertIn("comment", problems[0])
                self.assertIn("delete the comment", problems[0])

    def test_reports_a_comment_after_a_quoted_value(self):
        """A trailing comment outside quotes is reported, and the fix is to delete it."""
        fields, problems = parse_frontmatter('summary: "x." # note')
        self.assertEqual(fields, {})
        self.assertEqual(len(problems), 1)
        self.assertIn("delete the comment", problems[0])

    def test_reports_a_tag_anchor_or_alias(self):
        """`!x y` and `&x y` both load as `y`, dropping what was written."""
        for line in ("summary: !x y", "summary: &x y", "scope: [&a b/, *a]"):
            with self.subTest(line=line):
                fields, problems = parse_frontmatter(line)
                self.assertEqual(fields, {})
                self.assertEqual(len(problems), 1)

    def test_a_quoted_hash_is_text(self):
        """A `#` inside quotes is text, so quoting is the way out of the comment problem."""
        fields, problems = parse_frontmatter('summary: "Issue #12 closes."')
        self.assertEqual((fields, problems), ({"summary": "Issue #12 closes."}, []))

    def test_a_separator_yaml_splits_on_never_invents_a_field(self):
        """`k: v<sep>x: y` must not parse as two fields: the value is kept or a problem raised."""
        for separator in ("\u2028", "\u2029", "\x85", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e"):
            with self.subTest(separator=separator):
                fields, problems = parse_frontmatter(f"k: v{separator}x: y")
                self.assertNotIn("x", fields)
                self.assertEqual(len(fields) + len(problems), 1, (fields, problems))

    def test_names_a_line_separator_rather_than_a_quoted_key(self):
        """YAML reads two keys across U+2028, U+2029 and \\x85, so the message must not blame quotes."""
        for separator in ("\u2028", "\u2029", "\x85"):
            with self.subTest(separator=separator):
                self.assertEqual(
                    parse_frontmatter(f"k: v{separator}x: y"),
                    (
                        {},
                        [
                            (
                                "field k: YAML reads more than one key here "
                                "(a line separator inside the value?); remove it or quote the value"
                            )
                        ],
                    ),
                )

    def test_reports_a_comment_after_a_block_sequence_item(self):
        """A comment trailing any item of a multi-line field is reported against that field."""
        for block in (
            "tools:\n  - Read # note\n  - Bash",
            "tools:\n  - Read\n  - Bash # c",
        ):
            with self.subTest(block=block):
                fields, problems = parse_frontmatter(block)
                self.assertEqual(fields, {})
                self.assertEqual(len(problems), 1)
                self.assertTrue(problems[0].startswith("field tools holds a comment"), problems)

    def test_a_whole_line_comment_between_items_is_ignored(self):
        """The control for the above: a comment on its own line costs the field nothing."""
        fields, problems = parse_frontmatter("tools:\n  - Read\n  # note\n  - Bash")
        self.assertEqual((fields, problems), ({"tools": ["Read", "Bash"]}, []))

    def test_an_empty_quoted_value_is_an_empty_string(self):
        """`summary: ""` is written text that happens to be empty, not a bare key."""
        self.assertEqual(parse_frontmatter('summary: ""'), ({"summary": ""}, []))

    def test_reports_a_flow_list_split_across_lines(self):
        """A flow list wrapped onto a second line is a wrap, and its field is lost."""
        fields, problems = parse_frontmatter("scope: [a/,\n  b/]")
        self.assertEqual(fields, {})
        self.assertTrue(
            problems[0].startswith("continued onto another line; wrap it onto one"), problems
        )
        self.assertTrue(problems[-1].startswith("field scope is not valid YAML"), problems)


class LoaderTests(unittest.TestCase):
    """Which loader the module picks, run once rather than under each loader."""

    def test_loads_with_libyaml_where_available(self):
        """The fast loader is used when libyaml is built in, the pure-Python one otherwise."""
        self.assertIs(
            frontmatter.LOADER, yaml.CBaseLoader if yaml.__with_libyaml__ else yaml.BaseLoader
        )


class LoaderDifferenceTests(unittest.TestCase):
    """Inputs the two loaders decide differently, pinned so the difference stays known."""

    def parse_under(self, loader: type, block: str) -> tuple:
        with mock.patch.object(frontmatter, "LOADER", loader):
            return parse_frontmatter(block)

    def test_a_tab_inside_a_plain_value(self):
        """libyaml keeps the tab; the pure-Python scanner rejects it as a YAML error."""
        fields, problems = self.parse_under(yaml.CBaseLoader, "k: a\tb")
        self.assertEqual((fields, problems), ({"k": "a\tb"}, []))
        fields, problems = self.parse_under(yaml.BaseLoader, "k: a\tb")
        self.assertEqual(fields, {})
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("field k is not valid YAML"), problems)

    def test_a_byte_order_mark_inside_a_value(self):
        """libyaml keeps the mark; the pure-Python scanner reports a false comment."""
        fields, problems = self.parse_under(yaml.CBaseLoader, "k: a\ufeffb")
        self.assertEqual((fields, problems), ({"k": "a\ufeffb"}, []))
        fields, problems = self.parse_under(yaml.BaseLoader, "k: a\ufeffb")
        self.assertEqual(fields, {})
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("field k holds a comment"), problems)


def _add_base_loader_twins() -> None:
    """Add a ``BaseLoader`` twin of each parser test class, so the fallback is exercised."""
    for name, cls in list(globals().items()):
        if (
            isinstance(cls, type)
            and issubclass(cls, ParserTestCase)
            and cls is not ParserTestCase
        ):
            twin = type(f"{name}BaseLoader", (cls,), {"loader": yaml.BaseLoader})
            globals()[twin.__name__] = twin


_add_base_loader_twins()


if __name__ == "__main__":
    unittest.main()
