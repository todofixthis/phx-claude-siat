import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from release_notes import main, plugin_version, top_entry

CHANGELOG = """# Changelog

## 1.3.0 - 2026-07-22

### For phx plugin users

#### Changed

- Something changed.

## 1.2.0 - 2026-07-16

- Older entry.
"""


class TopEntryTests(unittest.TestCase):
    def test_returns_newest_version(self):
        version, _ = top_entry(CHANGELOG)
        self.assertEqual(version, "1.3.0")

    def test_notes_stop_before_the_previous_entry(self):
        _, notes = top_entry(CHANGELOG)
        self.assertIn("Something changed.", notes)
        self.assertNotIn("Older entry.", notes)

    def test_subsection_headers_are_not_boundaries(self):
        _, notes = top_entry(CHANGELOG)
        self.assertIn("#### Changed", notes)

    def test_missing_entry_raises(self):
        with self.assertRaises(ValueError):
            top_entry("# Changelog\n\nNo entries yet.\n")


class CliTests(unittest.TestCase):
    def test_version_mismatch_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            changelog = Path(directory) / "CHANGELOG.md"
            changelog.write_text("# Changelog\n\n## 1.3.0 - 2026-07-22\n\n- x\n")
            plugin = Path(directory) / "plugin.json"
            plugin.write_text('{"version": "1.2.0"}')
            out = Path(directory) / "notes.md"
            with contextlib.redirect_stderr(io.StringIO()):
                code = main(
                    ["--changelog", str(changelog), "--plugin", str(plugin),
                     "--out", str(out)]
                )
            self.assertEqual(code, 1)

    def test_plugin_version_reads_the_field(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin.json"
            plugin.write_text('{"version": "9.9.9"}')
            self.assertEqual(plugin_version(plugin), "9.9.9")


if __name__ == "__main__":
    unittest.main()
