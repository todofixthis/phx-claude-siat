"""Parse the flat YAML frontmatter used by ADRs and skill files.

Shared by scripts/adr and scripts/ci, which previously kept adapted copies that
drifted (ADR 007's revisit trigger). Stdlib-only by design: frontmatter here is a
flat key/value block, so a line parser suffices and the repo needs no PyYAML.

Every field must sit on one line. Wrapping is the failure this module exists to
catch: a continuation line parses to whatever fitted on the first line, and where
that continuation happens to contain a colon it also invents a key, so the real
value is truncated and nothing looks wrong.
"""

import re

# A value of `>` or `|` opens a block scalar, whose continuation lines a line
# parser cannot see. Trailing chomping indicators (`-`, `+`) included.
RE_BLOCK_SCALAR = re.compile(r"^[>|][-+]?$")

RE_WHITESPACE = re.compile(r"\s")


def parse_frontmatter(block: str) -> tuple[dict, list[str]]:
    """Parse a frontmatter block into a dict, plus any problems found.

    Handles `key: value` scalars and `key: [a, b, c]` inline lists. List values
    become list[str]; scalars stay str. Skill frontmatter uses no lists, but
    parsing the superset lets both callers share one implementation.
    """
    fields: dict = {}
    problems: list[str] = []
    for line in block.splitlines():
        if not line.strip():
            continue
        # Top-level keys start at column 0, so anything indented continues the
        # line above — including a continuation with no colon in it at all.
        if line[:1].isspace():
            problems.append(f"continued onto another line; wrap it onto one: {line.strip()!r}")
            continue
        if ":" not in line:
            problems.append(f"is not `key: value`: {line.strip()!r}")
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Every key in use is a single word, so whitespace means this line is
        # really an unindented continuation whose prose contained a colon.
        if RE_WHITESPACE.search(key):
            problems.append(f"has a key containing whitespace, so it reads as a wrapped line: {key!r}")
            continue
        if RE_BLOCK_SCALAR.match(value):
            problems.append(f"field {key} uses a block scalar; put it on one line")
            continue
        if key in fields:
            problems.append(f"sets field {key} twice; the later value silently wins")
            continue
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip() for item in value[1:-1].split(",")]
            fields[key] = [item for item in items if item]
        else:
            fields[key] = value
    return fields, problems
