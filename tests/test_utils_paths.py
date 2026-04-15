"""utils.paths のテスト。"""

from pathlib import Path

import pytest

from task_recorder_cui.utils.paths import (
    is_windows_path,
    normalize_user_path,
    to_windows_path,
)


def test_is_windows_path_detects_drive_letter() -> None:
    assert is_windows_path("C:\\Windows\\Media\\a.wav") is True
    assert is_windows_path("c:\\users\\foo") is True


def test_is_windows_path_detects_unc() -> None:
    assert is_windows_path("\\\\wsl$\\Ubuntu\\home") is True


def test_is_windows_path_false_for_posix() -> None:
    assert is_windows_path("/mnt/c/Windows/Media/a.wav") is False
    assert is_windows_path("/home/user/file") is False
    assert is_windows_path("~/file") is False


def test_normalize_user_path_posix_passthrough(tmp_path: Path) -> None:
    """POSIX パスはそのまま Path で返る。"""
    p = tmp_path / "sample.wav"
    p.write_bytes(b"")
    result = normalize_user_path(str(p))
    assert result == p


def test_normalize_user_path_expanduser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """'~' がホームディレクトリに展開される。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "sample.wav").write_bytes(b"")
    result = normalize_user_path("~/sample.wav")
    assert result == tmp_path / "sample.wav"


def test_normalize_user_path_windows_converts_via_wslpath(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows パスは wslpath -u で変換される (subprocess をモック)。"""
    import subprocess

    from task_recorder_cui.utils import paths as paths_mod

    (tmp_path / "out.wav").write_bytes(b"")

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "wslpath"
        assert cmd[1] == "-u"
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=str(tmp_path / "out.wav") + "\n", stderr=""
        )

    monkeypatch.setattr(paths_mod.subprocess, "run", fake_run)
    result = normalize_user_path("C:\\Windows\\Media\\out.wav")
    assert result == tmp_path / "out.wav"


def test_normalize_user_path_nonexistent_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        normalize_user_path(str(tmp_path / "nope.wav"))


def test_to_windows_path_converts_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    """POSIX パスを Windows 形式に変換する (wslpath -w)。"""
    import subprocess

    from task_recorder_cui.utils import paths as paths_mod

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "wslpath"
        assert cmd[1] == "-w"
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="C:\\Windows\\Media\\out.wav\n", stderr=""
        )

    monkeypatch.setattr(paths_mod.subprocess, "run", fake_run)
    result = to_windows_path(Path("/mnt/c/Windows/Media/out.wav"))
    assert result == "C:\\Windows\\Media\\out.wav"
