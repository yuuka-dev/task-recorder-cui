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


def test_archivedカテゴリはexit1(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["cat", "remove", "game"])
    capsys.readouterr()
    exit_code = main(["start", "game", "archived試行"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "アーカイブ済み" in err
    assert _fetch_records(isolated_db) == []


def test_start_with_timer_sets_target(isolated_db, monkeypatch: pytest.MonkeyPatch) -> None:
    """start --timer 30m で records に timer_target_at が書き込まれる。"""
    from task_recorder_cui.commands import start as start_cmd
    from task_recorder_cui.db import open_db
    from task_recorder_cui.repo import find_active_record

    calls: list[int] = []
    monkeypatch.setattr("task_recorder_cui.commands.start.spawn_daemon", lambda r: calls.append(r))

    rc = start_cmd.run("dev", "with-timer", timer_spec="30m")
    assert rc == 0
    with open_db() as conn:
        rec = find_active_record(conn)
        assert rec is not None
        assert rec.timer_target_at is not None
    assert len(calls) == 1


def test_start_without_timer_does_not_spawn(isolated_db, monkeypatch: pytest.MonkeyPatch) -> None:
    from task_recorder_cui.commands import start as start_cmd

    calls: list[int] = []
    monkeypatch.setattr("task_recorder_cui.commands.start.spawn_daemon", lambda r: calls.append(r))

    rc = start_cmd.run("dev", "no-timer", timer_spec=None)
    assert rc == 0
    assert calls == []


def test_start_with_invalid_timer_errors_before_insert(
    isolated_db, capsys: pytest.CaptureFixture[str]
) -> None:
    """invalid --timer なら start 自体を失敗させ、レコードを書かない。"""
    from task_recorder_cui.commands import start as start_cmd
    from task_recorder_cui.db import open_db

    rc = start_cmd.run("dev", "bad", timer_spec="nope")
    assert rc == 1
    err = capsys.readouterr().err
    assert "不正" in err
    with open_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        assert count == 0
