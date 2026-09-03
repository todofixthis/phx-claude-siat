"""Drift tests: what SKILL.md and adr.py both encode must be one thing.

The Format template, the frontmatter field names, and the command lines the skill tells
the agent to run against the subcommands the tool offers.
"""

import re
import unittest
from pathlib import Path

import adr
from frontmatter import parse_frontmatter

ALLOWED_TOOLS_FIELD = "allowed-tools"
SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"
RE_FORMAT_FENCE = re.compile(r"## Format\n\nFile: .*?\n\n```markdown\n(.*?)```", re.DOTALL)
RE_COMMAND_LINE = re.compile(r"`python3 \$\{CLAUDE_SKILL_DIR\}/adr\.py ([a-z]+)[^`]*`")
RE_FLAG = re.compile(r"--[a-z-]+")


def skill_frontmatter() -> dict:
    """The skill's frontmatter fields, parsed by the parser the tool itself uses."""
    match = adr.RE_FRONTMATTER.match(SKILL.read_text(encoding="utf-8"))
    assert match, "SKILL.md has no frontmatter block"
    fields, problems = parse_frontmatter(match.group(1))
    assert not problems, problems
    return fields


class FormatTemplateTests(unittest.TestCase):
    """The fenced Format block in the skill is the template `new` writes."""

    def test_the_fence_equals_the_template(self):
        """The fence under `## Format` matches `FORMAT_TEMPLATE` byte for byte."""
        text = SKILL.read_text(encoding="utf-8")
        match = RE_FORMAT_FENCE.search(text)
        self.assertIsNotNone(match, "SKILL.md has no fenced Format block")
        self.assertEqual(match.group(1), adr.FORMAT_TEMPLATE)


class FieldNameTests(unittest.TestCase):
    """Every frontmatter field the skill documents exists in the tool."""

    def test_documented_fields_are_known_to_the_tool(self):
        """The bolded field bullets name exactly the fields the tool knows."""
        text = SKILL.read_text(encoding="utf-8")
        documented = set(re.findall(r"^- \*\*`([a-z-]+)`\*\*", text, re.MULTILINE))
        known = {
            "archived-because",
            "date",
            adr.REVISIT_DISCHARGED_BY_FIELD,
            adr.REVISIT_WHEN_FIELD,
            adr.SCOPE_FIELD,
            "status",
            adr.SUMMARY_FIELD,
            adr.SUPERSEDED_BY_FIELD,
        }
        self.assertEqual(documented, known)


class CommandLineTests(unittest.TestCase):
    """Every command line the skill gives names a subcommand, and nothing grants it."""

    def test_the_frontmatter_carries_no_allowed_tools_grant(self):
        """The skill asks for no tool grant.

        Measured 2026-09-03 in headless sessions: a skill carrying `allowed-tools` is
        denied at invocation, and with the invocation allowed the grant still did not
        pre-approve the `adr.py` command. The grant costs a prompt and buys nothing.
        """
        self.assertNotIn(ALLOWED_TOOLS_FIELD, skill_frontmatter())

    def test_every_command_line_names_a_subcommand(self):
        """Every command line the skill gives names a subcommand the tool offers."""
        text = SKILL.read_text(encoding="utf-8")
        commands = RE_COMMAND_LINE.findall(text)
        self.assertTrue(commands, "the skill names no adr.py command")
        known = {
            "check",
            "discharge",
            "for",
            "index",
            "new",
            "reconcile",
            "renumber",
            "supersede",
        }
        self.assertTrue(set(commands) <= known, set(commands) - known)

    def test_every_flag_a_command_line_names_is_an_option_of_its_subcommand(self):
        """A flag the skill tells the agent to pass must exist on that subcommand's parser."""
        text = SKILL.read_text(encoding="utf-8")
        subcommands = adr.build_parser()._subparsers._group_actions[0].choices
        lines = re.findall(r"`python3 \$\{CLAUDE_SKILL_DIR\}/adr\.py ([a-z]+)([^`]*)`", text)
        self.assertTrue(
            any(RE_FLAG.search(rest) for _, rest in lines), "no command names a flag"
        )
        for command, rest in lines:
            with self.subTest(command=command, rest=rest):
                known = set(subcommands[command]._option_string_actions)
                self.assertTrue(
                    set(RE_FLAG.findall(rest)) <= known, set(RE_FLAG.findall(rest)) - known
                )

    def test_every_flag_named_on_its_own_is_an_option_of_some_subcommand(self):
        """A flag the prose names in its own code span exists on one of the subcommands."""
        text = SKILL.read_text(encoding="utf-8")
        subcommands = adr.build_parser()._subparsers._group_actions[0].choices
        known = {flag for sub in subcommands.values() for flag in sub._option_string_actions}
        named = set(re.findall(r"`(--[a-z-]+)[^`]*`", text))
        self.assertTrue(named, "the skill names no flag on its own")
        self.assertTrue(named <= known, named - known)
