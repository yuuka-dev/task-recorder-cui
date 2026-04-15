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
