"""tsk today コマンドのテスト。"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from task_recorder_cui.cli import main
from task_recorder_cui.db import open_db
from task_recorder_cui.repo import insert_record


def _local_noon() -> datetime:
    """テスト用: 今日のローカル正午 (tz付き)。日付境界のテスト不安定を防ぐ。"""
    return datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)


def test_記録なしでも正常終了(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["today"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "記録なし" in out


def test_addした記録がtimelineとsummaryに出る(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    noon = _local_noon()
    with open_db() as conn, conn:
        insert_record(
            conn,
            category_key="study",
            description="ABC",
            started_at=noon - timedelta(minutes=90),
            ended_at=noon - timedelta(minutes=45),
            duration_minutes=45,
        )
        insert_record(
            conn,
            category_key="game",
            description="HOI4",
            started_at=noon - timedelta(minutes=45),
            ended_at=noon - timedelta(minutes=15),
            duration_minutes=30,
        )
    capsys.readouterr()

    exit_code = main(["today"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "学習" in out
    assert "ゲーム" in out
    assert "ABC" in out
    assert "HOI4" in out
    assert "合計" in out


def test_記録中セッションは記録中マークで表示(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["start", "dev", "実装中"])
    capsys.readouterr()

    exit_code = main(["today"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "記録中" in out
    assert "実装中" in out


def test_today_english_no_records(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from task_recorder_cui.i18n import set_lang

    try:
        rc = main(["--lang", "en", "today"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No records" in out
    finally:
        set_lang(None)
