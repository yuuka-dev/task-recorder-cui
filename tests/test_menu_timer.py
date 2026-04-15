"""メニューからタイマー設定して start する経路のテスト (純粋関数部のみ)。"""

from task_recorder_cui.menu import _prompt_to_start_params


def test_prompt_to_start_params_with_timer() -> None:
    """フォーム結果 dict から start 引数 3 点タプルに変換する。"""
    form = {"category": "dev", "description": "obat", "timer": "30m"}
    cat, desc, timer = _prompt_to_start_params(form)
    assert cat == "dev"
    assert desc == "obat"
    assert timer == "30m"


def test_prompt_to_start_params_empty_timer() -> None:
    form = {"category": "dev", "description": "obat", "timer": ""}
    cat, desc, timer = _prompt_to_start_params(form)
    assert timer is None


def test_prompt_to_start_params_whitespace_desc() -> None:
    form = {"category": "dev", "description": "   ", "timer": ""}
    cat, desc, timer = _prompt_to_start_params(form)
    assert desc is None
