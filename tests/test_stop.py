"""tsk stop コマンドのテスト。"""

import sqlite3
from pathlib import Path

import pytest

from task_recorder_cui.cli import main


def test_stopで終了時刻とduration_minutesが入る(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["start", "game", "HOI4"])
    capsys.readouterr()

    exit_code = main(["stop"])
    assert exit_code == 0
    assert "停止" in capsys.readouterr().out

    conn = sqlite3.connect(isolated_db)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM records").fetchone()
    finally:
        conn.close()
    assert row["ended_at"] is not None
    assert row["duration_minutes"] is not None
    assert row["duration_minutes"] >= 0


def test_記録中セッションが無ければexit1(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["stop"])
    assert exit_code == 1
    assert "記録中" in capsys.readouterr().out


def test_stop_clears_active_timer(isolated_db) -> None:
    """stop するとタイマーも自動的に clear される (daemon は自殺方式で気づく)。"""
    from datetime import timedelta

    from task_recorder_cui.commands import stop as stop_cmd
    from task_recorder_cui.db import open_db
    from task_recorder_cui.repo import insert_record, set_timer_target
    from task_recorder_cui.utils.time import now_utc

    with open_db() as conn, conn:
        started = now_utc()
        rec_id = insert_record(
            conn, category_key="dev", description="x", started_at=started
        )
        set_timer_target(conn, rec_id, target_at=started + timedelta(minutes=30))

    rc = stop_cmd.run()
    assert rc == 0
    with open_db() as conn:
        row = conn.execute(
            "SELECT timer_target_at FROM records WHERE id = ?", (rec_id,)
        ).fetchone()
        assert row["timer_target_at"] is None
