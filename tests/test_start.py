"""tsk start コマンドのテスト。"""

import sqlite3
from pathlib import Path

import pytest

from task_recorder_cui.cli import main


def _fetch_records(db_path: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM records").fetchall()
    finally:
        conn.close()


def test_startで新規レコードが作成される(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["start", "game", "HOI4"])
    assert exit_code == 0
    assert "開始" in capsys.readouterr().out

    rows = _fetch_records(isolated_db)
    assert len(rows) == 1
    assert rows[0]["category_key"] == "game"
    assert rows[0]["description"] == "HOI4"
    assert rows[0]["ended_at"] is None
    assert rows[0]["duration_minutes"] is None


def test_description省略でもstartできる(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["start", "dev"])
    assert exit_code == 0
    rows = _fetch_records(isolated_db)
    assert rows[0]["description"] is None


def test_未登録カテゴリはexit1(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["start", "unknown_key"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "unknown_key" in err
    assert _fetch_records(isolated_db) == []


def test_既に記録中なら警告してexit1(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["start", "game", "既存"])
    capsys.readouterr()
    exit_code = main(["start", "dev", "別"])
    assert exit_code == 1
    assert "既に記録中" in capsys.readouterr().err
    rows = _fetch_records(isolated_db)
    assert len(rows) == 1  # 新しいレコードは作られない
