"""Drift tests: what SKILL.md and adr.py both encode must be one thing.

The Format template, the frontmatter field names, and the command lines the skill tells
the agent to run against the `allowed-tools` rule that pre-approves them.
"""

import re
import unittest
from pathlib import Path

import adr

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"
RE_FORMAT_FENCE = re.compile(r"## Format\n\nFile: .*?\n\n```markdown\n(.*?)```", re.DOTALL)
RE_COMMAND_LINE = re.compile(r"`python3 \$\{CLAUDE_SKILL_DIR\}/adr\.py ([a-z]+)[^`]*`")
RE_ALLOWED = re.compile(r"^allowed-tools: (.*)$", re.MULTILINE)


class FormatTemplateTests(unittest.TestCase):
    """The fenced Format block in the skill is the template `new` writes."""

    def test_the_fence_equals_the_template(self):
        text = SKILL.read_text(encoding="utf-8")
        match = RE_FORMAT_FENCE.search(text)
        self.assertIsNotNone(match, "SKILL.md has no fenced Format block")
        self.assertEqual(match.group(1), adr.FORMAT_TEMPLATE)


class FieldNameTests(unittest.TestCase):
    """Every frontmatter field the skill documents exists in the tool."""

    def test_documented_fields_are_known_to_the_tool(self):
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


class AllowedToolsTests(unittest.TestCase):
    """Every command line the skill gives matches the rule that pre-approves it."""

    def test_every_command_line_matches_the_rule(self):
        text = SKILL.read_text(encoding="utf-8")
        rule = RE_ALLOWED.search(text)
        self.assertIsNotNone(rule)
        self.assertEqual(rule.group(1).strip(), "Bash(python3 ${CLAUDE_SKILL_DIR}/adr.py:*)")
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
