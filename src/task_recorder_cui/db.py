"""SQLite接続とマイグレーション。

DBファイルは `~/.local/share/tsk/records.db` に配置する。
環境変数 `TSK_DB_PATH` で上書き可能 (主にテスト用)。
"""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from task_recorder_cui.utils.time import now_utc, to_iso

_DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "tsk" / "records.db"

INITIAL_CATEGORIES: list[tuple[str, str]] = [
    ("game", "ゲーム"),
    ("study", "学習"),
    ("dev", "開発"),
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_key TEXT NOT NULL,
    description TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_minutes INTEGER
);

CREATE INDEX IF NOT EXISTS idx_records_started_at ON records(started_at);
CREATE INDEX IF NOT EXISTS idx_records_category_key ON records(category_key);
"""


def get_db_path() -> Path:
    """DBファイルのパスを返す。

    環境変数 `TSK_DB_PATH` が設定されていればそれを優先する。

    Returns:
        SQLiteファイルのPath。

    """
    env = os.environ.get("TSK_DB_PATH")
    if env:
        return Path(env)
    return _DEFAULT_DB_PATH


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """SQLiteに接続する。親ディレクトリが無ければ作成する。

    Args:
        db_path: DBファイルのパス。省略時は `get_db_path()` の結果を使う。

    Returns:
        `sqlite3.Row` を row_factory に設定済みのConnection。

    """
    path = db_path if db_path is not None else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # 設計方針: FK制約は現状張らない (CLAUDE.md「設計メモ」参照)。
    # 将来FKを追加する場合は conn.execute("PRAGMA foreign_keys = ON") を有効化する。
    return conn


def initialize(conn: sqlite3.Connection) -> None:
    """スキーマを適用し、初回なら初期カテゴリを投入する。

    複数回呼んでも安全 (冪等)。初期データ投入はトランザクション内で行い、
    失敗時は自動ロールバックされる。

    Args:
        conn: 対象のSQLite接続。

    """
    # DDL は executescript が暗黙コミットする (Python標準仕様)。
    conn.executescript(_SCHEMA)
    # 初期データはアトミックに投入する (with conn: BEGIN / COMMIT / ROLLBACK)。
    with conn:
        existing = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if existing == 0:
            now_iso = to_iso(now_utc())
            conn.executemany(
                "INSERT INTO categories (key, display_name, created_at) VALUES (?, ?, ?)",
                [(key, name, now_iso) for key, name in INITIAL_CATEGORIES],
            )


@contextmanager
def open_db() -> Iterator[sqlite3.Connection]:
    """DBに接続してスキーマを適用し、終了時にクローズするコンテキストマネージャ。

    書き込みを行う場合は呼び出し側で `with conn:` を張りトランザクション管理すること。

    Yields:
        初期化済みのSQLite Connection。

    """
    conn = connect()
    try:
        initialize(conn)
        yield conn
    finally:
        conn.close()
