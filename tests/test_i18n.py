"""i18n のヘルパ関数テスト。"""

import pytest

from task_recorder_cui import i18n


def setup_function() -> None:
    i18n.set_lang(None)  # グローバル状態をリセット


def test_t_returns_ja_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)
    i18n.set_lang(None)
    result = i18n.t("SESSION_NONE")
    assert result == "現在: 記録なし"


def test_t_with_en_lang() -> None:
    i18n.set_lang("en")
    result = i18n.t("SESSION_NONE")
    assert result == "No active session"


def test_t_fallback_to_ja_when_key_missing_in_en(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """en に無いキーは ja にフォールバックする。"""
    from task_recorder_cui.locales import en

    monkeypatch.delattr(en, "ONLY_IN_JA", raising=False)

    from task_recorder_cui.locales import ja

    monkeypatch.setattr(ja, "ONLY_IN_JA", "日本語のみ", raising=False)

    i18n.set_lang("en")
    assert i18n.t("ONLY_IN_JA") == "日本語のみ"


def test_t_returns_key_when_missing_everywhere() -> None:
    """どちらにも無いキーはキー自体を返す (開発時のタイポ検出)。"""
    i18n.set_lang("en")
    assert i18n.t("NONEXISTENT_KEY_XYZ") == "NONEXISTENT_KEY_XYZ"


def test_t_formats_placeholders() -> None:
    i18n.set_lang("en")
    result = i18n.t("ERROR_INVALID_KEY", key="bogus")
    assert result == "Invalid category key: bogus"


def test_current_lang_priority_set_lang_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    i18n.set_lang("ja")
    assert i18n.current_lang() == "ja"


def test_current_lang_priority_env_lang(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.setenv("LANG", "en_GB.UTF-8")
    i18n.set_lang(None)

    def fake_load():
        from task_recorder_cui.config import Config, UIConfig

        return Config(ui=UIConfig(lang=""))  # 空 = 未設定扱い

    monkeypatch.setattr("task_recorder_cui.config.load_config", fake_load)
    assert i18n.current_lang() == "en"


def test_current_lang_lc_all_beats_lang(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LC_ALL", "ja_JP.UTF-8")
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    i18n.set_lang(None)

    def fake_load():
        from task_recorder_cui.config import Config, UIConfig

        return Config(ui=UIConfig(lang=""))

    monkeypatch.setattr("task_recorder_cui.config.load_config", fake_load)
    assert i18n.current_lang() == "ja"


def test_set_lang_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="unsupported lang"):
        i18n.set_lang("fr")


def test_current_lang_default_ja(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)
    i18n.set_lang(None)

    def fake_load():
        from task_recorder_cui.config import Config, UIConfig

        return Config(ui=UIConfig(lang=""))

    monkeypatch.setattr("task_recorder_cui.config.load_config", fake_load)
    assert i18n.current_lang() == "ja"


def test_current_lang_auto_detection_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    i18n.set_lang(None)
    call_count = 0

    def fake_load():
        nonlocal call_count
        from task_recorder_cui.config import Config, UIConfig

        call_count += 1
        return Config(ui=UIConfig(lang=""))  # 空 = 未設定扱い

    monkeypatch.setattr("task_recorder_cui.config.load_config", fake_load)
    assert i18n.current_lang() == "en"
    assert i18n.current_lang() == "en"
    assert i18n.t("SESSION_NONE") == "No active session"
    assert call_count == 1


def test_current_lang_re_detects_when_env_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    i18n.set_lang(None)

    def fake_load():
        from task_recorder_cui.config import Config, UIConfig

        return Config(ui=UIConfig(lang=""))

    monkeypatch.setattr("task_recorder_cui.config.load_config", fake_load)
    assert i18n.current_lang() == "en"
    monkeypatch.setenv("LANG", "ja_JP.UTF-8")
    assert i18n.current_lang() == "ja"


# --- 追加: 未カバー分岐 ---


def test_current_lang_uses_config_lang_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """config.ui.lang に 'en' があれば env を無視して 'en'。"""
    from task_recorder_cui import i18n as i18n_mod

    i18n_mod.set_lang(None)  # set_lang(None) で auto-detect cache もクリア
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.setenv("LANG", "ja_JP.UTF-8")

    def _fake_config_lang() -> str:
        return "en"

    monkeypatch.setattr(i18n_mod, "_config_lang", _fake_config_lang)
    assert i18n_mod.current_lang() == "en"
    i18n_mod.set_lang(None)


def test_config_lang_returns_none_on_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """config モジュールの import が失敗した場合 None を返す (循環 import 回避の保険)。"""
    import builtins

    from task_recorder_cui import i18n as i18n_mod

    real_import = builtins.__import__

    def _fake_import(name: str, *args, **kwargs):
        if name == "task_recorder_cui.config":
            raise ImportError("simulated")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    assert i18n_mod._config_lang() is None


def test_config_lang_returns_none_on_file_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_config が FileNotFoundError を投げた場合 None を返す。"""
    from task_recorder_cui import config as config_mod
    from task_recorder_cui import i18n as i18n_mod

    def _raise() -> None:
        raise FileNotFoundError("no config")

    monkeypatch.setattr(config_mod, "load_config", _raise)
    assert i18n_mod._config_lang() is None
