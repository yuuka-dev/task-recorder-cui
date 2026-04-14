"""repo.list_recent_records の単体テスト。"""

from datetime import UTC, datetime, timedelta

from task_recorder_cui.db import open_db
from task_recorder_cui.repo import (
    insert_record,
    list_recent_records,
    update_record_end,
)


def _add_completed(
    conn, key: str, started_at: datetime, ended_at: datetime, desc: str | None
) -> None:
    """テスト補助: 完了済みレコードを 1 件作る。"""
    rec_id = insert_record(conn, category_key=key, description=desc, started_at=started_at)
    duration = int((ended_at - started_at).total_seconds() // 60)
    update_record_end(conn, rec_id, ended_at=ended_at, duration_minutes=duration)


def test_list_recent_records_returns_completed_in_desc_order(isolated_db) -> None:
    base = datetime(2026, 4, 15, 9, 0, 0, tzinfo=UTC)
    with open_db() as conn:
        with conn:
            _add_completed(conn, "dev", base, base + timedelta(minutes=30), "A")
            _add_completed(conn, "game", base + timedelta(hours=1), base + timedelta(hours=2), "B")
            _add_completed(conn, "study", base + timedelta(hours=3), base + timedelta(hours=4), "C")

        records = list_recent_records(conn, 10)

    assert [r.description for r in records] == ["C", "B", "A"]


def test_list_recent_records_excludes_active_sessions(isolated_db) -> None:
    base = datetime(2026, 4, 15, 9, 0, 0, tzinfo=UTC)
    with open_db() as conn:
        with conn:
            _add_completed(conn, "dev", base, base + timedelta(minutes=30), "完了済み")
            insert_record(
                conn,
                category_key="game",
                description="記録中",
                started_at=base + timedelta(hours=2),
            )

        records = list_recent_records(conn, 10)

    assert [r.description for r in records] == ["完了済み"]


def test_list_recent_records_respects_limit(isolated_db) -> None:
    base = datetime(2026, 4, 15, 9, 0, 0, tzinfo=UTC)
    with open_db() as conn:
        with conn:
            for i in range(8):
                started = base + timedelta(hours=i)
                ended = started + timedelta(minutes=15)
                _add_completed(conn, "dev", started, ended, f"#{i}")

        records = list_recent_records(conn, 3)

    assert len(records) == 3
    assert [r.description for r in records] == ["#7", "#6", "#5"]


def test_list_recent_records_empty(isolated_db) -> None:
    with open_db() as conn:
        records = list_recent_records(conn, 5)
    assert records == []
