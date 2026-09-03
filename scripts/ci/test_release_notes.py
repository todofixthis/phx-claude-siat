"""Tests for release_notes.py.

Stdlib `unittest` rather than pytest, so the suite needs no dependency of its own
(ADR 007). Run from the repo root:

    python3 -m unittest discover -s scripts -t . -p 'test_*.py'

The subject joins every path to a `repo_root` its entry point requires (ADR 027), so these
tests pass a fixture root and never `chdir`. The one test that does change directory
asserts that a `chdir` *cannot* redirect the anchored root, and reads the constant rather
than calling the subject.
"""

import contextlib
import io
import json
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path

from scripts.ci import release_notes
from scripts.ci.release_notes import REPO_ROOT, main, plugin_version, top_entry

CHANGELOG = """# Changelog

## 1.3.0 - 2026-07-22

### For phx plugin users

#### Changed

- Something changed.

## 1.2.0 - 2026-07-16

- Older entry.
"""

TOP_NOTES = """### For phx plugin users

#### Changed

- Something changed."""


@contextlib.contextmanager
def release_files(changelog: str = CHANGELOG, version: str = "1.3.0") -> Iterator[Path]:
    """Yield a temp directory holding a changelog and manifest at their default paths."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / release_notes.DEFAULT_CHANGELOG_FILE).write_text(
            changelog, encoding="utf-8"
        )
        manifest = root / release_notes.DEFAULT_PLUGIN_FILE
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"version": version}), encoding="utf-8")
        yield root


class TopEntryTests(unittest.TestCase):
    """Unit tests for ``top_entry()``."""

    def test_returns_the_newest_version(self):
        """The version comes from the first entry heading, not a later one."""
        version, _ = top_entry(CHANGELOG)
        self.assertEqual(version, "1.3.0")

    def test_notes_span_the_entry_and_stop_at_the_next(self):
        """Notes keep the entry's sub-headings but exclude the previous entry."""
        _, notes = top_entry(CHANGELOG)
        self.assertEqual(notes, TOP_NOTES)

    def test_missing_entry_raises(self):
        """A changelog with no version heading is an error, not an empty release."""
        with self.assertRaises(ValueError):
            top_entry("# Changelog\n\nNo entries yet.\n")

    def test_unreleasable_version_raises(self):
        """A pre-release heading fails loudly rather than falling through (ADR 008)."""
        changelog = "# Changelog\n\n## 1.4.0-rc.1 - 2026-07-22\n\n- x\n\n" + CHANGELOG
        with self.assertRaisesRegex(ValueError, "1.4.0-rc.1"):
            top_entry(changelog)

    def test_leading_zero_version_raises(self):
        """The heading shape is the shared one, which no-leading-zeros is part of."""
        with self.assertRaisesRegex(ValueError, "01.2.3"):
            top_entry("# Changelog\n\n## 01.2.3 - 2026-07-22\n\n- x\n")

    def test_empty_entry_raises(self):
        """An entry with no body would publish an empty release."""
        with self.assertRaises(ValueError):
            top_entry("# Changelog\n\n## 1.3.0 - 2026-07-22\n")


class PluginVersionTests(unittest.TestCase):
    """Unit tests for ``plugin_version()``."""

    def test_reads_the_declared_version(self):
        """The version comes from the manifest's `version` field."""
        with release_files(version="9.9.9") as root:
            self.assertEqual(
                plugin_version(release_notes.DEFAULT_PLUGIN_FILE, root), "9.9.9"
            )

    def test_unusable_version_raises(self):
        """A manifest missing a usable version is an error, not an empty string."""
        with release_files(version="") as root:
            with self.assertRaises(ValueError):
                plugin_version(release_notes.DEFAULT_PLUGIN_FILE, root)


class CliTests(unittest.TestCase):
    """Integration tests: the command line, end to end over real files."""

    def test_defaults_resolve_against_the_injected_root(self):
        """With no path arguments, the defaults locate the files under the root passed in."""
        with release_files() as root:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main([], root)
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), f"1.3.0\n{TOP_NOTES}\n")

    def test_out_writes_the_notes_file(self):
        """--out diverts the notes to a file, leaving only the version on stdout."""
        with release_files() as root:
            out = root / "notes.md"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(
                    [
                        "--changelog",
                        str(release_notes.DEFAULT_CHANGELOG_FILE),
                        "--plugin-manifest",
                        str(release_notes.DEFAULT_PLUGIN_FILE),
                        "--out",
                        str(out),
                    ],
                    root,
                )
            self.assertEqual(code, 0)
            self.assertEqual(stdout.getvalue(), "1.3.0\n")
            self.assertEqual(out.read_text(encoding="utf-8"), f"{TOP_NOTES}\n")

    def test_version_mismatch_returns_nonzero(self):
        """A changelog ahead of (or behind) the manifest fails the release."""
        with release_files(version="1.2.0") as root:
            with contextlib.redirect_stderr(io.StringIO()):
                code = main([], root)
            self.assertEqual(code, 1)


class RepoRootTests(unittest.TestCase):
    """Unit tests for ``REPO_ROOT``: the one path the module resolves for itself."""

    def test_chdir_cannot_redirect_the_anchor(self):
        """The anchor names the tree the module ships in, wherever the caller stands."""
        with tempfile.TemporaryDirectory() as directory:
            with contextlib.chdir(directory):
                self.assertTrue(REPO_ROOT.is_absolute())
                self.assertFalse(REPO_ROOT.is_relative_to(directory))

    def test_root_is_this_repository(self):
        """The anchor has to reach the real repo, not merely some absolute directory."""
        self.assertTrue(Path(__file__).resolve().is_relative_to(REPO_ROOT))
        self.assertTrue((REPO_ROOT / release_notes.DEFAULT_PLUGIN_FILE).is_file())


if __name__ == "__main__":
    unittest.main()
