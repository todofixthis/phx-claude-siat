"""Unit tests for validate_manifests.py.

Stdlib `unittest` rather than pytest, so the suite needs no dependency of its own
(ADR 007). Run from the repo root:

    python3 -m unittest discover -s scripts -t . -p 'test_*.py'

Every path this module reads is a module-level relative `Path`, resolved afresh on
each call, so these tests `chdir` into a fixture repo rather than patching five
constants and risking a half-applied patch. That works only while those constants
stay relative — anchoring one to `__file__` would break it silently.

Each test starts from a skeleton that validates clean and breaks exactly one thing,
so a single reported error is meaningful. `test_pristine_fixture_is_valid` is what
makes that true; it also guards against a lost chdir, which would otherwise let a
positive test pass by reading the real repo.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci import validate_manifests as vm

PLUGIN_NAME = "example"
SKILL_FRONTMATTER = "---\nname: {name}\ndescription: Does a thing.\n---\n\n# Skill\n"
WORKFLOW = "jobs:\n  python:\n    # runs skills/example-tooling under black\n    steps: []\n"


class ManifestTestCase(unittest.TestCase):
    """A temp directory holding a repo skeleton that validates clean."""

    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(directory)
        self.enterContext(contextlib.chdir(self.root))
        self.assertNotEqual(Path.cwd(), Path(vm.__file__).parents[2], "fixture chdir failed")

        self.write_plugin()
        self.write_marketplace()
        for root in ("skills", ".agents/skills"):
            self.write_skill(f"{root}/plain")
        self.write(".github/workflows/pr.yml", WORKFLOW)

    def write(self, path: str, content: str) -> Path:
        """Create a file in the fixture, making its parents as needed."""
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def write_plugin(self, **overrides) -> None:
        """Write .claude-plugin/plugin.json, with any field overridden."""
        manifest = {"name": PLUGIN_NAME, "version": "1.2.3"} | overrides
        self.write(".claude-plugin/plugin.json", json.dumps(manifest))

    def write_marketplace(self, *entries) -> None:
        """Write .claude-plugin/marketplace.json, defaulting to one valid entry."""
        if not entries:
            entries = ({"name": PLUGIN_NAME, "source": dict(vm.EXPECTED_SOURCE)},)
        self.write(".claude-plugin/marketplace.json", json.dumps({"plugins": list(entries)}))

    def write_skill(self, path: str, name: str | None = None, body: str | None = None) -> None:
        """Write a SKILL.md whose declared name matches its directory by default."""
        directory = Path(path)
        content = body if body is not None else SKILL_FRONTMATTER.format(
            name=name if name is not None else directory.name
        )
        self.write(f"{path}/SKILL.md", content)

    def errors_from(self, check, *args) -> list:
        """Run one check in isolation and return the errors it recorded."""
        errors: list = []
        check(*args, errors)
        return errors

    def run_validate(self) -> tuple[int, str, str]:
        """Run validate(), returning its exit code with stdout and stderr."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = vm.validate()
        return code, out.getvalue(), err.getvalue()


class FixtureTests(ManifestTestCase):
    def test_pristine_fixture_is_valid(self):
        """The skeleton every other test mutates must itself pass, or nothing below means anything."""
        code, out, err = self.run_validate()
        self.assertEqual((code, err), (0, ""))
        self.assertIn("Manifests and skill frontmatter are valid", out)


class LoadJsonTests(ManifestTestCase):
    def test_reports_a_missing_file(self):
        """A manifest that does not exist is named rather than crashing on open."""
        errors: list = []
        self.assertIsNone(vm.load_json(Path("nope.json"), errors))
        self.assertEqual(errors, ["nope.json is missing"])

    def test_reports_malformed_json(self):
        """A syntax error is attributed to the file that holds it."""
        errors: list = []
        self.assertIsNone(vm.load_json(self.write("bad.json", "{oops"), errors))
        self.assertIn("bad.json is not valid JSON", errors[0])

    def test_rejects_json_that_is_not_an_object(self):
        """Well-formed JSON of the wrong shape must not reach a caller's `.get`."""
        for payload in ("[1, 2, 3]", '"a string"', "42"):
            with self.subTest(payload=payload):
                errors: list = []
                self.assertIsNone(vm.load_json(self.write("odd.json", payload), errors))
                self.assertIn("must hold a JSON object", errors[0])


class CheckPluginTests(ManifestTestCase):
    def check(self) -> list:
        """Load the fixture's plugin manifest and run the plugin check over it."""
        errors: list = []
        vm.check_plugin(vm.load_json(vm.PLUGIN_FILE, errors), errors)
        return errors

    def test_reports_a_missing_version(self):
        """The plugin manifest is the single source of the version, so it must carry one."""
        self.write_plugin(version=None)
        self.write(".claude-plugin/plugin.json", json.dumps({"name": PLUGIN_NAME}))
        self.assertEqual(self.check(), [f"{vm.PLUGIN_FILE} has no version"])

    def test_rejects_a_version_that_is_not_a_string(self):
        """A JSON number is a realistic hand-edit and must not reach the regex."""
        self.write(".claude-plugin/plugin.json", json.dumps({"name": PLUGIN_NAME, "version": 1.0}))
        self.assertIn("is not releasable", self.check()[0])

    def test_rejects_a_pre_release_version(self):
        """Only X.Y.Z can be published, so a suffix fails here rather than after the merge."""
        self.write_plugin(version="1.2.3-rc.1")
        error = self.check()[0]
        self.assertIn("'1.2.3-rc.1'", error)
        self.assertIn("docs/adr/008", error)


class CheckMarketplaceTests(ManifestTestCase):
    def check(self) -> list:
        """Run the marketplace check against the fixture's two manifests."""
        errors: list = []
        vm.check_marketplace(vm.load_json(vm.PLUGIN_FILE, errors), errors)
        return errors

    def test_rejects_an_entry_carrying_a_version(self):
        """Duplicating the version in the entry breaks single-source-of-truth."""
        self.write_marketplace(
            {"name": PLUGIN_NAME, "version": "1.2.3", "source": dict(vm.EXPECTED_SOURCE)}
        )
        error = next(e for e in self.check() if "carries a version" in e)
        self.assertIn("docs/adr/001", error)

    def test_rejects_the_pre_pin_relative_source(self):
        """`./` is what the entry held before ADR 010; it must never come back."""
        self.write_marketplace({"name": PLUGIN_NAME, "source": "./"})
        error = self.check()[0]
        self.assertIn("'./'", error)
        self.assertIn("docs/adr/010", error)

    def test_accepts_source_keys_in_any_order(self):
        """The pin is compared as a mapping, so key order in the file is irrelevant."""
        source = dict(reversed(list(vm.EXPECTED_SOURCE.items())))
        self.write(
            ".claude-plugin/marketplace.json",
            json.dumps({"plugins": [{"name": PLUGIN_NAME, "source": source}]}),
        )
        self.assertEqual(self.check(), [])

    def test_rejects_an_extra_key_in_the_source(self):
        """A `sha` commit pin is refused by design: ADR 010 rejected per-release edits."""
        self.write_marketplace(
            {"name": PLUGIN_NAME, "source": dict(vm.EXPECTED_SOURCE, sha="a" * 40)}
        )
        self.assertIn("docs/adr/010", self.check()[0])

    def test_reports_every_broken_invariant_on_one_entry(self):
        """Two faults must surface together, not one per run."""
        self.write_marketplace({"name": "wrong", "version": "1.2.3", "source": "./"})
        errors = self.check()
        self.assertEqual(len(errors), 3, errors)

    def test_rejects_a_name_that_disagrees_with_the_plugin_manifest(self):
        """Installs resolve by name, so a mismatch breaks them while every other field is fine."""
        self.write_marketplace({"name": "other", "source": dict(vm.EXPECTED_SOURCE)})
        error = self.check()[0]
        self.assertIn("'other'", error)
        self.assertIn(f"'{PLUGIN_NAME}'", error)

    def test_rejects_an_entry_that_is_not_an_object(self):
        """A malformed entry is named rather than crashing the run."""
        self.write_marketplace("just a string")
        self.assertIn("is not an object", self.check()[0])

    def test_rejects_a_missing_or_malformed_plugins_list(self):
        """Without a list of plugins there is no catalogue to check."""
        for payload in ({}, {"plugins": {"name": PLUGIN_NAME}}):
            with self.subTest(payload=payload):
                self.write(".claude-plugin/marketplace.json", json.dumps(payload))
                self.assertIn("has no plugins list", self.check()[0])

    def test_rejects_an_empty_plugins_list(self):
        """An empty catalogue is well-formed and advertises nothing."""
        self.write(".claude-plugin/marketplace.json", json.dumps({"plugins": []}))
        self.assertEqual(self.check(), [f"{vm.MARKETPLACE_FILE} lists no plugins"])


class CheckSkillsTests(ManifestTestCase):
    def check(self) -> list:
        """Run the skill check over the fixture's skill roots."""
        return self.errors_from(vm.check_skills)

    def test_reports_a_directory_with_no_skill_file(self):
        """Every directory under a skill root is a skill and must declare itself."""
        (self.root / "skills" / "empty").mkdir()
        self.assertIn("skills/empty/SKILL.md is missing", self.check())

    def test_reports_a_skill_file_with_no_frontmatter(self):
        """Frontmatter is where the name and description live; without it there is nothing to check."""
        self.write_skill("skills/bare", body="# Just a heading\n")
        self.assertIn("skills/bare/SKILL.md has no frontmatter block", self.check())

    def test_rejects_a_name_that_does_not_match_the_directory(self):
        """The invocation name comes from the directory, so a mismatch renames the skill silently."""
        self.write_skill("skills/actual", name="declared")
        error = next(e for e in self.check() if "does not match" in e)
        self.assertIn("'declared'", error)

    def test_reports_a_missing_name_and_an_empty_description(self):
        """Both fields are required, and an empty value is as absent as a missing key."""
        self.write_skill("skills/thin", body="---\ndescription:\n---\n\n# Skill\n")
        errors = self.check()
        self.assertIn("skills/thin/SKILL.md has no name", errors)
        self.assertIn("skills/thin/SKILL.md has no description", errors)

    def test_surfaces_parser_problems_against_the_file(self):
        """A frontmatter problem must name the file it came from, not float free."""
        self.write_skill(
            "skills/wrapped",
            body="---\nname: wrapped\ndescription: A long one\n  and its remainder\n---\n\n# Skill\n",
        )
        self.assertIn(
            "skills/wrapped/SKILL.md continued onto another line; wrap it onto one: "
            "'and its remainder'",
            self.check(),
        )

    def test_reports_a_missing_skill_root(self):
        """A vanished root is an error, not zero skills to check."""
        for item in (self.root / ".agents" / "skills" / "plain").iterdir():
            item.unlink()
        (self.root / ".agents" / "skills" / "plain").rmdir()
        (self.root / ".agents" / "skills").rmdir()
        self.assertIn(".agents/skills is missing", self.check())

    def test_checks_both_skill_roots(self):
        """A broken project-local skill must fail as loudly as a published one."""
        self.write_skill(".agents/skills/local", name="wrong")
        self.assertTrue(
            any(".agents/skills/local" in error for error in self.check()), self.check()
        )


class DeclaredToolsTests(ManifestTestCase):
    def tools(self, toml: str | None) -> tuple[list, list]:
        """Write a skill's pyproject (or none) and return its tools and errors."""
        skill = self.root / "skills" / "tooled"
        skill.mkdir(parents=True, exist_ok=True)
        if toml is not None:
            (skill / "pyproject.toml").write_text(toml, encoding="utf-8")
        errors: list = []
        return vm.declared_tools(Path("skills/tooled"), errors), errors

    def test_returns_nothing_without_a_pyproject(self):
        """Most skills ship no tooling, and that is not an error."""
        self.assertEqual(self.tools(None), ([], []))

    def test_returns_nothing_without_an_autohooks_table(self):
        """A pyproject that declares no hooks declares no tools."""
        self.assertEqual(self.tools('[project]\nname = "x"\n'), ([], []))

    def test_reports_invalid_toml(self):
        """A pyproject that cannot be read is an error, not an empty declaration."""
        tools, errors = self.tools("[tool.autohooks\n")
        self.assertEqual(tools, [])
        self.assertIn("is not valid TOML", errors[0])

    def test_trims_each_plugin_path_to_its_tool(self):
        """`autohooks.plugins.black` runs `black`; a bare name is already the tool."""
        tools, errors = self.tools(
            '[tool.autohooks]\npre-commit = ["autohooks.plugins.black", "ruff"]\n'
        )
        self.assertEqual((tools, errors), (["black", "ruff"], []))

    def test_rejects_declarations_that_are_not_a_list_of_names(self):
        """Every malformed shape otherwise fails open, verifying nothing downstream."""
        shapes = {
            "bare string": '[tool.autohooks]\npre-commit = "autohooks.plugins.black"\n',
            "list of numbers": "[tool.autohooks]\npre-commit = [1, 2]\n",
            "table": "[tool.autohooks.pre-commit]\nblack = true\n",
            "trailing dot": '[tool.autohooks]\npre-commit = ["black."]\n',
        }
        for label, toml in shapes.items():
            with self.subTest(shape=label):
                tools, errors = self.tools(toml)
                self.assertEqual(tools, [])
                self.assertIn("must be a list of plugin names", errors[0])


class CheckSkillToolingTests(ManifestTestCase):
    def check(self) -> list:
        """Run the tooling-mirror check over the fixture."""
        return self.errors_from(vm.check_skill_tooling)

    def test_ignores_skills_that_ship_no_tooling(self):
        """The fixture's plain skills must not trip a check about tooling they lack."""
        self.assertEqual(self.check(), [])

    def test_reports_a_tooling_skill_the_workflow_never_names(self):
        """A skill CI does not gate is the drift ADR 006 exists to catch."""
        self.write("skills/ungated/SKILL.md", SKILL_FRONTMATTER.format(name="ungated"))
        self.write("skills/ungated/pyproject.toml", "[project]\nname = 'x'\n")
        error = next(e for e in self.check() if "skills/ungated" in e)
        self.assertIn("nothing in .github/workflows/pr.yml references it", error)

    def test_counts_a_package_json_as_tooling(self):
        """Both markers mean the skill ships something a job has to run."""
        self.write("skills/noded/SKILL.md", SKILL_FRONTMATTER.format(name="noded"))
        self.write("skills/noded/package.json", "{}")
        self.assertTrue(any("skills/noded" in error for error in self.check()))

    def test_reports_a_declared_tool_the_workflow_never_runs(self):
        """The second half of the mirror: a gated skill whose declaration outgrew its job."""
        self.write("skills/example-tooling/SKILL.md", SKILL_FRONTMATTER.format(name="example-tooling"))
        self.write(
            "skills/example-tooling/pyproject.toml",
            '[tool.autohooks]\npre-commit = ["autohooks.plugins.mypy"]\n',
        )
        errors = self.check()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("declares mypy but .github/workflows/pr.yml never runs it", errors[0])

    def test_a_tool_named_only_in_a_comment_satisfies_the_check(self):
        """ADR 006 accepted this blindness knowingly; pinning it makes any change deliberate."""
        self.write("skills/example-tooling/SKILL.md", SKILL_FRONTMATTER.format(name="example-tooling"))
        self.write(
            "skills/example-tooling/pyproject.toml",
            '[tool.autohooks]\npre-commit = ["autohooks.plugins.black"]\n',
        )
        self.assertEqual(self.check(), [])

    def test_reports_a_missing_workflow(self):
        """Without the workflow there is nothing to mirror against."""
        (self.root / ".github" / "workflows" / "pr.yml").unlink()
        self.assertEqual(self.check(), [".github/workflows/pr.yml is missing"])


class ValidateTests(ManifestTestCase):
    def test_reports_a_single_failure_and_exits_non_zero(self):
        """One broken invariant fails the run, with the error and the trailer on stderr."""
        self.write_plugin(version="nope")
        code, _, err = self.run_validate()
        self.assertEqual(code, 1)
        self.assertIn("is not releasable", err)
        self.assertIn("Fix the errors above before committing.", err)

    def test_reports_failures_from_every_check_in_one_run(self):
        """No check short-circuits the rest, so one run lists everything to fix."""
        self.write_plugin(version="nope")
        self.write_marketplace({"name": PLUGIN_NAME, "source": "./"})
        self.write_skill("skills/mismatched", name="other")
        code, _, err = self.run_validate()
        self.assertEqual(code, 1)
        self.assertIn("is not releasable", err)
        self.assertIn("docs/adr/010", err)
        self.assertIn("does not match", err)


if __name__ == "__main__":
    unittest.main()
