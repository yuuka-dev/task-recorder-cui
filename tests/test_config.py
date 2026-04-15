"""config のテスト (デフォルト値、読み書き、key アクセス)。"""

from pathlib import Path

import pytest

from task_recorder_cui.config import (
    Config,
    TimerConfig,
    UIConfig,
    all_keys,
    default_config,
    dump_toml,
    get_config_path,
    get_value,
    load_config,
    reset_value,
    save_config,
    set_value,
)


def test_default_config_has_timer_and_ui() -> None:
    cfg = default_config()
    assert isinstance(cfg, Config)
    assert isinstance(cfg.timer, TimerConfig)
    assert isinstance(cfg.ui, UIConfig)


def test_default_timer_values() -> None:
    cfg = default_config()
    assert cfg.timer.enabled is True
    assert cfg.timer.sound_path == "/mnt/c/Windows/Media/Alarm01.wav"
    assert cfg.timer.notify_when_closed is True


def test_default_ui_values() -> None:
    cfg = default_config()
    assert cfg.ui.lang == ""
    assert cfg.ui.bar_color == "cyan"
    assert cfg.ui.bar_style == "solid"


def test_get_config_path_uses_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config.toml"
    monkeypatch.setenv("TSK_CONFIG_PATH", str(path))
    assert get_config_path() == path


def test_get_config_path_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TSK_CONFIG_PATH", raising=False)
    monkeypatch.setenv("HOME", "/home/fake")
    assert get_config_path() == Path("/home/fake/.config/tsk/config.toml")


def test_load_config_returns_default_when_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TSK_CONFIG_PATH", str(tmp_path / "absent.toml"))
    cfg = load_config()
    assert cfg.ui.lang == ""


def test_save_and_load_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config.toml"
    monkeypatch.setenv("TSK_CONFIG_PATH", str(path))
    cfg = Config(
        timer=TimerConfig(enabled=False, sound_path="/tmp/x.wav", notify_when_closed=False),
        ui=UIConfig(lang="en", bar_color="magenta", bar_style="rainbow"),
    )
    save_config(cfg)
    assert path.exists()
    loaded = load_config()
    assert loaded == cfg


def test_dump_toml_format() -> None:
    cfg = Config(
        timer=TimerConfig(enabled=True, sound_path="/tmp/a.wav", notify_when_closed=False),
        ui=UIConfig(lang="ja", bar_color="cyan", bar_style="solid"),
    )
    text = dump_toml(cfg)
    assert "[timer]" in text
    assert 'sound_path = "/tmp/a.wav"' in text
    assert "enabled = true" in text
    assert "notify_when_closed = false" in text
    assert "[ui]" in text
    assert 'lang = "ja"' in text


def test_load_config_with_partial_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """一部キーしか書かれてない config でもデフォルトで埋められる。"""
    path = tmp_path / "partial.toml"
    path.write_text('[timer]\nsound_path = "/tmp/other.wav"\n', encoding="utf-8")
    monkeypatch.setenv("TSK_CONFIG_PATH", str(path))
    cfg = load_config()
    assert cfg.timer.sound_path == "/tmp/other.wav"
    assert cfg.timer.enabled is True
    assert cfg.ui.lang == ""


def test_get_value_nested_key() -> None:
    cfg = Config(
        timer=TimerConfig(sound_path="/tmp/x.wav"),
        ui=UIConfig(bar_color="magenta"),
    )
    assert get_value(cfg, "timer.sound_path") == "/tmp/x.wav"
    assert get_value(cfg, "ui.bar_color") == "magenta"
    assert get_value(cfg, "timer.enabled") is True


def test_get_value_rejects_unknown_key() -> None:
    with pytest.raises(KeyError, match="timer.xxx"):
        get_value(default_config(), "timer.xxx")


def test_set_value_returns_new_config() -> None:
    cfg = default_config()
    updated = set_value(cfg, "timer.sound_path", "/tmp/new.wav")
    assert updated.timer.sound_path == "/tmp/new.wav"
    assert cfg.timer.sound_path != "/tmp/new.wav"


def test_set_value_coerces_bool() -> None:
    cfg = default_config()
    updated = set_value(cfg, "timer.enabled", "false")
    assert updated.timer.enabled is False
    updated2 = set_value(cfg, "timer.enabled", "true")
    assert updated2.timer.enabled is True


def test_set_value_rejects_invalid_bool() -> None:
    with pytest.raises(ValueError, match="true/false"):
        set_value(default_config(), "timer.enabled", "yes")


def test_reset_value() -> None:
    cfg = Config(timer=TimerConfig(sound_path="/tmp/custom.wav"))
    reset = reset_value(cfg, "timer.sound_path")
    assert reset.timer.sound_path == TimerConfig.sound_path


def test_iter_all_keys() -> None:
    keys = set(all_keys())
    assert "timer.enabled" in keys
    assert "timer.sound_path" in keys
    assert "timer.notify_when_closed" in keys
    assert "ui.lang" in keys
    assert "ui.bar_color" in keys
    assert "ui.bar_style" in keys
    assert len(keys) == 6
