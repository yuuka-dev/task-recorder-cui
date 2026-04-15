"""repo のタイマー操作 API のテスト。"""

from datetime import timedelta

from task_recorder_cui.db import open_db
from task_recorder_cui.repo import (
    clear_timer_target,
    find_active_record,
    insert_record,
    mark_timer_fired,
    set_timer_target,
)
from task_recorder_cui.utils.time import now_utc


def test_set_timer_target_writes_iso8601(isolated_db) -> None:
    """set_timer_target で timer_target_at に UTC ISO8601 が書き込まれる。"""
    with open_db() as conn:
        started = now_utc()
        rec_id = insert_record(conn, category_key="dev", description="x", started_at=started)
        target = started + timedelta(minutes=30)
        with conn:
            set_timer_target(conn, rec_id, target_at=target)

        record = find_active_record(conn)
        assert record is not None
        assert record.id == rec_id
        assert record.timer_target_at is not None
        assert abs((record.timer_target_at - target).total_seconds()) < 1


def test_clear_timer_target_sets_null(isolated_db) -> None:
    """clear_timer_target で timer_target_at が NULL に戻る。"""
    with open_db() as conn:
        started = now_utc()
        rec_id = insert_record(conn, category_key="dev", description="x", started_at=started)
        target = started + timedelta(minutes=30)
        with conn:
            set_timer_target(conn, rec_id, target_at=target)
            clear_timer_target(conn, rec_id)

        record = find_active_record(conn)
        assert record is not None
        assert record.timer_target_at is None


def test_mark_timer_fired_sets_fired_at(isolated_db) -> None:
    """mark_timer_fired で timer_fired_at が set される (target は残る)。"""
    with open_db() as conn:
        started = now_utc()
        rec_id = insert_record(conn, category_key="dev", description="x", started_at=started)
        target = started + timedelta(minutes=30)
        fired = started + timedelta(minutes=30, seconds=2)
        with conn:
            set_timer_target(conn, rec_id, target_at=target)
            mark_timer_fired(conn, rec_id, fired_at=fired)

        record = find_active_record(conn)
        assert record is not None
        assert record.timer_fired_at is not None
        assert record.timer_target_at is not None
