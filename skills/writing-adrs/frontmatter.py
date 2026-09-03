"""Parse the flat YAML frontmatter used by ADRs and skill files.

Ships with the writing-adrs skill and is reached from this repository's `scripts/`
through a symlink, so there is one parser for the ADR tool and the manifest validator.
Standard library only, so it runs wherever python3 does: frontmatter here is a flat
key/value block, and a line parser suffices.

Every *value* sits on one line, though a key may open an indented block sequence.
Wrapping is the failure this module exists to catch: a continuation line parses to
whatever fitted on the first line, and where that continuation happens to contain a
colon it also invents a key, so the real value is truncated and nothing looks wrong.
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
    sequence_key: str | None = None
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[:1].isspace():
            # An indented `- item` continues a block sequence opened by the key
            # above; anything else indented is a value wrapped onto a second line,
            # which would otherwise parse as whatever fitted on the first.
            if sequence_key is not None and stripped.startswith("- "):
                if not isinstance(fields[sequence_key], list):
                    fields[sequence_key] = []
                fields[sequence_key].append(stripped[2:].strip())
            else:
                problems.append(f"continued onto another line; wrap it onto one: {stripped!r}")
            continue
        sequence_key = None
        if ":" not in line:
            problems.append(f"is not `key: value`: {stripped!r}")
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Every key in use is a single word, so whitespace means this line is
        # really an unindented continuation whose prose contained a colon.
        if RE_WHITESPACE.search(key):
            problems.append(
                f"has a key containing whitespace, so it reads as a wrapped line: {key!r}"
            )
            continue
        if RE_BLOCK_SCALAR.match(value):
            problems.append(f"field {key} uses a block scalar; put it on one line")
            continue
        if key in fields:
            problems.append(f"sets field {key} twice; the first value stands")
            continue
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip() for item in value[1:-1].split(",")]
            fields[key] = [item for item in items if item]
        else:
            fields[key] = value
            # A bare `key:` opens a block sequence if indented `- item` lines
            # follow, and stays an empty value if none do.
            if not value:
                sequence_key = key
    return fields, problems
