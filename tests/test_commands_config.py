"""tsk config サブコマンドのテスト。"""

from pathlib import Path

import pytest

from task_recorder_cui.commands import config as config_cmd
from task_recorder_cui.config import load_config


@pytest.fixture()
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "config.toml"
    monkeypatch.setenv("TSK_CONFIG_PATH", str(path))
    return path


def test_list_shows_all_keys(isolated_config, capsys: pytest.CaptureFixture[str]) -> None:
    rc = config_cmd.list_all()
    assert rc == 0
    out = capsys.readouterr().out
    assert "timer.enabled" in out
    assert "ui.lang" in out


def test_get_prints_value(isolated_config, capsys: pytest.CaptureFixture[str]) -> None:
    rc = config_cmd.get("timer.enabled")
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out == "True"


def test_get_unknown_key_errors(isolated_config, capsys: pytest.CaptureFixture[str]) -> None:
    rc = config_cmd.get("timer.nope")
    assert rc == 1
    err = capsys.readouterr().err
    assert "未知" in err or "timer.nope" in err


def test_set_writes_file(isolated_config: Path) -> None:
    rc = config_cmd.set_("ui.bar_color", "red")
    assert rc == 0
    assert isolated_config.exists()
    cfg = load_config()
    assert cfg.ui.bar_color == "red"


def test_set_invalid_bool_errors(isolated_config, capsys: pytest.CaptureFixture[str]) -> None:
    rc = config_cmd.set_("timer.enabled", "maybe")
    assert rc == 1
    err = capsys.readouterr().err
    assert "true" in err.lower() or "false" in err.lower()


def test_reset_restores_default(isolated_config: Path) -> None:
    config_cmd.set_("ui.bar_color", "red")
    rc = config_cmd.reset("ui.bar_color")
    assert rc == 0
    cfg = load_config()
    assert cfg.ui.bar_color == "cyan"


def test_set_sound_path_converts_windows(
    isolated_config: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows パスが normalize_user_path で POSIX に変換される。"""
    import subprocess

    from task_recorder_cui.utils import paths as paths_mod

    (tmp_path / "x.wav").write_bytes(b"")

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=str(tmp_path / "x.wav") + "\n", stderr=""
        )

    monkeypatch.setattr(paths_mod.subprocess, "run", fake_run)
    rc = config_cmd.set_("timer.sound_path", "C:\\fake\\x.wav")
    assert rc == 0
    cfg = load_config()
    assert cfg.timer.sound_path == str(tmp_path / "x.wav")
