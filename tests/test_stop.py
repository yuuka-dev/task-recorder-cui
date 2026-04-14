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
