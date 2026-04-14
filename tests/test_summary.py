"""commands/_summary.py のユニットテスト。"""

from datetime import timedelta
from pathlib import Path

from task_recorder_cui.commands._summary import (
    aggregate_period,
    today_local,
)
from task_recorder_cui.db import open_db
from task_recorder_cui.repo import insert_record
from task_recorder_cui.utils.time import now_utc


def test_aggregate_period_空DB(isolated_db: Path) -> None:
    today = today_local()
    with open_db() as conn:
        summary = aggregate_period(conn, today, today)
    assert summary.total_minutes == 0
    assert summary.days == []
    assert summary.per_category_minutes == {}


def test_aggregate_period_単一日複数カテゴリ(isolated_db: Path) -> None:
    today = today_local()
    now = now_utc()
    with open_db() as conn:
        with conn:
            insert_record(
                conn,
                category_key="game",
                description="a",
                started_at=now - timedelta(minutes=60),
                ended_at=now - timedelta(minutes=30),
                duration_minutes=30,
            )
            insert_record(
                conn,
                category_key="study",
                description="b",
                started_at=now - timedelta(minutes=30),
                ended_at=now - timedelta(minutes=10),
                duration_minutes=20,
            )
        summary = aggregate_period(conn, today, today)
    assert summary.total_minutes == 50
    assert summary.per_category_minutes == {"game": 30, "study": 20}
    assert summary.display_names["game"] == "ゲーム"
    assert len(summary.days) == 1


def test_aggregate_period_記録中セッションを計上(isolated_db: Path) -> None:
    today = today_local()
    now = now_utc()
    with open_db() as conn:
        with conn:
            insert_record(
                conn,
                category_key="dev",
                description="実装",
                started_at=now - timedelta(minutes=5),
            )
        summary = aggregate_period(conn, today, today)
    assert summary.active_partial_minutes >= 0
    assert summary.total_minutes == summary.active_partial_minutes
    assert "dev" in summary.per_category_minutes
