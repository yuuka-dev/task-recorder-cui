"""locales/ja.py と locales/en.py のキー集合が一致することを保証する。

片方に追加し忘れると CI で落ちる。
"""

import inspect

from task_recorder_cui.locales import en, ja


def _public_string_constants(module: object) -> set[str]:
    """モジュールから大文字スタートの str 定数名を抽出する。"""
    return {
        name
        for name, value in inspect.getmembers(module)
        if name[:1].isupper() and isinstance(value, str)
    }


def test_ja_en_keys_match() -> None:
    ja_keys = _public_string_constants(ja)
    en_keys = _public_string_constants(en)
    missing_in_en = ja_keys - en_keys
    missing_in_ja = en_keys - ja_keys
    assert not missing_in_en, f"en に無いキー: {sorted(missing_in_en)}"
    assert not missing_in_ja, f"ja に無いキー: {sorted(missing_in_ja)}"


def test_all_keys_have_nonempty_values() -> None:
    for module in (ja, en):
        for name in _public_string_constants(module):
            value = getattr(module, name)
            assert value, f"{module.__name__}.{name} が空文字"
