"""Route docs/backlog/ items from the paths they bind — the backlog's own `for` lookup.

Standard library only, kept beside `adr.py`: the skill runs it as
`python3 ${CLAUDE_SKILL_DIR}/backlog.py for PATH ...`, and `.githooks/pre-commit` runs it
as a sibling to `adr.py`'s own `for`, over every staged path.

    backlog.py [--repo-root DIR] for PATH ...

A backlog item carries no `scope` frontmatter — `docs/backlog/`'s items are plain
Markdown (ADR 020) — so scope is derived from the reference-style link definitions every
item already ends with (`docs/backlog/README.md`'s Shape), resolved the way an ADR's own
links resolve: from the item's own file, so `../../skills/x.py` names `skills/x.py` from
the repo root (ADR 028). A link to an external URL, or into `docs/adr/` or
`docs/backlog/` itself, names a decision or a sibling item for context rather than a site
this item's own work would touch, so neither contributes to scope.

Unlike an ADR's `scope`, a dangling target here is never reported: an item naming a path
since deleted is very likely finished work that should have been deleted with it, not
rot to fix, so nothing here can fail a build the way `scope_problems()` does (ADR 028).

The tool acts on the caller's tree, resolving its root from the path in hand exactly as
`adr.py` does (ADR 024), so it has no anchor of its own to test.
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from adr import (
    ADR_DIR,
    RE_H1_TITLE,
    read_document,
    relative_to_root,
    resolve_root,
    scope_matches,
)

BACKLOG_DIR = Path("docs") / "backlog"
README_FILENAME = "README.md"

# A Markdown reference-style link definition: `[label]: target`, the label discarded.
RE_LINK_TARGET = re.compile(r"^\[[^\]]+\]:\s*(\S+)", re.MULTILINE)


@dataclass(frozen=True)
class Item:
    """One backlog item as the reverse lookup renders it: a path, since it has no number."""

    path: str
    title: str


def item_title(content: str) -> str:
    """The item's title: the first level-one heading, verbatim (no number prefix to strip)."""
    match = RE_H1_TITLE.search(content)
    return match.group(1).strip() if match else ""


def derive_scope(content: str, root: Path) -> list[str]:
    """Return the repo-relative paths one backlog item binds, derived from its own links.

    A directory link is trailing-slashed when `root` shows it really is one, so it covers
    what sits beneath it the way an ADR's `scope` does; a dangling link cannot be checked
    this way and is kept as an exact-path entry.
    """
    scope: list[str] = []
    for target in RE_LINK_TARGET.findall(content):
        if "://" in target:
            continue
        combined = os.path.normpath(str(BACKLOG_DIR / target))
        resolved = PurePosixPath(combined).as_posix()
        if resolved.startswith("../"):
            continue
        if scope_matches(f"{ADR_DIR.as_posix()}/", resolved) or scope_matches(
            f"{BACKLOG_DIR.as_posix()}/", resolved
        ):
            continue
        if (root / resolved).is_dir() and not resolved.endswith("/"):
            resolved += "/"
        if resolved not in scope:
            scope.append(resolved)
    return scope


def load_items(root: Path) -> list[tuple[Item, list[str]]]:
    """Every backlog item under `root`, paired with its derived scope.

    Skips `docs/backlog/README.md`, which states the shape rather than naming an item.
    """
    backlog_dir = root / BACKLOG_DIR
    if not backlog_dir.is_dir():
        return []
    items = []
    for path in sorted(backlog_dir.iterdir()):
        if not path.is_file() or path.suffix != ".md" or path.name == README_FILENAME:
            continue
        content = read_document(path)
        item = Item(path=(BACKLOG_DIR / path.name).as_posix(), title=item_title(content))
        items.append((item, derive_scope(content, root)))
    return items


def binding(root: Path, paths: list[str]) -> list[Item]:
    """Return the backlog items whose derived scope covers any of `paths`.

    Mirrors `adr.py`'s own `binding()`: the direction a directory listing cannot serve,
    from a file in hand to the items concerning it. A directory subject is matched with
    its trailing slash, since that is how a derived scope entry names one.
    """
    subjects = []
    for path in paths:
        relative = relative_to_root(path, root)
        if relative is None:
            continue
        if (root / relative).is_dir() and not relative.endswith("/"):
            relative += "/"
        subjects.append(relative)
    if not subjects:
        return []

    return [
        item
        for item, scope in load_items(root)
        if any(scope_matches(entry, subject) for entry in scope for subject in subjects)
    ]


def command_for(root: Path, paths: list[str], cwd: Path) -> int:
    """`for`: the reverse lookup, one line per backlog item concerning any of these paths.

    A relative path is the caller's, so it resolves against `cwd` and not against the
    root, matching `adr.py`'s own `for`.
    """
    resolved = [path if Path(path).is_absolute() else str(cwd / path) for path in paths]
    for item in binding(root, resolved):
        print(f"{item.path}: {item.title}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """The command line."""
    parser = argparse.ArgumentParser(prog="backlog.py", description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--repo-root", type=Path, help="act on this tree instead of resolving one"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    lookup = commands.add_parser("for", help="the backlog items concerning these paths")
    lookup.add_argument("paths", nargs="+")
    return parser


def main(argv: list[str], cwd: Path) -> int:
    """Run one command. `cwd` is the working directory the caller was given, never read here."""
    args = build_parser().parse_args(argv)
    root = resolve_root(cwd, args.repo_root)
    return command_for(root, args.paths, cwd)


def cli() -> int:
    """Entry point, for a consumer that packages this tool the way `adr.py` ships `phx-adr`."""
    return main(sys.argv[1:], Path.cwd())


if __name__ == "__main__":
    sys.exit(cli())
