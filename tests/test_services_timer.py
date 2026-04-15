"""services.timer の時刻パーサのテスト。"""

import pytest

from task_recorder_cui.services.timer import parse_timer_spec


def test_parse_timer_spec_h_and_m() -> None:
    """'2h30m' は 150 分。"""
    assert parse_timer_spec("2h30m") == 150


def test_parse_timer_spec_m_only() -> None:
    assert parse_timer_spec("30m") == 30


def test_parse_timer_spec_h_only() -> None:
    assert parse_timer_spec("2h") == 120


def test_parse_timer_spec_plain_number_is_minutes() -> None:
    """'150' は分単体扱い。"""
    assert parse_timer_spec("150") == 150


def test_parse_timer_spec_150m() -> None:
    assert parse_timer_spec("150m") == 150


def test_parse_timer_spec_rejects_zero() -> None:
    with pytest.raises(ValueError, match="1 分以上"):
        parse_timer_spec("0m")


def test_parse_timer_spec_rejects_negative_hidden() -> None:
    """負の数値は正規表現自体で弾かれる。"""
    with pytest.raises(ValueError, match="不正"):
        parse_timer_spec("-5m")


def test_parse_timer_spec_rejects_empty() -> None:
    with pytest.raises(ValueError, match="不正"):
        parse_timer_spec("")


def test_parse_timer_spec_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="不正"):
        parse_timer_spec("abc")


def test_parse_timer_spec_rejects_whitespace() -> None:
    with pytest.raises(ValueError, match="不正"):
        parse_timer_spec("2h 30m")
