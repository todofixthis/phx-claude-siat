"""Smoke tests for ``scripts.frontmatter``, the symlink into the writing-adrs skill.

The parser's own cases live once, in `skills/writing-adrs/tests/test_frontmatter.py`, which
CI's `python` job runs on any change to the parser. What only this suite can show is that
`scripts/` reaches that module through its symlink and runs it on the dependencies
`scripts/pyproject.toml` declares (ADR 035). Run from the repo root:

    uv run python -m unittest discover -s scripts -t . -p 'test_*.py'
"""

import unittest
from pathlib import Path

from scripts import frontmatter

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_PARSER = REPO_ROOT / "skills" / "writing-adrs" / "frontmatter.py"


class SymlinkTests(unittest.TestCase):
    """Unit tests for how ``scripts.frontmatter`` reaches the skill's parser."""

    def test_resolves_to_the_skills_parser(self):
        """A copy in place of the symlink would drift from the parser the ADR tool runs."""
        self.assertTrue((REPO_ROOT / "scripts" / "frontmatter.py").is_symlink())
        self.assertEqual(Path(frontmatter.__file__).resolve(), SKILL_PARSER)


class ParseFrontmatterTests(unittest.TestCase):
    """Unit tests for ``parse_frontmatter()`` as `scripts/` imports it."""

    def test_parses_a_block_on_the_declared_dependencies(self):
        """A quoted templated scope entry needs PyYAML, so this fails if scripts/ lacks it."""
        self.assertEqual(
            frontmatter.parse_frontmatter(
                "status: Accepted\nscope: ['{{ cookiecutter.github_project_name }}/', docs/]"
            ),
            (
                {
                    "status": "Accepted",
                    "scope": ["{{ cookiecutter.github_project_name }}/", "docs/"],
                },
                [],
            ),
        )

    def test_reports_a_problem_rather_than_raising(self):
        """Callers such as validate_manifests.py rely on problems coming back, not exceptions."""
        fields, problems = frontmatter.parse_frontmatter("summary: Use X: not Y")
        self.assertEqual(fields, {})
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("field summary is not valid YAML"), problems)


if __name__ == "__main__":
    unittest.main()
