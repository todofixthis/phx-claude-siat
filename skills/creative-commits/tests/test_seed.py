from unittest.mock import MagicMock, patch

import pytest

from seed import main


def _git_result(stdout: str, returncode: int = 0, stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def test_normal_case(capsys):
    """Two emoji in recent commits; seed differs from both — exact output format."""
    with patch("subprocess.run", return_value=_git_result("abc Fix bug 🧱\ndef Add feature 🌉\n")):
        with patch("random.choice", return_value="🌊"):
            main()

    assert capsys.readouterr().out == "seed: 🌊  off-limits: 🧱 🌉\n"


def test_retry_logic(capsys):
    """random.choice returns an off-limits emoji twice, then a clean pick on the third attempt."""
    with patch("subprocess.run", return_value=_git_result("abc Fix bug 🧱\n")):
        with patch("random.choice", side_effect=["🧱", "🧱", "🌊"]):
            main()

    assert capsys.readouterr().out == "seed: 🌊  off-limits: 🧱\n"


def test_give_up_case(capsys):
    """All 3 attempts return an off-limits emoji — last pick is used as the seed anyway."""
    with patch("subprocess.run", return_value=_git_result("abc Fix bug 🧱\n")):
        with patch("random.choice", return_value="🧱"):
            main()

    assert capsys.readouterr().out == "seed: 🧱  off-limits: 🧱\n"


def test_new_repo(capsys):
    """No commits in git log — off-limits is absent from output entirely."""
    with patch("subprocess.run", return_value=_git_result("")):
        with patch("random.choice", return_value="🌊"):
            main()

    assert capsys.readouterr().out == "seed: 🌊\n"


def test_git_nonzero_exit(capsys):
    """git exits non-zero — script exits non-zero and writes a message to stderr."""
    with patch("subprocess.run", return_value=_git_result("", returncode=128, stderr="not a git repository")):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code != 0
    assert capsys.readouterr().err != ""


def test_git_subprocess_raises(capsys):
    """subprocess.run raises OSError (git not on PATH) — script exits non-zero with message to stderr."""
    with patch("subprocess.run", side_effect=OSError("git not found")):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code != 0
    assert capsys.readouterr().err != ""
