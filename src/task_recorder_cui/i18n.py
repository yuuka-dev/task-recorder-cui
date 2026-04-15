"""i18n ヘルパ。

`t(key, **fmt)` が唯一の公開 API。言語選択は優先順位:
  1. set_lang(...) での明示指定 (CLI フラグ経由)
  2. config.ui.lang
  3. LC_ALL / LANG 環境変数
  4. 'ja' (デフォルト)
未対応言語 (fr など) はサイレントに 'ja' フォールバック。
"""

import os
from typing import Any

from task_recorder_cui.locales import en, ja

_LOCALES: dict[str, object] = {"ja": ja, "en": en}
_current_lang: str | None = None


def set_lang(lang: str | None) -> None:
    """明示的な言語指定。None に戻すと自動判定に戻る。

    Args:
        lang: 'ja' / 'en' / None のいずれか

    Raises:
        ValueError: サポート外の言語コードを渡した場合

    """
    global _current_lang
    if lang is not None and lang not in _LOCALES:
        raise ValueError(f"unsupported lang: {lang}")
    _current_lang = lang


def current_lang() -> str:
    """現在の有効な言語 ('ja' or 'en') を返す。"""
    if _current_lang is not None:
        return _current_lang
    cfg_lang = _config_lang()
    if cfg_lang in _LOCALES:
        return cfg_lang
    for env_var in ("LC_ALL", "LANG"):
        env = os.environ.get(env_var, "")
        prefix = env.split("_", 1)[0].lower()
        if prefix in _LOCALES:
            return prefix
    return "ja"


def _config_lang() -> str | None:
    """設定ファイルから言語を読む (循環 import 回避のため遅延 import)。"""
    try:
        from task_recorder_cui.config import load_config
    except ImportError:
        return None
    try:
        return load_config().ui.lang
    except Exception:
        return None


def t(key: str, /, **fmt: Any) -> str:
    """メッセージを現在言語で解決し、{placeholder} を埋める。

    Args:
        key: locales モジュールの定数名 (positional-only: **fmt に ``key`` を
            含めてもキー解決用引数と衝突しないようにするため)
        **fmt: テンプレート内 ``{name}`` に埋め込む値

    Returns:
        解決済み文字列。言語モジュールに該当キーが無ければ ja にフォールバック、
        ja にも無ければ key 自体を返す (開発時のタイポを可視化)。

    """
    lang = current_lang()
    mod = _LOCALES.get(lang, ja)
    template = getattr(mod, key, None)
    if template is None and mod is not ja:
        template = getattr(ja, key, None)
    if template is None:
        return key
    return template.format(**fmt)
