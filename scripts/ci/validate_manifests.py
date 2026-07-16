#!/usr/bin/env python3
"""Validate the plugin manifests and skill frontmatter.

Run manually from the repo root: python3 scripts/ci/validate_manifests.py
Run automatically by .github/workflows/pr.yml on every pull request.

Stdlib-only by design, for the same reason as scripts/adr/generate_index.py: the
repo needs no Python project (or PyYAML) at its root. The frontmatter parser is
duplicated from that script rather than imported, because the two live in sibling
directories with no package to hang an import off.
"""

import json
import re
import sys
from pathlib import Path

MARKETPLACE_FILE = Path(".claude-plugin/marketplace.json")
PLUGIN_FILE = Path(".claude-plugin/plugin.json")
SKILL_ROOTS = (Path("skills"), Path(".agents/skills"))

RE_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
# The official grammar, from https://semver.org/
RE_SEMVER = re.compile(
    r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-(?:(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?:[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


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
    """The plugin manifest must carry a semver version — the single source of truth."""
    plugin = load_json(PLUGIN_FILE, errors)
    if plugin is None:
        return

    version = plugin.get("version")
    if version is None:
        errors.append(f"{PLUGIN_FILE} has no version")
    elif not isinstance(version, str) or not RE_SEMVER.match(version):
        errors.append(f"{PLUGIN_FILE} version {version!r} is not valid semver")


def check_marketplace(errors: list) -> None:
    """Marketplace entries must not carry a version — see docs/adr/001.

    The version resolves plugin.json -> marketplace entry -> SHA, so duplicating it
    in the entry breaks single-source-of-truth.
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


def validate() -> int:
    """Validate every manifest invariant. Return 0 on success, 1 on error."""
    errors: list = []
    check_plugin(errors)
    check_marketplace(errors)
    check_skills(errors)

    for error in errors:
        print(f"Error: {error}", file=sys.stderr)
    if errors:
        print("Fix the errors above before committing.", file=sys.stderr)
        return 1

    print("Manifests and skill frontmatter are valid")
    return 0


if __name__ == "__main__":
    sys.exit(validate())
