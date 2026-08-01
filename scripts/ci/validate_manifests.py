#!/usr/bin/env python3
"""Validate the plugin manifests and skill frontmatter.

Run manually from the repo root: python3 scripts/ci/validate_manifests.py
Run automatically by .github/workflows/pr.yml on every pull request.

Stdlib-only by design (ADR 007): the repo needs no Python project (or PyYAML) at
its root. The frontmatter parser is adapted from scripts/adr/generate_index.py
rather than imported, because the two live in sibling directories with no package
to hang an import off; this copy handles scalars only, where that one also parses
inline lists.
"""

import json
import re
import sys
import tomllib
from pathlib import Path

from versions import RE_VERSION

MARKETPLACE_FILE = Path(".claude-plugin/marketplace.json")
PLUGIN_FILE = Path(".claude-plugin/plugin.json")

# What every plugin entry's `source` must be, pinning distribution to the release
# branch rather than to whichever branch happens to be the repo default (ADR 010).
EXPECTED_SOURCE = {
    "ref": "main",
    "repo": "todofixthis/phx-claude-siat",
    "source": "github",
}
SKILL_ROOTS = (Path("skills"), Path(".agents/skills"))
WORKFLOW_FILE = Path(".github/workflows/pr.yml")

# Files whose presence means a skill ships tooling something has to run.
TOOLING_MARKERS = ("package.json", "pyproject.toml")

RE_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(block: str) -> dict:
    """Parse a flat YAML frontmatter block into a dict.

    Skill frontmatter is `key: value` scalars only, so a line parser suffices.
    """
    fields: dict = {}
    for line in block.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def load_json(path: Path, errors: list) -> dict | None:
    """Read and parse a JSON manifest, recording an error if it is unusable."""
    if not path.exists():
        errors.append(f"{path} is missing")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path} is not valid JSON: {exc}")
        return None


def check_plugin(errors: list) -> None:
    """The plugin manifest must carry a releasable version — the single source of truth."""
    plugin = load_json(PLUGIN_FILE, errors)
    if plugin is None:
        return

    version = plugin.get("version")
    if version is None:
        errors.append(f"{PLUGIN_FILE} has no version")
    elif not isinstance(version, str) or not RE_VERSION.match(version):
        errors.append(
            f"{PLUGIN_FILE} version {version!r} is not releasable: this project "
            "publishes X.Y.Z only, with no pre-release suffix or build metadata "
            "(see docs/adr/008)"
        )


def check_marketplace(errors: list) -> None:
    """Marketplace entries must not carry a version, and must pin the release ref.

    The version resolves plugin.json -> marketplace entry -> SHA, so duplicating it
    in the entry breaks single-source-of-truth (ADR 001). The `source` pin is what
    makes `main` the branch users install (ADR 010); dropped or repointed, the entry
    silently falls back to the repo's default branch, which is `develop`. That fails
    nowhere else — installs just start serving integration — so it is asserted here
    rather than left to review, the same reasoning ADR 006 applied to skill tooling.
    """
    marketplace = load_json(MARKETPLACE_FILE, errors)
    if marketplace is None:
        return

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        errors.append(f"{MARKETPLACE_FILE} has no plugins list")
        return

    for entry in plugins:
        name = entry.get("name", "<unnamed>") if isinstance(entry, dict) else "<unnamed>"
        if not isinstance(entry, dict):
            errors.append(f"{MARKETPLACE_FILE} plugin entry {name} is not an object")
        elif "version" in entry:
            errors.append(
                f"{MARKETPLACE_FILE} plugin entry {name} carries a version; "
                f"the version belongs only in {PLUGIN_FILE} (see docs/adr/001)"
            )
        elif entry.get("source") != EXPECTED_SOURCE:
            errors.append(
                f"{MARKETPLACE_FILE} plugin entry {name} has source "
                f"{entry.get('source')!r}; it must be {EXPECTED_SOURCE!r} so installs "
                f"track the release branch, not the repo default (see docs/adr/010)"
            )


def check_skills(errors: list) -> None:
    """Every skill must declare a name matching its directory, plus a description."""
    for root in SKILL_ROOTS:
        if not root.is_dir():
            errors.append(f"{root} is missing")
            continue

        for skill_dir in sorted(d for d in root.iterdir() if d.is_dir()):
            path = skill_dir / "SKILL.md"
            if not path.exists():
                errors.append(f"{path} is missing")
                continue

            match = RE_FRONTMATTER.match(path.read_text(encoding="utf-8"))
            if not match:
                errors.append(f"{path} has no frontmatter block")
                continue

            fields = parse_frontmatter(match.group(1))
            name = fields.get("name", "")
            if not name:
                errors.append(f"{path} has no name")
            elif name != skill_dir.name:
                errors.append(f"{path} name {name!r} does not match its directory")
            if not fields.get("description"):
                errors.append(f"{path} has no description")


def declared_tools(skill_dir: Path, errors: list) -> list:
    """Return the tool names a skill declares in [tool.autohooks], if any.

    `autohooks.plugins.black` names the tool `black`. Skills declaring tooling any
    other way return nothing — see docs/adr/006.
    """
    path = skill_dir / "pyproject.toml"
    if not path.exists():
        return []

    try:
        with path.open("rb") as handle:
            config = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"{path} is not valid TOML: {exc}")
        return []

    plugins = config.get("tool", {}).get("autohooks", {}).get("pre-commit", [])
    return [plugin.rsplit(".", 1)[-1] for plugin in plugins]


def check_skill_tooling(errors: list) -> None:
    """A skill's declared tooling must be gated by the PR workflow — see docs/adr/006.

    The workflow mirrors each skill's declaration by hand, so it would otherwise fail
    open. Two halves: a skill nothing gates at all, and a gated skill whose declaration
    grew a tool its job never runs. The second is a substring match over the whole
    workflow, so a tool named only in a comment satisfies it.
    """
    if not WORKFLOW_FILE.exists():
        errors.append(f"{WORKFLOW_FILE} is missing")
        return

    workflow = WORKFLOW_FILE.read_text(encoding="utf-8")
    for root in SKILL_ROOTS:
        if not root.is_dir():
            continue

        for skill_dir in sorted(d for d in root.iterdir() if d.is_dir()):
            markers = [m for m in TOOLING_MARKERS if (skill_dir / m).exists()]
            if not markers:
                continue

            if skill_dir.as_posix() not in workflow:
                errors.append(
                    f"{skill_dir} ships tooling ({', '.join(markers)}) but nothing in "
                    f"{WORKFLOW_FILE} references it; add a check for it (see docs/adr/006)"
                )
                continue

            for tool in declared_tools(skill_dir, errors):
                if tool not in workflow:
                    errors.append(
                        f"{skill_dir} declares {tool} but {WORKFLOW_FILE} never runs it; "
                        f"the workflow mirrors the declaration (see docs/adr/006)"
                    )


def validate() -> int:
    """Validate every manifest invariant. Return 0 on success, 1 on error."""
    errors: list = []
    check_plugin(errors)
    check_marketplace(errors)
    check_skills(errors)
    check_skill_tooling(errors)

    for error in errors:
        print(f"Error: {error}", file=sys.stderr)
    if errors:
        print("Fix the errors above before committing.", file=sys.stderr)
        return 1

    print("Manifests and skill frontmatter are valid")
    return 0


if __name__ == "__main__":
    sys.exit(validate())
