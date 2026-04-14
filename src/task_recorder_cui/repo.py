"""SQLite への基本的なデータアクセスレイヤ。

`commands/` 配下から共通で使う CRUD ヘルパと `sqlite3.Row` → dataclass 変換を
まとめる。各関数は呼び出し側で `with conn:` などのトランザクション管理を行う
ことを前提とする (読み取り関数は tx 不要)。
"""

import sqlite3
from datetime import datetime

from task_recorder_cui.models import Category, Record
from task_recorder_cui.utils.time import from_iso, to_iso


def row_to_category(row: sqlite3.Row) -> Category:
    """DB行を Category に変換する。"""
    return Category(
        id=row["id"],
        key=row["key"],
        display_name=row["display_name"],
        created_at=from_iso(row["created_at"]),
        archived=bool(row["archived"]),
    )


def row_to_record(row: sqlite3.Row) -> Record:
    """DB行を Record に変換する。記録中セッション (ended_at IS NULL) にも対応。"""
    ended_at_raw = row["ended_at"]
    return Record(
        id=row["id"],
        category_key=row["category_key"],
        description=row["description"],
        started_at=from_iso(row["started_at"]),
        ended_at=from_iso(ended_at_raw) if ended_at_raw else None,
        duration_minutes=row["duration_minutes"],
    )


def find_category(conn: sqlite3.Connection, key: str) -> Category | None:
    """指定 key のカテゴリを返す。

    Args:
        conn: DB接続。
        key: 検索するカテゴリキー。

    Returns:
        該当カテゴリ、無ければ None。archived 状態は問わない。

    """
    row = conn.execute("SELECT * FROM categories WHERE key = ?", (key,)).fetchone()
    return row_to_category(row) if row else None


def find_active_record(conn: sqlite3.Connection) -> Record | None:
    """記録中 (ended_at IS NULL) のセッションを返す。

    仕様上 active は高々1件だが、防御的に最新のものを返す。

    Args:
        conn: DB接続。

    Returns:
        記録中セッション、無ければ None。

    """
    row = conn.execute(
        "SELECT * FROM records WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    return row_to_record(row) if row else None


def insert_record(
    conn: sqlite3.Connection,
    *,
    category_key: str,
    description: str | None,
    started_at: datetime,
    ended_at: datetime | None = None,
    duration_minutes: int | None = None,
) -> int:
    """records に1件挿入し、生成された id を返す。

    Args:
        conn: DB接続。
        category_key: 参照するカテゴリキー。
        description: 活動内容 (任意)。
        started_at: 開始時刻 (tz付き)。
        ended_at: 終了時刻 (tz付き)。start中の場合は None。
        duration_minutes: 記録時間の分数。start中の場合は None。

    Returns:
        挿入された行の id。

    Raises:
        RuntimeError: lastrowid が取得できなかった場合 (通常起きない)。

    """
    cur = conn.execute(
        "INSERT INTO records (category_key, description, started_at, ended_at, duration_minutes) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            category_key,
            description,
            to_iso(started_at),
            to_iso(ended_at) if ended_at else None,
            duration_minutes,
        ),
    )
    if cur.lastrowid is None:
        raise RuntimeError("INSERT が lastrowid を返しませんでした")
    return cur.lastrowid


def update_record_end(
    conn: sqlite3.Connection,
    record_id: int,
    *,
    ended_at: datetime,
    duration_minutes: int,
) -> None:
    """記録中のレコードに終了時刻と分数を書き込む。

    Args:
        conn: DB接続。
        record_id: 対象レコードの id。
        ended_at: 終了時刻 (tz付き)。
        duration_minutes: 計算済みの分数。

    """
    conn.execute(
        "UPDATE records SET ended_at = ?, duration_minutes = ? WHERE id = ?",
        (to_iso(ended_at), duration_minutes, record_id),
    )
