"""Validate the plugin manifests and skill frontmatter.

Run manually from the repo root: python3 -m scripts.ci.validate_manifests
Run automatically by .github/workflows/pr.yml on every pull request.

Stdlib-only by design (ADR 007): the repo needs no Python project (or PyYAML) at
its root. The frontmatter parser is imported from scripts.frontmatter rather than
adapted, so this and the ADR index cannot disagree on the same input (ADR 011).
"""

import json
import re
import sys
import tomllib
from pathlib import Path

from scripts.ci.versions import RE_VERSION
from scripts.frontmatter import parse_frontmatter

# Every path constant below stays repo-relative and is joined to a `repo_root` at the
# call that touches the filesystem, so error messages name a repo-relative path rather
# than a temp directory or a CI container path. `REPO_ROOT` is read only on the
# `__main__` line (ADR 016): no default path resolves against the caller's tree, and a
# test that omits its fixture root fails rather than reading the real repository.
REPO_ROOT = Path(__file__).resolve().parents[2]

MARKETPLACE_FILE = Path(".claude-plugin/marketplace.json")
PLUGIN_FILE = Path(".claude-plugin/plugin.json")

# What every plugin entry's `source` must be, pinning distribution to the release
# branch rather than to whichever branch happens to be the repo default (ADR 010).
# Compared for equality, so an extra key is rejected too — including a `sha` commit
# pin, which ADR 010 weighed and rejected because it needs editing every release.
# A pin whose only defence is that someone reads it should fail closed.
EXPECTED_SOURCE = {
    "ref": "main",
    "repo": "todofixthis/phx-claude-siat",
    "source": "github",
}
PYPROJECT_FILENAME = "pyproject.toml"
SKILL_FILENAME = "SKILL.md"
SKILL_ROOTS = (Path("skills"), Path(".agents/skills"))
WORKFLOW_FILE = Path(".github/workflows/pr.yml")

# Files whose presence means a skill ships tooling something has to run.
TOOLING_MARKERS = ("package.json", PYPROJECT_FILENAME)

RE_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def load_json(path: Path, repo_root: Path, errors: list) -> dict | None:
    """Read and parse a JSON manifest, recording an error if it is unusable.

    `path` is repo-relative and names the file in every message; `repo_root` locates it.

    Well-formed JSON of the wrong shape is rejected here rather than left to the
    caller: a manifest holding a list or a string parses cleanly, and every caller
    then reaches for `.get`, so without this the run ends in a traceback instead of
    a message naming the file.
    """
    target = repo_root / path
    if not target.exists():
        errors.append(f"{path} is missing")
        return None
    try:
        content = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path} is not valid JSON: {exc}")
        return None
    if not isinstance(content, dict):
        errors.append(f"{path} must hold a JSON object, not {type(content).__name__}")
        return None
    return content


def check_plugin(plugin_manifest: dict | None, errors: list) -> None:
    """The plugin manifest must carry a name and a releasable version.

    The name is what an install resolves, and it is also what the marketplace check
    compares its entry against — unvalidated here, a missing name would silently
    disable that comparison rather than failing.
    """
    if plugin_manifest is None:
        return

    if not plugin_manifest.get("name"):
        errors.append(f"{PLUGIN_FILE} has no name")

    version = plugin_manifest.get("version")
    if version is None:
        errors.append(f"{PLUGIN_FILE} has no version")
    elif not isinstance(version, str) or not RE_VERSION.match(version):
        errors.append(
            f"{PLUGIN_FILE} version {version!r} is not releasable: this project "
            "publishes X.Y.Z only, with no pre-release suffix or build metadata "
            "(see docs/adr/008)"
        )


def check_marketplace(plugin_manifest: dict | None, repo_root: Path, errors: list) -> None:
    """The catalogue lists this plugin alone, versionless, pinned to the release ref.

    The version resolves plugin.json -> marketplace entry -> SHA, so duplicating it
    in the entry breaks single-source-of-truth (ADR 001). The `source` pin is what
    makes `main` the branch users install (ADR 010); dropped or repointed, the entry
    silently falls back to the repo's default branch, which is `develop`. That fails
    nowhere else — installs just start serving integration — so it is asserted here
    rather than left to review, the same reasoning ADR 006 applied to skill tooling.

    A second entry fails rather than passing as a catalogue that grew: distributing
    another plugin from here is an architectural change, and this check failing is
    what tells whoever added the entry that ADR 012 wants the decision recorded.

    Each condition is checked independently: an entry that breaks two invariants
    should report both, rather than revealing the second only once the first is fixed.
    """
    marketplace = load_json(MARKETPLACE_FILE, repo_root, errors)
    if marketplace is None:
        return

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        errors.append(f"{MARKETPLACE_FILE} has no plugins list")
        return
    # An empty list is well-formed and advertises nothing, so the catalogue would
    # serve no plugin at all while every other check passed.
    if not plugins:
        errors.append(f"{MARKETPLACE_FILE} lists no plugins")
        return
    if len(plugins) > 1:
        errors.append(
            f"{MARKETPLACE_FILE} lists {len(plugins)} entries; this catalogue advertises "
            f"the one plugin {PLUGIN_FILE} declares and nothing else. Remove the "
            "duplicate, or — if the second plugin is deliberate — reopen docs/adr/001 "
            "and relax this check, which is the decision docs/adr/012 asks for"
        )

    names = []
    for entry in plugins:
        if not isinstance(entry, dict):
            errors.append(f"{MARKETPLACE_FILE} plugin entry {entry!r} is not an object")
            continue

        name = entry.get("name")
        names.append(name)
        if "version" in entry:
            errors.append(
                f"{MARKETPLACE_FILE} plugin entry {name} carries a version; "
                f"the version belongs only in {PLUGIN_FILE} (see docs/adr/001)"
            )
        if entry.get("source") != EXPECTED_SOURCE:
            errors.append(
                f"{MARKETPLACE_FILE} plugin entry {name} has source "
                f"{entry.get('source')!r}; it must be {EXPECTED_SOURCE!r} so installs "
                f"track the release branch, not the repo default (see docs/adr/010)"
            )

    plugin_name = plugin_manifest.get("name") if plugin_manifest else None
    if plugin_name and plugin_name not in names:
        errors.append(
            f"{MARKETPLACE_FILE} lists no entry named {plugin_name!r}, which is what "
            f"{PLUGIN_FILE} calls the plugin; installs resolve by name. Entries: {names!r}"
        )


def skill_dirs(root: Path, repo_root: Path) -> list[Path]:
    """Return the skill directories under `root`, repo-relative and sorted.

    `iterdir` on the joined root yields absolute paths, which would reach both the error
    messages and the workflow substring match downstream — where the workflow names skills
    repo-relative, so every comparison would miss. Rebuilding from the name keeps the
    repo-relative form the only one that leaves this function.
    """
    return sorted(root / d.name for d in (repo_root / root).iterdir() if d.is_dir())


def check_skills(repo_root: Path, errors: list) -> None:
    """Every skill must declare a name matching its directory, plus a description."""
    for root in SKILL_ROOTS:
        if not (repo_root / root).is_dir():
            errors.append(f"{root} is missing")
            continue

        for skill_dir in skill_dirs(root, repo_root):
            path = skill_dir / SKILL_FILENAME
            if not (repo_root / path).exists():
                errors.append(f"{path} is missing")
                continue

            match = RE_FRONTMATTER.match((repo_root / path).read_text(encoding="utf-8"))
            if not match:
                errors.append(f"{path} has no frontmatter block")
                continue

            fields, problems = parse_frontmatter(match.group(1))
            errors.extend(f"{path} {problem}" for problem in problems)
            name = fields.get("name", "")
            if not name:
                errors.append(f"{path} has no name")
            elif name != skill_dir.name:
                errors.append(f"{path} name {name!r} does not match its directory")
            if not fields.get("description"):
                errors.append(f"{path} has no description")


def declared_tools(skill_dir: Path, repo_root: Path, errors: list) -> list:
    """Return the tool names a skill declares in [tool.autohooks], if any.

    `autohooks.plugins.black` names the tool `black`. Skills declaring tooling any
    other way return nothing — see docs/adr/006.

    The shape is checked rather than assumed, because every malformed form fails
    open: a bare string iterates into single characters, a table iterates into its
    keys, and a trailing dot trims to the empty string — which is a substring of any
    workflow, so the mirror check downstream passes having verified nothing.
    """
    path = skill_dir / PYPROJECT_FILENAME
    if not (repo_root / path).exists():
        return []

    try:
        with (repo_root / path).open("rb") as handle:
            config = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"{path} is not valid TOML: {exc}")
        return []

    # Absent means the skill declares no hooks, which is fine. Present but the wrong
    # type is a declaration nobody can read, and returning [] for it would report the
    # mirror intact having checked nothing.
    tool = config.get("tool")
    if tool is None:
        return []
    if not isinstance(tool, dict):
        errors.append(f"{path} [tool] is not a table (see docs/adr/006)")
        return []

    autohooks = tool.get("autohooks")
    if autohooks is None:
        return []
    if not isinstance(autohooks, dict):
        errors.append(f"{path} [tool.autohooks] is not a table (see docs/adr/006)")
        return []

    plugins = autohooks.get("pre-commit")
    if plugins is None:
        return []

    names = (
        [plugin.rsplit(".", 1)[-1] for plugin in plugins]
        if isinstance(plugins, list) and all(isinstance(p, str) for p in plugins)
        else None
    )
    if names is None or not all(names):
        errors.append(
            f"{path} [tool.autohooks] pre-commit must be a list of plugin names, each "
            f"ending in the tool it runs; got {plugins!r} (see docs/adr/006)"
        )
        return []
    return names


def check_skill_tooling(repo_root: Path, errors: list) -> None:
    """A skill's declared tooling must be gated by the PR workflow — see docs/adr/006.

    The workflow mirrors each skill's declaration by hand, so it would otherwise fail
    open. Two halves: a skill nothing gates at all, and a gated skill whose declaration
    grew a tool its job never runs. The second is a substring match over the whole
    workflow, so a tool named only in a comment satisfies it.
    """
    if not (repo_root / WORKFLOW_FILE).exists():
        errors.append(f"{WORKFLOW_FILE} is missing")
        return

    workflow = (repo_root / WORKFLOW_FILE).read_text(encoding="utf-8")
    for root in SKILL_ROOTS:
        if not (repo_root / root).is_dir():
            continue

        for skill_dir in skill_dirs(root, repo_root):
            markers = [m for m in TOOLING_MARKERS if (repo_root / skill_dir / m).exists()]
            if not markers:
                continue

            if skill_dir.as_posix() not in workflow:
                errors.append(
                    f"{skill_dir} ships tooling ({', '.join(markers)}) but nothing in "
                    f"{WORKFLOW_FILE} references it; add a check for it (see docs/adr/006)"
                )
                continue

            for tool in declared_tools(skill_dir, repo_root, errors):
                if tool not in workflow:
                    errors.append(
                        f"{skill_dir} declares {tool} but {WORKFLOW_FILE} never runs it; "
                        f"the workflow mirrors the declaration (see docs/adr/006)"
                    )


def validate(repo_root: Path) -> int:
    """Validate every manifest invariant. Return 0 on success, 1 on error."""
    errors: list = []
    # Loaded once and shared, so a missing manifest is reported once and the
    # marketplace check can compare names against it.
    plugin = load_json(PLUGIN_FILE, repo_root, errors)
    check_plugin(plugin, errors)
    check_marketplace(plugin, repo_root, errors)
    check_skills(repo_root, errors)
    check_skill_tooling(repo_root, errors)

    for error in errors:
        print(f"Error: {error}", file=sys.stderr)
    if errors:
        print("Fix the errors above before committing.", file=sys.stderr)
        return 1

    print("Manifests and skill frontmatter are valid")
    return 0


if __name__ == "__main__":
    sys.exit(validate(REPO_ROOT))
