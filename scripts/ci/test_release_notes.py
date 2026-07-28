"""Unit tests for release_notes.py.

Stdlib `unittest` rather than pytest, so the suite needs no dependency of its own
(ADR 007). Run from the repo root:

    python3 -m unittest discover -s scripts/ci -t scripts/ci -p 'test_*.py'
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import release_notes
from release_notes import main, plugin_version, top_entry

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
def release_files(changelog: str = CHANGELOG, version: str = "1.3.0"):
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
    def test_reads_the_declared_version(self):
        """The version comes from the manifest's `version` field."""
        with release_files(version="9.9.9") as root:
            self.assertEqual(
                plugin_version(root / release_notes.DEFAULT_PLUGIN_FILE), "9.9.9"
            )

    def test_unusable_version_raises(self):
        """A manifest missing a usable version is an error, not an empty string."""
        with release_files(version="") as root:
            with self.assertRaises(ValueError):
                plugin_version(root / release_notes.DEFAULT_PLUGIN_FILE)


class CliTests(unittest.TestCase):
    def test_defaults_resolve_against_the_working_directory(self):
        """With no path arguments, the default paths locate the repo's own files."""
        with release_files() as root, contextlib.chdir(root):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main([])
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
                        str(root / release_notes.DEFAULT_CHANGELOG_FILE),
                        "--plugin-manifest",
                        str(root / release_notes.DEFAULT_PLUGIN_FILE),
                        "--out",
                        str(out),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(stdout.getvalue(), "1.3.0\n")
            self.assertEqual(out.read_text(encoding="utf-8"), f"{TOP_NOTES}\n")

    def test_version_mismatch_returns_nonzero(self):
        """A changelog ahead of (or behind) the manifest fails the release."""
        with release_files(version="1.2.0") as root, contextlib.chdir(root):
            with contextlib.redirect_stderr(io.StringIO()):
                code = main([])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
