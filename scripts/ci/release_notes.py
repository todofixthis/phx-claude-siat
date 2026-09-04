"""Extract the top CHANGELOG entry and assert it matches plugin.json's version.

Stdlib-only, run from the repo root (ADR 007): the repo carries no root Python
project. Prints the version to stdout and writes the notes to `--out`:

    python3 -m scripts.ci.release_notes --out notes.md
"""

import argparse
import json
import re
import sys
from pathlib import Path

from scripts.ci.versions import RE_VERSION, VERSION

# Every path below is repo-relative and joined to a `repo_root` where it is read, and
# `REPO_ROOT` is read only on the `__main__` line (ADR 027): nothing resolves a default
# path against whichever tree the caller happens to be standing in.
REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CHANGELOG_FILE = Path("CHANGELOG.md")
DEFAULT_PLUGIN_FILE = Path(".claude-plugin/plugin.json")

DATE = r"\d{4}-\d{2}-\d{2}"

# A version-entry heading: "## X.Y.Z - YYYY-MM-DD". Sub-sections use ### / ####,
# which this does not match (character 3 is "#", not a space).
RE_ENTRY = re.compile(rf"^## (?P<version>{VERSION}) - {DATE}\s*$")

# The same heading with any version shape, including ones RE_ENTRY rejects.
# Matching this but not RE_ENTRY is an error rather than a miss: falling through
# to the entry below would publish the previous release's notes under this
# release's tag.
RE_ANY_ENTRY = re.compile(rf"^## (?P<version>\S+) - {DATE}\s*$")


def plugin_version(plugin_file: Path, repo_root: Path) -> str:
    """Return the version the plugin manifest declares.

    `plugin_file` is repo-relative and names the file in the error; `repo_root` locates it.

    This is the plugin's version, not the marketplace's — the marketplace entry
    carries no version at all (ADR 001).
    """
    content = (repo_root / plugin_file).read_text(encoding="utf-8")
    version = json.loads(content).get("version", "")
    if not RE_VERSION.match(version):
        raise ValueError(f"{plugin_file} declares no usable version: {version!r}")
    return version


def top_entry(changelog: str) -> tuple[str, str]:
    """Return (version, notes) for the newest CHANGELOG entry.

    notes is every line after the heading up to (not including) the next entry
    heading, stripped of surrounding whitespace.
    """
    lines = changelog.splitlines()
    start = None
    version = None
    for index, line in enumerate(lines):
        if match := RE_ENTRY.match(line):
            start, version = index, match.group("version")
            break
        if unsupported := RE_ANY_ENTRY.match(line):
            raise ValueError(
                f"{unsupported.group('version')} is not a releasable version: this"
                " project publishes X.Y.Z only, with no pre-release suffix or build"
                " metadata (see docs/adr/008)"
            )
    if start is None:
        raise ValueError("no '## X.Y.Z - DATE' entry found in CHANGELOG")
    body = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    notes = "\n".join(body).strip()
    if not notes:
        raise ValueError(f"the {version} CHANGELOG entry is empty")
    return version, notes


def main(argv: list[str], repo_root: Path) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # Both stay repo-relative and are joined to `repo_root` where they are read (ADR 027),
    # so an error names the path a reader can act on. Joining an absolute path a caller
    # passed is a no-op, and a relative one they passed resolves against the repo, which
    # is the whole point of the anchor.
    parser.add_argument("--changelog", type=Path, default=DEFAULT_CHANGELOG_FILE)
    parser.add_argument("--plugin-manifest", type=Path, default=DEFAULT_PLUGIN_FILE)
    parser.add_argument("--out", type=Path, help="write notes here instead of stdout")
    args = parser.parse_args(argv)

    version, notes = top_entry((repo_root / args.changelog).read_text(encoding="utf-8"))
    declared = plugin_version(args.plugin_manifest, repo_root)
    if version != declared:
        print(
            f"CHANGELOG top entry is {version} but plugin.json is {declared}",
            file=sys.stderr,
        )
        return 1
    print(version)
    if args.out:
        args.out.write_text(f"{notes}\n", encoding="utf-8")
    else:
        sys.stdout.write(f"{notes}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], REPO_ROOT))
