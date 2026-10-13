"""Parse the flat YAML frontmatter used by ADRs and skill files.

Ships with the writing-adrs skill and is reached from this repository's `scripts/`
through a symlink, so there is one parser for the ADR tool and the manifest validator.

Two layers decide what a block means. The line rules are this repository's own and
stricter than YAML: every *value* sits on one line, though a key may open an indented
block sequence. Wrapping is the failure they exist to catch: a continuation line parses
to whatever fitted on the first line, and where that continuation happens to contain a
colon it also invents a key, so the real value is truncated and nothing looks wrong.
The values themselves are YAML's, decided by PyYAML field by field, with no type
resolution, so numbers, booleans and dates stay text. A comment, tag, anchor or alias
inside a value is reported rather than honoured, since YAML drops each without a word.
"""

import re

import yaml

# A value of `>` or `|` opens a block scalar, whose continuation lines a line
# parser cannot see. Trailing chomping indicators (`-`, `+`) included.
RE_BLOCK_SCALAR = re.compile(r"^[>|][-+]?$")

RE_WHITESPACE = re.compile(r"\s")

# libyaml's loader where PyYAML was built with it, the pure-Python one otherwise.
# Neither resolves types, so every scalar loads as a string.
LOADER = yaml.CBaseLoader if yaml.__with_libyaml__ else yaml.BaseLoader

# Tokens that mark no text of their own; the pure-Python scanner places them at the end
# of a single-line input where libyaml places them on the next line, so counting them
# would hide a trailing comment under the fallback loader.
IGNORED_TOKENS = (yaml.StreamStartToken, yaml.StreamEndToken, yaml.BlockEndToken)

# Tokens that load as the node they decorate, dropping what was written.
DROPPED_TOKENS = {
    yaml.TagToken: "tag",
    yaml.AnchorToken: "anchor",
    yaml.AliasToken: "alias",
}


def _undecorated_problem(text: str) -> str | None:
    """Name the comment, tag, anchor or alias `text` holds, or None if it holds none.

    Whole-line comments are gone before this runs, so non-blank text after the last
    token ending on a line can only be an inline comment.
    """
    # Split on "\n" alone: `str.splitlines()` also splits on separators YAML treats as text.
    lines = text.split("\n")
    last_end: dict[int, int] = {}
    for token in yaml.scan(text, Loader=LOADER):
        for kind, name in DROPPED_TOKENS.items():
            if isinstance(token, kind):
                return name
        if isinstance(token, IGNORED_TOKENS):
            continue
        end = token.end_mark
        last_end[end.line] = max(last_end.get(end.line, 0), end.column)
    for number, column in last_end.items():
        if number < len(lines) and lines[number][column:].strip():
            return "comment"
    return None


def _load_field(key: str, lines: list[str]) -> tuple[str | list[str] | None, str | None]:
    """Load one field's raw lines, returning its value or the problem with it."""
    text = "\n".join(lines)
    try:
        document = yaml.load(text, Loader=LOADER)
        decorated = _undecorated_problem(text)
    except yaml.YAMLError as exc:
        reason = getattr(exc, "problem", None) or str(exc)
        return None, f"field {key} is not valid YAML; quote the value: {reason}"
    # YAML strips quotes from a key, so a quoted key loads under a different name; a line
    # separator YAML breaks on inside the value loads as a second key.
    if isinstance(document, dict) and len(document) > 1:
        return None, (
            f"field {key}: YAML reads more than one key here "
            "(a line separator inside the value?); remove it or quote the value"
        )
    if not isinstance(document, dict) or list(document) != [key]:
        return None, f"field {key} has a quoted key; write the key unquoted"
    value = document[key]
    if decorated:
        return None, (
            f"field {key} holds a {decorated}, which YAML drops; "
            f"quote the whole value or delete the {decorated}"
        )
    if isinstance(value, str) or (
        isinstance(value, list) and all(isinstance(item, str) for item in value)
    ):
        return value, None
    kind = "mapping" if isinstance(value, dict) else "list holding a non-text item"
    return None, f"field {key} holds a {kind}, not text or a list of text; quote it"


def parse_frontmatter(block: str) -> tuple[dict[str, str | list[str]], list[str]]:
    """Parse a frontmatter block into a dict, plus any problems found.

    Handles `key: value` scalars, `key: [a, b, c]` inline lists and indented block
    sequences. List values become list[str]; scalars stay str. Skill frontmatter uses
    no inline lists, but parsing the superset lets both callers share one implementation.
    """
    # Raw lines per accepted field, in order: the key line plus its `- item` lines.
    raw: dict[str, list[str]] = {}
    problems: list[str] = []
    sequence_key: str | None = None
    # "\n" alone, for the same reason as above: a stray separator must not invent a key.
    for line in block.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[:1].isspace():
            # An indented `- item` continues a block sequence opened by the key
            # above; anything else indented is a value wrapped onto a second line,
            # which would otherwise parse as whatever fitted on the first.
            if sequence_key is not None and stripped.startswith("- "):
                raw[sequence_key].append(line)
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
        if key in raw:
            problems.append(f"sets field {key} twice; the first value stands")
            continue
        # Rebuilt from the stripped parts, so spacing around the key and colon is
        # formatting rather than something YAML could object to.
        raw[key] = [f"{key}: {value}" if value else f"{key}:"]
        # A bare `key:` opens a block sequence if indented `- item` lines follow,
        # and stays an empty value if none do.
        if not value:
            sequence_key = key
    fields: dict[str, str | list[str]] = {}
    for key, lines in raw.items():
        value, problem = _load_field(key, lines)
        if problem:
            problems.append(problem)
        else:
            fields[key] = value
    return fields, problems
