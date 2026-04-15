"""SQLite への基本的なデータアクセスレイヤ。

`commands/` 配下から共通で使う CRUD ヘルパと `sqlite3.Row` → dataclass 変換を
まとめる。各関数は呼び出し側で `with conn:` などのトランザクション管理を行う
ことを前提とする (読み取り関数は tx 不要)。
"""

import sqlite3
from datetime import datetime

from task_recorder_cui.models import Category, Record
from task_recorder_cui.utils.time import from_iso, now_utc, to_iso


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
    """DB行を Record に変換する。記録中セッション (ended_at IS NULL) にも対応。

    timer カラムは v0 DB との互換のため存在チェックしてから読む。
    """
    ended_at_raw = row["ended_at"]
    keys = row.keys()
    target_raw = row["timer_target_at"] if "timer_target_at" in keys else None
    fired_raw = row["timer_fired_at"] if "timer_fired_at" in keys else None
    return Record(
        id=row["id"],
        category_key=row["category_key"],
        description=row["description"],
        started_at=from_iso(row["started_at"]),
        ended_at=from_iso(ended_at_raw) if ended_at_raw else None,
        duration_minutes=row["duration_minutes"],
        timer_target_at=from_iso(target_raw) if target_raw else None,
        timer_fired_at=from_iso(fired_raw) if fired_raw else None,
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


def list_all_categories(
    conn: sqlite3.Connection,
    *,
    active_only: bool = False,
    archived_only: bool = False,
) -> list[Category]:
    """カテゴリ一覧を返す。

    Args:
        conn: DB接続。
        active_only: True なら archived=0 のみ。
        archived_only: True なら archived=1 のみ。
        両方 False なら全件 (archived 順 → id 順でソート)。

    Returns:
        Category のリスト。

    Raises:
        ValueError: active_only と archived_only が同時に True の場合。

    """
    if active_only and archived_only:
        raise ValueError("active_only と archived_only を同時に True にはできません")
    if active_only:
        rows = conn.execute("SELECT * FROM categories WHERE archived = 0 ORDER BY id").fetchall()
    elif archived_only:
        rows = conn.execute("SELECT * FROM categories WHERE archived = 1 ORDER BY id").fetchall()
    else:
        rows = conn.execute("SELECT * FROM categories ORDER BY archived, id").fetchall()
    return [row_to_category(r) for r in rows]


def insert_category(conn: sqlite3.Connection, key: str, display_name: str) -> int:
    """カテゴリを1件挿入する。created_at には現在UTCを入れる。

    Args:
        conn: DB接続。
        key: 新しいカテゴリキー。
        display_name: 表示名。

    Returns:
        挿入された行の id。

    Raises:
        sqlite3.IntegrityError: key UNIQUE 制約違反時。

    """
    cur = conn.execute(
        "INSERT INTO categories (key, display_name, created_at) VALUES (?, ?, ?)",
        (key, display_name, to_iso(now_utc())),
    )
    if cur.lastrowid is None:  # pragma: no cover  # sqlite3 の実装上 INSERT 成功時は必ず返る
        raise RuntimeError("INSERT が lastrowid を返しませんでした")
    return cur.lastrowid


def update_category_archived(conn: sqlite3.Connection, key: str, *, archived: bool) -> int:
    """カテゴリの archived フラグを更新する。

    Args:
        conn: DB接続。
        key: 対象カテゴリキー。
        archived: 新しい archived 値。

    Returns:
        更新された行数 (0 なら key 未存在)。

    """
    cur = conn.execute(
        "UPDATE categories SET archived = ? WHERE key = ?",
        (1 if archived else 0, key),
    )
    return cur.rowcount


def update_category_display_name(conn: sqlite3.Connection, key: str, new_display_name: str) -> int:
    """カテゴリの display_name を更新する (key は不変)。

    Args:
        conn: DB接続。
        key: 対象カテゴリキー。
        new_display_name: 新しい表示名。

    Returns:
        更新された行数 (0 なら key 未存在)。

    """
    cur = conn.execute(
        "UPDATE categories SET display_name = ? WHERE key = ?",
        (new_display_name, key),
    )
    return cur.rowcount


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
    if cur.lastrowid is None:  # pragma: no cover  # sqlite3 の実装上 INSERT 成功時は必ず返る
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


def set_timer_target(conn: sqlite3.Connection, record_id: int, *, target_at: datetime) -> None:
    """レコードにタイマー目標時刻を設定する。

    Args:
        conn: DB接続。
        record_id: 対象レコードの id。
        target_at: タイマー発火予定時刻 (tz付き)。

    """
    conn.execute(
        "UPDATE records SET timer_target_at = ? WHERE id = ?",
        (to_iso(target_at), record_id),
    )


def clear_timer_target(conn: sqlite3.Connection, record_id: int) -> None:
    """レコードのタイマー目標時刻を NULL に戻す。

    Args:
        conn: DB接続。
        record_id: 対象レコードの id。

    """
    conn.execute(
        "UPDATE records SET timer_target_at = NULL WHERE id = ?",
        (record_id,),
    )


def mark_timer_fired(conn: sqlite3.Connection, record_id: int, *, fired_at: datetime) -> None:
    """レコードのタイマー発火時刻を記録する。target_at はそのまま。

    Args:
        conn: DB接続。
        record_id: 対象レコードの id。
        fired_at: 発火時刻 (tz付き)。

    """
    conn.execute(
        "UPDATE records SET timer_fired_at = ? WHERE id = ?",
        (to_iso(fired_at), record_id),
    )


def list_recent_records(conn: sqlite3.Connection, limit: int) -> list[Record]:
    """完了済みレコードを新しい順に最大 limit 件返す。

    記録中セッション (`ended_at IS NULL`) は除外する。menu のヘッダ「直近」表示
    用途を想定。

    **不変条件**: 戻り値の各 Record の `ended_at` は必ず not None。

    Args:
        conn: DB接続。
        limit: 取得件数の上限 (正の整数を想定、0 以下なら空リスト)。

    Returns:
        新しい順 (started_at DESC) の Record リスト。

    """
    if limit <= 0:
        return []
    rows = conn.execute(
        "SELECT * FROM records WHERE ended_at IS NOT NULL ORDER BY started_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [row_to_record(r) for r in rows]
