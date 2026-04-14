"""db.py のテスト。"""

from pathlib import Path

from task_recorder_cui.db import INITIAL_CATEGORIES, connect, initialize


def test_initializeでテーブルが作成される(tmp_path: Path) -> None:
    db_path = tmp_path / "records.db"
    with connect(db_path) as conn:
        initialize(conn)
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
    assert {"categories", "records"} <= tables


def test_initializeで初期カテゴリが投入される(tmp_path: Path) -> None:
    db_path = tmp_path / "records.db"
    with connect(db_path) as conn:
        initialize(conn)
        rows = conn.execute("SELECT key, display_name FROM categories ORDER BY id").fetchall()
    keys = [r["key"] for r in rows]
    assert keys == [k for k, _ in INITIAL_CATEGORIES]


def test_initializeは冪等(tmp_path: Path) -> None:
    db_path = tmp_path / "records.db"
    with connect(db_path) as conn:
        initialize(conn)
        initialize(conn)
        count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    assert count == len(INITIAL_CATEGORIES)


def test_connectで親ディレクトリが作られる(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "dir" / "records.db"
    with connect(db_path) as conn:
        initialize(conn)
    assert db_path.exists()
