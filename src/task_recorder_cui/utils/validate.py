"""バリデーションユーティリティ。"""

import re

from task_recorder_cui.i18n import t

_CATEGORY_KEY_PATTERN = re.compile(r"^[a-z0-9_]+$")


def validate_category_key(key: str) -> None:
    """category.key が ASCII英小文字+数字+アンダースコアのみで構成されているか検証する。

    Args:
        key: 検証対象の文字列。

    Raises:
        ValueError: 不正なkeyの場合。メッセージは現在言語 (i18n) で返す。

    """
    if not key:
        raise ValueError(t("VALIDATE_KEY_EMPTY"))
    if not _CATEGORY_KEY_PATTERN.match(key):
        raise ValueError(t("VALIDATE_KEY_INVALID_CHARS", key=key))
