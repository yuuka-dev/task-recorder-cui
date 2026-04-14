"""バリデーションユーティリティ。"""

import re

_CATEGORY_KEY_PATTERN = re.compile(r"^[a-z0-9_]+$")


def validate_category_key(key: str) -> None:
    """category.key が ASCII英小文字+数字+アンダースコアのみで構成されているか検証する。

    Args:
        key: 検証対象の文字列。

    Raises:
        ValueError: 不正なkeyの場合。
    """
    if not _CATEGORY_KEY_PATTERN.match(key):
        raise ValueError(
            f"category key must match [a-z0-9_]+ (ASCII lowercase/digit/underscore): {key!r}"
        )
