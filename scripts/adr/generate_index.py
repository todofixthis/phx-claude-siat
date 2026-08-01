#!/usr/bin/env python3
"""Regenerate docs/adr/INDEX.md from ADR frontmatter.

Run manually from the repo root: python3 scripts/adr/generate_index.py
Run automatically by .githooks/pre-commit when ADR files are staged.

Stdlib-only by design (ADR 007): ADR frontmatter is a flat key/value block, so a
small line parser suffices and the repo needs no Python project (or PyYAML) at its
root.
"""

import re
import sys
from pathlib import Path

ADR_DIR = Path("docs/adr")
INDEX_FILE = ADR_DIR / "INDEX.md"

STATUSES = ("Accepted", "Archived", "Superseded")

# Kept out of the index an agent loads by default: Superseded because a later ADR
# replaced it, Archived because the decision stands but isn't worth carrying. Both
# stay in the repo.
HIDDEN_STATUSES = ("Archived", "Superseded")

# A value of `>` or `|` opens a YAML block scalar, whose continuation lines this
# parser cannot see. Trailing chomping indicators (`-`, `+`) included.
RE_BLOCK_SCALAR = re.compile(r"^[>|][-+]?$")

RE_ADR_FILENAME = re.compile(r"^\d+-.*\.md$")
RE_FILE_NUMBER = re.compile(r"^(\d+)")
RE_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
RE_H1_TITLE = re.compile(r"^# (.+)$", re.MULTILINE)
RE_NUMBER_PREFIX = re.compile(r"^\d+:\s*")


def parse_frontmatter(block: str) -> tuple[dict, list[str]]:
    """Parse a flat YAML frontmatter block into a dict, plus any problems found.

    Handles `key: value` scalars and `key: [a, b, c]` inline lists — the only
    shapes ADR frontmatter uses. List values become list[str]; scalars stay str.

    Every field must sit on one line. A wrapped value or a block scalar would
    otherwise parse to whatever fitted on the first line and produce a truncated
    index row with no error, so both are reported rather than skipped.
    """
    fields: dict = {}
    problems: list[str] = []
    for line in block.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            problems.append(
                f"frontmatter line is not `key: value` — wrap onto one line: {line.strip()!r}"
            )
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if RE_BLOCK_SCALAR.match(value):
            problems.append(f"frontmatter field {key} uses a block scalar; put it on one line")
            continue
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip() for item in value[1:-1].split(",")]
            fields[key] = [item for item in items if item]
        else:
            fields[key] = value
    return fields, problems


def parse_adr(content: str):
    """Return (frontmatter, title, problems) for an ADR, or None if either is missing."""
    match = RE_FRONTMATTER.match(content)
    if not match:
        return None
    title_match = RE_H1_TITLE.search(match.group(2))
    if not title_match:
        return None
    title = RE_NUMBER_PREFIX.sub("", title_match.group(1).strip())
    fields, problems = parse_frontmatter(match.group(1))
    return fields, title, problems


def cell(value) -> str:
    """Render a frontmatter value for a Markdown table cell, escaping pipes."""
    if isinstance(value, list):
        value = ", ".join(value)
    return value.replace("|", "\\|")


def generate() -> int:
    """Regenerate INDEX.md from ADR frontmatter. Return 0 on success, 1 on error."""
    files = sorted(f for f in ADR_DIR.iterdir() if RE_ADR_FILENAME.match(f.name))

    rows = []
    has_errors = False
    for path in files:
        parsed = parse_adr(path.read_text(encoding="utf-8"))
        if not parsed:
            print(
                f"Error: {path.name} is missing frontmatter or a title heading",
                file=sys.stderr,
            )
            has_errors = True
            continue
        fields, title, problems = parsed
        for problem in problems:
            print(f"Error: {path.name} {problem}", file=sys.stderr)
            has_errors = True

        # Checked before the skip below, so a typo excludes nothing silently: an
        # unrecognised status would otherwise land in the index as a literal, and a
        # misspelled hidden one would publish an ADR meant to stay out.
        status = fields.get("status")
        if status not in STATUSES:
            print(
                f"Error: {path.name} has status {status!r}; expected one of "
                f"{', '.join(STATUSES)}",
                file=sys.stderr,
            )
            has_errors = True
            continue
        if status in HIDDEN_STATUSES:
            continue
        number_match = RE_FILE_NUMBER.match(path.name)
        if not number_match:
            print(f"Error: {path.name} has no leading number", file=sys.stderr)
            has_errors = True
            continue
        rows.append(
            f"| [{number_match.group(1)}]({path.name}) | {cell(fields.get('status', ''))} "
            f"| {cell(title)} | {cell(fields.get('tags', []))} | {cell(fields.get('summary', ''))} |"
        )

    if has_errors:
        print("Fix the errors above before committing.", file=sys.stderr)
        return 1

    output = "\n".join(
        [
            "<!-- Auto-generated by scripts/adr/generate_index.py — do not edit manually. -->",
            "",
            "# ADR Index",
            "",
            "| # | Status | Title | Tags | Summary |",
            "|---|--------|-------|------|---------|",
            *rows,
            "",
        ]
    )
    INDEX_FILE.write_text(output, encoding="utf-8")
    print(f"Generated {INDEX_FILE} ({len(rows)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(generate())
