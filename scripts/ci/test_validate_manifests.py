"""Tests for validate_manifests.py.

Stdlib `unittest` rather than pytest, so the suite needs no dependency of its own
(ADR 007). Run from the repo root:

    python3 -m unittest discover -s scripts -t . -p 'test_*.py'

The subject joins every path constant to a `repo_root` its checks require (ADR 027), so
these tests pass the fixture root and never `chdir`. Nothing here can fall back to the
real repository: the checks carry no default, so omitting the root is a `TypeError`
rather than a test that passes against the wrong tree. The only test that changes
directory is the one asserting a `chdir` *cannot* redirect the anchor, and it reads the
constant rather than calling the subject.

Each test starts from a fixture that validates clean and breaks exactly one thing,
so a single reported error is meaningful. `test_pristine_fixture_is_valid` is what
makes that true.
"""

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from scripts.ci import validate_manifests as vm

PLUGIN_NAME = "example"
SKILL_FRONTMATTER = "---\nname: {name}\ndescription: Does a thing.\n---\n\n# Skill\n"
WORKFLOW = "jobs:\n  python:\n    # runs skills/example-tooling under black\n    steps: []\n"


class ManifestTestCase(unittest.TestCase):
    """A temp directory holding a repo skeleton that validates clean."""

    def setUp(self) -> None:
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(directory)

        self.write_plugin_manifest()
        self.write_marketplace()
        for root in vm.SKILL_ROOTS:
            self.write_skill(root / "plain")
        self.write(vm.WORKFLOW_FILE, WORKFLOW)

    def write(self, path: str | Path, content: str) -> Path:
        """Create a file in the fixture, making its parents as needed."""
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def write_plugin_manifest(self, **overrides) -> None:
        """Write .claude-plugin/plugin.json, with any field overridden."""
        manifest = {"name": PLUGIN_NAME, "version": "1.2.3"} | overrides
        self.write(vm.PLUGIN_FILE, json.dumps(manifest))

    def write_marketplace(self, *entries) -> None:
        """Write .claude-plugin/marketplace.json, defaulting to one valid entry."""
        if not entries:
            entries = ({"name": PLUGIN_NAME, "source": dict(vm.EXPECTED_SOURCE)},)
        self.write(vm.MARKETPLACE_FILE, json.dumps({"plugins": list(entries)}))

    def write_skill(
        self, path: str | Path, name: str | None = None, body: str | None = None
    ) -> None:
        """Write a SKILL.md whose declared name matches its directory by default."""
        directory = Path(path)
        content = body if body is not None else SKILL_FRONTMATTER.format(
            name=name if name is not None else directory.name
        )
        self.write(directory / vm.SKILL_FILENAME, content)

    def errors_from(self, check: Callable, *args) -> list:
        """Run one check in isolation and return the errors it recorded."""
        errors: list = []
        check(*args, errors)
        return errors

    def run_validate(self) -> tuple[int, str, str]:
        """Run validate() over the fixture, returning its exit code with both streams."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = vm.validate(self.root)
        return code, out.getvalue(), err.getvalue()


class LoadJsonTests(ManifestTestCase):
    """Unit tests for ``load_json()``."""

    def test_reports_a_missing_file(self):
        """A manifest that does not exist is named rather than crashing on open."""
        errors: list = []
        self.assertIsNone(vm.load_json(Path("nope.json"), self.root, errors))
        self.assertEqual(errors, ["nope.json is missing"])

    def test_reports_malformed_json(self):
        """A syntax error is attributed to the file that holds it."""
        errors: list = []
        self.write("bad.json", "{oops")
        self.assertIsNone(vm.load_json(Path("bad.json"), self.root, errors))
        self.assertIn("bad.json is not valid JSON", errors[0])

    def test_rejects_json_that_is_not_an_object(self):
        """Well-formed JSON of the wrong shape must not reach a caller's `.get`."""
        for payload in ("[1, 2, 3]", '"a string"', "42"):
            with self.subTest(payload=payload):
                errors: list = []
                self.write("odd.json", payload)
                self.assertIsNone(
                    vm.load_json(Path("odd.json"), self.root, errors)
                )
                self.assertIn("must hold a JSON object", errors[0])


class CheckPluginTests(ManifestTestCase):
    """Unit tests for ``check_plugin()``."""

    def check(self) -> list:
        """Load the fixture's plugin manifest and run the plugin check over it."""
        errors: list = []
        vm.check_plugin(vm.load_json(vm.PLUGIN_FILE, self.root, errors), errors)
        return errors

    def test_reports_a_missing_version(self):
        """The plugin manifest is the single source of the version, so it must carry one."""
        self.write(vm.PLUGIN_FILE, json.dumps({"name": PLUGIN_NAME}))
        self.assertEqual(self.check(), [f"{vm.PLUGIN_FILE} has no version"])

    def test_rejects_a_version_that_is_not_a_string(self):
        """A JSON number is a realistic hand-edit and must not reach the regex."""
        self.write(vm.PLUGIN_FILE, json.dumps({"name": PLUGIN_NAME, "version": 1.0}))
        self.assertIn("is not releasable", self.check()[0])

    def test_reports_a_missing_name(self):
        """The name an install resolves must exist, and the marketplace check relies on it."""
        self.write(vm.PLUGIN_FILE, json.dumps({"version": "1.2.3"}))
        self.assertIn(f"{vm.PLUGIN_FILE} has no name", self.check())

    def test_rejects_a_pre_release_version(self):
        """Only X.Y.Z can be published, so a suffix fails here rather than after the merge."""
        self.write_plugin_manifest(version="1.2.3-rc.1")
        error = self.check()[0]
        self.assertIn("'1.2.3-rc.1'", error)
        self.assertIn("docs/adr/008", error)


class CheckMarketplaceTests(ManifestTestCase):
    """Unit tests for ``check_marketplace()``."""

    def check(self) -> list:
        """Run the marketplace check against the fixture's two manifests."""
        errors: list = []
        vm.check_marketplace(
            vm.load_json(vm.PLUGIN_FILE, self.root, errors), self.root, errors
        )
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
            vm.MARKETPLACE_FILE,
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

    def test_rejects_a_second_entry_alongside_the_plugin(self):
        """Distributing another plugin from here is a decision, and this is where it surfaces."""
        self.write_marketplace(
            {"name": PLUGIN_NAME, "source": dict(vm.EXPECTED_SOURCE)},
            {"name": "other-plugin", "source": dict(vm.EXPECTED_SOURCE)},
        )
        error = self.check()[0]
        self.assertIn("lists 2 entries", error)
        self.assertIn("Remove the duplicate", error)
        self.assertIn("docs/adr/012", error)

    def test_rejects_a_catalogue_that_never_names_the_plugin(self):
        """Installs resolve by name, so some entry has to carry the plugin's own."""
        self.write_marketplace({"name": "other", "source": dict(vm.EXPECTED_SOURCE)})
        error = self.check()[0]
        self.assertIn(f"lists no entry named '{PLUGIN_NAME}'", error)

    def test_rejects_an_entry_that_is_not_an_object(self):
        """A malformed entry is named rather than crashing the run."""
        self.write_marketplace("just a string")
        self.assertIn("is not an object", self.check()[0])

    def test_rejects_a_missing_or_malformed_plugins_list(self):
        """Without a list of plugins there is no catalogue to check."""
        for payload in ({}, {"plugins": {"name": PLUGIN_NAME}}):
            with self.subTest(payload=payload):
                self.write(vm.MARKETPLACE_FILE, json.dumps(payload))
                self.assertIn("has no plugins list", self.check()[0])

    def test_rejects_an_empty_plugins_list(self):
        """An empty catalogue is well-formed and advertises nothing."""
        self.write(vm.MARKETPLACE_FILE, json.dumps({"plugins": []}))
        self.assertEqual(self.check(), [f"{vm.MARKETPLACE_FILE} lists no plugins"])


class CheckSkillsTests(ManifestTestCase):
    """Unit tests for ``check_skills()``."""

    def check(self) -> list:
        """Run the skill check over the fixture's skill roots."""
        return self.errors_from(vm.check_skills, self.root)

    def test_reports_a_directory_with_no_skill_file(self):
        """Every directory under a skill root is a skill and must declare itself."""
        empty = vm.SKILL_ROOTS[0] / "empty"
        (self.root / empty).mkdir()
        self.assertIn(f"{empty / vm.SKILL_FILENAME} is missing", self.check())

    def test_reports_a_skill_file_with_no_frontmatter(self):
        """Frontmatter is where the name and description live; without it there is nothing to check."""
        bare = vm.SKILL_ROOTS[0] / "bare"
        self.write_skill(bare, body="# Just a heading\n")
        self.assertIn(f"{bare / vm.SKILL_FILENAME} has no frontmatter block", self.check())

    def test_rejects_a_name_that_does_not_match_the_directory(self):
        """The invocation name comes from the directory, so a mismatch renames the skill silently."""
        self.write_skill("skills/actual", name="declared")
        error = next(e for e in self.check() if "does not match" in e)
        self.assertIn("'declared'", error)

    def test_reports_a_missing_name(self):
        """The name is what the skill is invoked as, so frontmatter has to declare it."""
        self.write_skill("skills/thin", body="---\ndescription: A thing.\n---\n\n# Skill\n")
        self.assertIn(f"skills/thin/{vm.SKILL_FILENAME} has no name", self.check())

    def test_reports_an_empty_description(self):
        """A key present with nothing after it is as absent as a missing key."""
        self.write_skill("skills/thin", body="---\nname: thin\ndescription:\n---\n\n# Skill\n")
        self.assertIn(f"skills/thin/{vm.SKILL_FILENAME} has no description", self.check())

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
        root = vm.SKILL_ROOTS[-1]
        shutil.rmtree(self.root / root)
        self.assertIn(f"{root} is missing", self.check())

    def test_checks_both_skill_roots(self):
        """A broken project-local skill must fail as loudly as a published one."""
        local = vm.SKILL_ROOTS[-1] / "local"
        self.write_skill(local, name="wrong")
        self.assertTrue(any(str(local) in error for error in self.check()), self.check())


class DeclaredToolsTests(ManifestTestCase):
    """Unit tests for ``declared_tools()``."""

    def tools(self, toml: str | None) -> tuple[list, list]:
        """Write a skill's pyproject (or none) and return its tools and errors."""
        skill = self.root / "skills" / "tooled"
        skill.mkdir(parents=True, exist_ok=True)
        if toml is not None:
            (skill / vm.PYPROJECT_FILENAME).write_text(toml, encoding="utf-8")
        errors: list = []
        return vm.declared_tools(Path("skills/tooled"), self.root, errors), errors

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

    def test_reports_a_wrongly_typed_autohooks_table(self):
        """A declaration nobody can read must error, not return no tools at all."""
        for label, toml in {
            "autohooks a list": '[tool]\nautohooks = ["autohooks.plugins.mypy"]\n',
            "tool a string": 'tool = "x"\n',
        }.items():
            with self.subTest(shape=label):
                tools, errors = self.tools(toml)
                self.assertEqual(tools, [])
                self.assertTrue(errors, "a malformed table must not pass silently")

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
    """Unit tests for ``check_skill_tooling()``."""

    def check(self) -> list:
        """Run the tooling-mirror check over the fixture."""
        return self.errors_from(vm.check_skill_tooling, self.root)

    def test_ignores_skills_that_ship_no_tooling(self):
        """The fixture's plain skills must not trip a check about tooling they lack."""
        self.assertEqual(self.check(), [])

    def test_reports_a_tooling_skill_the_workflow_never_names(self):
        """A skill CI does not gate is the drift ADR 006 exists to catch."""
        self.write_skill("skills/ungated")
        self.write(f"skills/ungated/{vm.PYPROJECT_FILENAME}", "[project]\nname = 'x'\n")
        error = next(e for e in self.check() if "skills/ungated" in e)
        self.assertIn(f"nothing in {vm.WORKFLOW_FILE} references it", error)

    def test_counts_a_package_json_as_tooling(self):
        """Both markers mean the skill ships something a job has to run."""
        self.write_skill("skills/noded")
        self.write(f"skills/noded/{vm.TOOLING_MARKERS[0]}", "{}")
        self.assertTrue(any("skills/noded" in error for error in self.check()))

    def test_reports_a_declared_tool_the_workflow_never_runs(self):
        """The second half of the mirror: a gated skill whose declaration outgrew its job."""
        self.write_skill("skills/example-tooling")
        self.write(
            f"skills/example-tooling/{vm.PYPROJECT_FILENAME}",
            '[tool.autohooks]\npre-commit = ["autohooks.plugins.mypy"]\n',
        )
        errors = self.check()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn(f"declares mypy but {vm.WORKFLOW_FILE} never runs it", errors[0])

    def test_a_tool_named_only_in_a_comment_satisfies_the_check(self):
        """ADR 006 accepted this blindness knowingly; pinning it makes any change deliberate."""
        self.write_skill("skills/example-tooling")
        self.write(
            f"skills/example-tooling/{vm.PYPROJECT_FILENAME}",
            '[tool.autohooks]\npre-commit = ["autohooks.plugins.black"]\n',
        )
        self.assertEqual(self.check(), [])

    def test_reports_a_missing_workflow(self):
        """Without the workflow there is nothing to mirror against."""
        (self.root / vm.WORKFLOW_FILE).unlink()
        self.assertEqual(self.check(), [f"{vm.WORKFLOW_FILE} is missing"])


class ValidateTests(ManifestTestCase):
    """Integration tests: every check runs, and one run reports all of them."""

    def test_pristine_fixture_is_valid(self):
        """The fixture every other test mutates must itself pass, or nothing else means anything."""
        code, out, err = self.run_validate()
        self.assertEqual((code, err), (0, ""))
        self.assertIn("Manifests and skill frontmatter are valid", out)

    def test_reports_a_single_failure_and_exits_non_zero(self):
        """One broken invariant fails the run, with the error and the trailer on stderr."""
        self.write_plugin_manifest(version="nope")
        code, _, err = self.run_validate()
        self.assertEqual(code, 1)
        self.assertIn("is not releasable", err)
        self.assertIn("Fix the errors above before committing.", err)

    def test_reports_failures_from_every_check_in_one_run(self):
        """No check short-circuits the rest, so one run lists everything to fix."""
        self.write_plugin_manifest(version="nope")
        self.write_marketplace({"name": PLUGIN_NAME, "source": "./"})
        self.write_skill("skills/mismatched", name="other")
        code, _, err = self.run_validate()
        self.assertEqual(code, 1)
        self.assertIn("is not releasable", err)
        self.assertIn("docs/adr/010", err)
        self.assertIn("does not match", err)


class RepoRootTests(unittest.TestCase):
    """Unit tests for ``REPO_ROOT``: the one path the module resolves for itself."""

    def test_chdir_cannot_redirect_the_anchor(self):
        """The anchor names the tree the module ships in, wherever the caller stands."""
        with tempfile.TemporaryDirectory() as directory:
            with contextlib.chdir(directory):
                self.assertTrue(vm.REPO_ROOT.is_absolute())
                self.assertFalse(vm.REPO_ROOT.is_relative_to(directory))

    def test_root_is_this_repository(self):
        """The anchor has to reach the real repo, not merely some absolute directory."""
        self.assertTrue(Path(__file__).resolve().is_relative_to(vm.REPO_ROOT))
        self.assertTrue((vm.REPO_ROOT / vm.PLUGIN_FILE).is_file())


if __name__ == "__main__":
    unittest.main()
