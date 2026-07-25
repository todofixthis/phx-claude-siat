#!/usr/bin/env python3
"""Extract the top CHANGELOG entry and assert it matches plugin.json's version.

Stdlib-only, run from the repo root, for the same reason as
scripts/ci/validate_manifests.py: the repo carries no root Python project.

    python3 scripts/ci/release_notes.py --out notes.md   # prints version; notes to file
"""

import argparse
import json
import re
import sys
from pathlib import Path

CHANGELOG_FILE = Path("CHANGELOG.md")
PLUGIN_FILE = Path(".claude-plugin/plugin.json")

# A version-entry heading: "## X.Y.Z - YYYY-MM-DD". Sub-sections use ### / ####,
# which this does not match (character 3 is "#", not a space).
RE_ENTRY = re.compile(r"^## (?P<version>\d+\.\d+\.\d+) - \d{4}-\d{2}-\d{2}\s*$")


def plugin_version(plugin_file: Path = PLUGIN_FILE) -> str:
    return json.loads(plugin_file.read_text(encoding="utf-8"))["version"]


def top_entry(changelog: str) -> tuple[str, str]:
    """Return (version, notes) for the newest CHANGELOG entry.

    notes is every line after the heading up to (not including) the next
    "## " entry heading, trimmed of surrounding blank lines.
    """
    lines = changelog.splitlines()
    start = None
    version = None
    for index, line in enumerate(lines):
        match = RE_ENTRY.match(line)
        if match:
            start, version = index, match.group("version")
            break
    if start is None:
        raise ValueError("no '## X.Y.Z - DATE' entry found in CHANGELOG")
    body = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return version, "\n".join(body).strip() + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changelog", type=Path, default=CHANGELOG_FILE)
    parser.add_argument("--plugin", type=Path, default=PLUGIN_FILE)
    parser.add_argument("--out", type=Path, help="write notes here instead of stdout")
    args = parser.parse_args(argv)

    version, notes = top_entry(args.changelog.read_text(encoding="utf-8"))
    declared = plugin_version(args.plugin)
    if version != declared:
        print(
            f"CHANGELOG top entry is {version} but plugin.json is {declared}",
            file=sys.stderr,
        )
        return 1
    print(version)
    if args.out:
        args.out.write_text(notes, encoding="utf-8")
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
