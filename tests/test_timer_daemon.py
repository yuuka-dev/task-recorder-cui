"""タイマー daemon のループ単体テスト (subprocess は起こさない)。"""

from datetime import timedelta

import pytest

from task_recorder_cui.db import open_db
from task_recorder_cui.repo import (
    insert_record,
    set_timer_target,
)
from task_recorder_cui.services.timer import run_daemon_loop
from task_recorder_cui.utils.time import now_utc


@pytest.fixture()
def make_record(isolated_db):
    def _f(target_offset_minutes: int):
        with open_db() as conn:
            started = now_utc()
            rec_id = insert_record(conn, category_key="dev", description="t", started_at=started)
            with conn:
                set_timer_target(
                    conn,
                    rec_id,
                    target_at=started + timedelta(minutes=target_offset_minutes),
                )
            return rec_id

    return _f


def test_daemon_self_kills_when_target_is_null(isolated_db) -> None:
    """target が NULL の状態で開始したら即 exit する。"""
    with open_db() as conn:
        rec_id = insert_record(
            conn, category_key="dev", description="no-timer", started_at=now_utc()
        )

    fired: list[int] = []
    rc = run_daemon_loop(
        rec_id,
        sleep_fn=lambda _s: None,
        fire_fn=lambda r: fired.append(r.id),
        max_iterations=3,
    )
    assert rc == 0
    assert fired == []


def test_daemon_fires_when_target_passed(make_record) -> None:
    """target が過去なら即 fire_fn が呼ばれて終了。"""
    rec_id = make_record(target_offset_minutes=-1)
    fired: list[int] = []

    rc = run_daemon_loop(
        rec_id,
        sleep_fn=lambda _s: None,
        fire_fn=lambda r: fired.append(r.id),
        max_iterations=5,
    )
    assert rc == 0
    assert fired == [rec_id]


def test_daemon_waits_for_future_target(make_record, monkeypatch: pytest.MonkeyPatch) -> None:
    """target が未来なら sleep し続け、時刻到来で fire する。"""
    rec_id = make_record(target_offset_minutes=60)

    from task_recorder_cui.services import timer as timer_mod

    base = now_utc()
    times = [base, base, base + timedelta(minutes=61)]
    idx = [0]

    def fake_now():
        i = min(idx[0], len(times) - 1)
        idx[0] += 1
        return times[i]

    monkeypatch.setattr(timer_mod, "now_utc", fake_now)
    fired: list[int] = []
    rc = run_daemon_loop(
        rec_id,
        sleep_fn=lambda _s: None,
        fire_fn=lambda r: fired.append(r.id),
        max_iterations=5,
    )
    assert rc == 0
    assert fired == [rec_id]


def test_daemon_stops_if_record_gone(make_record) -> None:
    """レコード自体が削除されてたら fire せず exit。"""
    rec_id = make_record(target_offset_minutes=30)
    with open_db() as conn, conn:
        conn.execute("DELETE FROM records WHERE id = ?", (rec_id,))

    fired: list[int] = []
    rc = run_daemon_loop(
        rec_id,
        sleep_fn=lambda _s: None,
        fire_fn=lambda r: fired.append(r.id),
        max_iterations=3,
    )
    assert rc == 0
    assert fired == []


def test_daemon_stops_if_already_fired(make_record) -> None:
    """既に fired_at が入ってたら再発火しない。"""
    from task_recorder_cui.repo import mark_timer_fired

    rec_id = make_record(target_offset_minutes=-1)
    with open_db() as conn, conn:
        mark_timer_fired(conn, rec_id, fired_at=now_utc())

    fired: list[int] = []
    rc = run_daemon_loop(
        rec_id,
        sleep_fn=lambda _s: None,
        fire_fn=lambda r: fired.append(r.id),
        max_iterations=3,
    )
    assert rc == 0
    assert fired == []
