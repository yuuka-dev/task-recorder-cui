"""db.migrate() のテスト。user_version ベースの段階適用を検証する。"""

import sqlite3
from pathlib import Path

from task_recorder_cui.db import connect, initialize, migrate


def _user_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r["name"] for r in rows]


def test_migrate_from_v0_to_v1_adds_timer_columns(tmp_path: Path) -> None:
    """既存 v0 DB に対して migrate を走らせると timer 系カラムが追加され user_version=1 になる。"""
    db_path = tmp_path / "v0.db"
    conn = connect(db_path)
    conn.executescript(
        """
        CREATE TABLE records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_key TEXT NOT NULL,
            description TEXT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            duration_minutes INTEGER
        );
        """
    )
    conn.execute("PRAGMA user_version = 0")
    conn.commit()
    assert _user_version(conn) == 0
    assert "timer_target_at" not in _columns(conn, "records")

    migrate(conn)

    assert _user_version(conn) == 1
    cols = _columns(conn, "records")
    assert "timer_target_at" in cols
    assert "timer_fired_at" in cols
    conn.close()


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    """migrate を 2 回呼んでも user_version は 1 のまま、ALTER は 1 回だけ走る。"""
    db_path = tmp_path / "idem.db"
    conn = connect(db_path)
    initialize(conn)
    first_version = _user_version(conn)

    migrate(conn)

    assert _user_version(conn) == first_version
    conn.close()


def test_migrate_preserves_existing_records(tmp_path: Path) -> None:
    """マイグレーション実行後も既存レコードは読め、新カラムは NULL。"""
    db_path = tmp_path / "preserve.db"
    conn = connect(db_path)
    conn.executescript(
        """
        CREATE TABLE records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_key TEXT NOT NULL,
            description TEXT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            duration_minutes INTEGER
        );
        """
    )
    conn.execute("PRAGMA user_version = 0")
    conn.execute(
        "INSERT INTO records (category_key, description, started_at) VALUES (?, ?, ?)",
        ("dev", "pre-migration", "2026-04-14T12:00:00+00:00"),
    )
    conn.commit()

    migrate(conn)

    row = conn.execute("SELECT * FROM records WHERE description = 'pre-migration'").fetchone()
    assert row is not None
    assert row["timer_target_at"] is None
    assert row["timer_fired_at"] is None
    conn.close()


def test_row_to_record_includes_timer_columns(tmp_path: Path) -> None:
    """migrate 後の records 行から Record dataclass に変換できる (timer カラム込み)。"""
    from task_recorder_cui.repo import row_to_record

    db_path = tmp_path / "row.db"
    conn = connect(db_path)
    initialize(conn)
    conn.execute(
        "INSERT INTO records (category_key, description, started_at, timer_target_at) "
        "VALUES (?, ?, ?, ?)",
        ("dev", "with-timer", "2026-04-14T12:00:00+00:00", "2026-04-14T14:30:00+00:00"),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM records WHERE description = 'with-timer'").fetchone()
    record = row_to_record(row)
    assert record.timer_target_at is not None
    assert record.timer_fired_at is None
    conn.close()
