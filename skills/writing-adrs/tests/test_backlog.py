"""Tests for `backlog.py` — derived scope, the reverse lookup, and the `for` command.

Unit classes call one function directly; `MainTests` reaches the tool through its entry
point and covers only what emerges from the composition: the exit code and stdout.

The module acts on the caller's tree and resolves its root from the path it is given
(the testing rule's caller's-tree stance, ADR 024), so it has no anchor of its own.
Every test passes a fixture root explicitly and never changes the working directory.
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from backlog import (
    BACKLOG_DIR,
    Item,
    binding,
    derive_scope,
    item_title,
    load_items,
    main,
)


class BacklogDirTestCase(unittest.TestCase):
    """A temp repository with a `docs/backlog` inside it, living for the whole test."""

    def setUp(self) -> None:
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.repo_root = Path(directory).resolve()
        self.backlog_dir = self.repo_root / BACKLOG_DIR
        self.backlog_dir.mkdir(parents=True)
        # resolve_root falls back to the nearest .git; there is no docs/adr here to manage.
        (self.repo_root / ".git").mkdir()

    def write(self, name: str, content: str) -> None:
        """Place one item file in the backlog directory."""
        (self.backlog_dir / name).write_text(content, encoding="utf-8")

    def write_target(self, relative: str) -> None:
        """Create a real file at `relative` from the repo root, for a link to resolve onto."""
        target = self.repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")

    def run_main(self, *argv: str, cwd: Path | None = None) -> tuple[int, str, str]:
        """Run the entry point against the fixture, returning its exit code with both streams."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv), cwd or self.repo_root)
        return code, out.getvalue(), err.getvalue()


def item_text(title: str = "An item", links: str = "") -> str:
    """A minimal backlog item: a title, a body, and a caller-supplied link-definitions block."""
    return (
        f"# {title}\n\n"
        "> Recorded 2026-09-05, from a test. Never filed as a GitHub issue.\n\n"
        "## What\n\nSomething.\n\n"
        "## Acceptance\n\n- Something happens.\n\n"
        f"{links}"
    )


class ItemTitleTests(unittest.TestCase):
    """Unit tests for ``item_title()``."""

    def test_returns_the_level_one_heading(self):
        """A backlog item's title is its first `#` heading, carrying no number to strip."""
        self.assertEqual(item_title("# The title\n\nBody.\n"), "The title")

    def test_returns_empty_for_no_heading(self):
        """A file with no level-one heading yields an empty title rather than raising."""
        self.assertEqual(item_title("Just body text.\n"), "")


class DeriveScopeTests(BacklogDirTestCase):
    """Unit tests for ``derive_scope()``: resolving an item's own reference links."""

    def test_resolves_a_link_relative_to_the_backlog_directory(self):
        """`../../skills/x.py` in a backlog item names `skills/x.py` from the repo root."""
        self.write_target("skills/nz-english/table.py")
        content = item_text(links="[`table.py`]: ../../skills/nz-english/table.py\n")
        self.assertEqual(derive_scope(content, self.repo_root), ["skills/nz-english/table.py"])

    def test_resolves_every_link_in_the_block_not_only_the_first(self):
        """Two linked files must both surface, so a partial parse cannot pass unnoticed."""
        self.write_target("skills/a.py")
        self.write_target("skills/b.py")
        content = item_text(links="[`a.py`]: ../../skills/a.py\n[`b.py`]: ../../skills/b.py\n")
        self.assertEqual(derive_scope(content, self.repo_root), ["skills/a.py", "skills/b.py"])

    def test_skips_an_external_url(self):
        """A GitHub issue or PR link names no file this item's own work would touch."""
        content = item_text(links="[#37]: https://github.com/todofixthis/x/pull/37\n")
        self.assertEqual(derive_scope(content, self.repo_root), [])

    def test_skips_a_url_shaped_target_engineered_to_traverse_out_of_the_prefix(self):
        """Without the URL check, enough `../` segments after a scheme spoof a real path.

        `docs/backlog/` is prepended before normalising, so most external URLs would be
        caught by the docs/backlog/ exclusion regardless of the URL check — this is the
        case that check alone catches: a target carrying its own scheme but enough `..`
        to cancel that prefix and land outside `docs/backlog/` too.
        """
        self.write_target("skills/x.py")
        content = item_text(links="[spoofed]: https://../../../skills/x.py\n")
        self.assertEqual(derive_scope(content, self.repo_root), [])

    def test_skips_a_link_into_docs_adr(self):
        """A cited ADR is context for the item, not a site its own work binds."""
        content = item_text(
            links="[ADR 020]: ../adr/020-track-deferred-work-in-the-repository.md\n"
        )
        self.assertEqual(derive_scope(content, self.repo_root), [])

    def test_skips_a_link_into_docs_backlog(self):
        """A sibling backlog item cited for context is not a scope entry either."""
        content = item_text(links="[other item]: other-item.md\n")
        self.assertEqual(derive_scope(content, self.repo_root), [])

    def test_skips_a_link_that_climbs_above_the_repository_root(self):
        """More `../` than the item's own depth would name a path outside the repo."""
        content = item_text(links="[outside]: ../../../outside.py\n")
        self.assertEqual(derive_scope(content, self.repo_root), [])

    def test_keeps_a_dangling_link_as_an_exact_path(self):
        """A target absent from disk is not checkable as a directory, so it stays exact."""
        content = item_text(links="[`gone.py`]: ../../skills/gone.py\n")
        self.assertEqual(derive_scope(content, self.repo_root), ["skills/gone.py"])

    def test_trailing_slashes_a_link_that_is_really_a_directory(self):
        """A directory link covers what sits beneath it, the way an ADR's scope does."""
        self.write_target("skills/nz-english/tests/x.py")
        content = item_text(links="[`tests/`]: ../../skills/nz-english/tests\n")
        self.assertEqual(derive_scope(content, self.repo_root), ["skills/nz-english/tests/"])

    def test_ignores_a_line_that_is_not_a_link_definition(self):
        """Ordinary prose naming a path in a code span must not be read as scope."""
        content = item_text() + "See `skills/nz-english/table.py` in prose.\n"
        self.assertEqual(derive_scope(content, self.repo_root), [])


class LoadItemsTests(BacklogDirTestCase):
    """Unit tests for ``load_items()``."""

    def test_skips_readme(self):
        """docs/backlog/README.md states the shape; it is not itself a deferred item."""
        self.write("README.md", "# Backlog\n\nShape docs.\n")
        self.assertEqual(load_items(self.repo_root), [])

    def test_returns_nothing_for_a_missing_backlog_directory(self):
        """A repository with no docs/backlog/ at all binds no items rather than raising."""
        empty_root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.assertEqual(load_items(empty_root), [])


class BindingTests(BacklogDirTestCase):
    """Unit tests for ``binding()``: the reverse lookup, directories slashed."""

    def test_reports_the_item_binding_a_staged_path(self):
        """A staged change under a path an item's derived scope covers reports that item."""
        self.write_target("skills/nz-english/table.py")
        self.write(
            "nz-english-widget.md",
            item_text(
                title="nz-english: fix the widget pattern",
                links="[`table.py`]: ../../skills/nz-english/table.py\n",
            ),
        )
        result = binding(self.repo_root, ["skills/nz-english/table.py"])
        self.assertEqual(
            result,
            [
                Item(
                    path="docs/backlog/nz-english-widget.md",
                    title="nz-english: fix the widget pattern",
                )
            ],
        )

    def test_a_dangling_scoped_item_still_matches_and_never_raises(self):
        """A path an item names that no longer exists must not fail the lookup."""
        self.write(
            "stale-item.md",
            item_text(links="[`gone.py`]: ../../skills/gone.py\n"),
        )
        result = binding(self.repo_root, ["skills/gone.py"])
        self.assertEqual([item.path for item in result], ["docs/backlog/stale-item.md"])

    def test_stays_silent_for_a_path_nothing_binds(self):
        """Most files concern no deferred item, so the common case must not cry wolf."""
        self.write_target("skills/nz-english/table.py")
        self.write(
            "nz-english-widget.md",
            item_text(links="[`table.py`]: ../../skills/nz-english/table.py\n"),
        )
        self.assertEqual(binding(self.repo_root, ["docs/unrelated.md"]), [])

    def test_matches_a_directory_token_with_or_without_its_slash(self):
        """A file beneath a scoped directory is bound, staged with or without a trailing slash."""
        self.write_target("skills/nz-english/tests/x.py")
        self.write(
            "item.md",
            item_text(links="[`tests/`]: ../../skills/nz-english/tests\n"),
        )
        self.assertEqual(
            [i.path for i in binding(self.repo_root, ["skills/nz-english/tests"])],
            ["docs/backlog/item.md"],
        )
        self.assertEqual(
            [i.path for i in binding(self.repo_root, ["skills/nz-english/tests/x.py"])],
            ["docs/backlog/item.md"],
        )

    def test_an_absolute_path_inside_the_root_matches(self):
        """An absolute path, as a hook receives it, is made repo-relative before matching."""
        self.write_target("skills/x.py")
        self.write("item.md", item_text(links="[`x.py`]: ../../skills/x.py\n"))
        absolute = str(self.repo_root / "skills" / "x.py")
        self.assertEqual(
            [i.path for i in binding(self.repo_root, [absolute])], ["docs/backlog/item.md"]
        )

    def test_a_path_outside_the_root_binds_nothing(self):
        """A path under no managed root is the answer 'nothing binds this', not an error."""
        self.write("item.md", item_text(links="[`x.py`]: ../../skills/x.py\n"))
        self.assertEqual(binding(self.repo_root, ["/nowhere/else.py"]), [])

    def test_reports_every_item_binding_the_path(self):
        """Two items can concern one file, and stopping at the first would hide the second."""
        self.write_target("skills/x.py")
        self.write("first.md", item_text(title="First", links="[`x.py`]: ../../skills/x.py\n"))
        self.write(
            "second.md", item_text(title="Second", links="[`x.py`]: ../../skills/x.py\n")
        )
        self.assertEqual(len(binding(self.repo_root, ["skills/x.py"])), 2)

    def test_matches_any_of_several_paths(self):
        """The hook passes every staged path at once, so one match in the set is enough."""
        self.write_target("skills/x.py")
        self.write("item.md", item_text(links="[`x.py`]: ../../skills/x.py\n"))
        result = binding(self.repo_root, ["docs/unrelated.md", "skills/x.py"])
        self.assertEqual([i.path for i in result], ["docs/backlog/item.md"])

    def test_readme_is_never_reported(self):
        """README.md documents the shape; it must never surface as a concerning item."""
        self.write_target("skills/x.py")
        self.write("README.md", item_text(links="[`x.py`]: ../../skills/x.py\n"))
        self.assertEqual(binding(self.repo_root, ["skills/x.py"]), [])


class MainTests(BacklogDirTestCase):
    """Integration tests: the `for` command through the real entry point."""

    def test_prints_path_and_title_for_a_bound_file(self):
        """The report names the item by its own path, since it has no number."""
        self.write_target("skills/nz-english/table.py")
        self.write(
            "nz-english-widget.md",
            item_text(
                title="nz-english: fix the widget pattern",
                links="[`table.py`]: ../../skills/nz-english/table.py\n",
            ),
        )
        code, out, err = self.run_main("for", "skills/nz-english/table.py")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(
            out, "docs/backlog/nz-english-widget.md: nz-english: fix the widget pattern\n"
        )

    def test_exits_zero_and_prints_nothing_for_an_unbound_file(self):
        """Advisory and silent: most commits touch nothing any backlog item concerns."""
        code, out, err = self.run_main("for", "docs/unrelated.md")
        self.assertEqual((code, out, err), (0, "", ""))

    def test_a_dangling_scoped_item_does_not_fail_the_command(self):
        """The acceptance bar: a backlog item naming a gone path must not fail the build."""
        self.write("stale-item.md", item_text(links="[`gone.py`]: ../../skills/gone.py\n"))
        code, out, err = self.run_main("for", "skills/gone.py")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "docs/backlog/stale-item.md: An item\n")

    def test_resolves_a_relative_path_against_cwd_not_root(self):
        """A relative path is the caller's, matching adr.py's own `for`."""
        self.write_target("skills/x.py")
        self.write("item.md", item_text(links="[`x.py`]: ../../skills/x.py\n"))
        subdir = self.repo_root / "skills"
        code, out, _ = self.run_main("for", "x.py", cwd=subdir)
        self.assertEqual(code, 0)
        self.assertEqual(out, "docs/backlog/item.md: An item\n")


if __name__ == "__main__":
    unittest.main()
