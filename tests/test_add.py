"""tsk add コマンドのテスト。"""

import sqlite3
from pathlib import Path

import pytest

from task_recorder_cui.cli import main


def test_addでレコードが作成される(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["add", "study", "45", "ABC B問題"])
    assert exit_code == 0
    assert "追加" in capsys.readouterr().out

    conn = sqlite3.connect(isolated_db)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM records").fetchone()
    finally:
        conn.close()
    assert row["category_key"] == "study"
    assert row["description"] == "ABC B問題"
    assert row["duration_minutes"] == 45
    assert row["started_at"] is not None
    assert row["ended_at"] is not None


def test_負のminutesはexit1(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["add", "study", "-5", "bad"])
    assert exit_code == 1
    assert "1以上" in capsys.readouterr().err


def test_未登録カテゴリはexit1(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["add", "unknown_cat", "30"])
    assert exit_code == 1
    assert "unknown_cat" in capsys.readouterr().err
