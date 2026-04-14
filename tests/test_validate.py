"""utils/validate.py のテスト。"""

import pytest

from task_recorder_cui.utils.validate import validate_category_key


class TestValidateCategoryKey:
    """category key のバリデーション。"""

    @pytest.mark.parametrize("key", ["game", "study", "dev", "a1", "a_b_c", "z9_"])
    def test_有効なkeyは例外を投げない(self, key: str) -> None:
        validate_category_key(key)

    @pytest.mark.parametrize(
        "key",
        [
            "",
            "Game",  # 大文字
            "ゲーム",  # 日本語
            "a-b",  # ハイフン
            "a b",  # スペース
            "a.b",  # ドット
        ],
    )
    def test_無効なkeyはValueError(self, key: str) -> None:
        with pytest.raises(ValueError):
            validate_category_key(key)
