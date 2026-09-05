"""Tests for `seed.py`, entry-point level throughout — the module exposes only
`main() -> None`, so every case reaches it directly rather than a lower unit.

`EmojiSelectionTests` covers a successful git log and how `main()` picks and reports a
seed against it; `GitFailureTests` covers the two ways running or reading git can fail.
"""

import contextlib
import io
import unittest
from unittest.mock import MagicMock, patch

from seed import main


def _git_result(stdout: str, returncode: int = 0, stderr: str = "") -> MagicMock:
    """Build a subprocess.CompletedProcess-shaped mock for `subprocess.run`."""
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class EmojiSelectionTests(unittest.TestCase):
    """A successful git log; which emoji `main()` picks and how it reports the pick."""

    def test_normal_case(self):
        """Two emoji in recent commits; seed differs from both — exact output format."""
        out = io.StringIO()
        with (
            patch(
                "subprocess.run",
                return_value=_git_result("abc Fix bug 🧱\ndef Add feature 🌉\n"),
            ),
            patch("random.choice", return_value="🌊"),
            contextlib.redirect_stdout(out),
        ):
            main()

        self.assertEqual(out.getvalue(), "seed: 🌊  off-limits: 🧱 🌉\n")

    def test_retry_logic(self):
        """random.choice returns an off-limits emoji twice, then a clean pick third try."""
        out = io.StringIO()
        with (
            patch("subprocess.run", return_value=_git_result("abc Fix bug 🧱\n")),
            patch("random.choice", side_effect=["🧱", "🧱", "🌊"]),
            contextlib.redirect_stdout(out),
        ):
            main()

        self.assertEqual(out.getvalue(), "seed: 🌊  off-limits: 🧱\n")

    def test_give_up_case(self):
        """All 3 attempts return an off-limits emoji — last pick is used as the seed anyway."""
        out = io.StringIO()
        with (
            patch("subprocess.run", return_value=_git_result("abc Fix bug 🧱\n")),
            patch("random.choice", return_value="🧱"),
            contextlib.redirect_stdout(out),
        ):
            main()

        self.assertEqual(out.getvalue(), "seed: 🧱  off-limits: 🧱\n")

    def test_new_repo(self):
        """No commits in git log — off-limits is absent from output entirely."""
        out = io.StringIO()
        with (
            patch("subprocess.run", return_value=_git_result("")),
            patch("random.choice", return_value="🌊"),
            contextlib.redirect_stdout(out),
        ):
            main()

        self.assertEqual(out.getvalue(), "seed: 🌊\n")


class GitFailureTests(unittest.TestCase):
    """The two ways running or reading git can fail, and what each prints to stderr."""

    def test_git_nonzero_exit(self):
        """git exits non-zero — main() exits non-zero, reporting git's own stderr."""
        err = io.StringIO()
        with (
            patch(
                "subprocess.run",
                return_value=_git_result(
                    "", returncode=128, stderr="not a git repository"
                ),
            ),
            contextlib.redirect_stderr(err),
            self.assertRaises(SystemExit) as ctx,
        ):
            main()

        self.assertNotEqual(ctx.exception.code, 0)
        self.assertEqual(err.getvalue(), "git log failed: not a git repository\n")

    def test_git_subprocess_raises(self):
        """subprocess.run raises OSError (git not on PATH) — main() reports that failure."""
        err = io.StringIO()
        with (
            patch("subprocess.run", side_effect=OSError("git not found")),
            contextlib.redirect_stderr(err),
            self.assertRaises(SystemExit) as ctx,
        ):
            main()

        self.assertNotEqual(ctx.exception.code, 0)
        self.assertEqual(err.getvalue(), "Failed to run git: git not found\n")
