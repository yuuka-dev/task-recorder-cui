"""tsk start: 新しい時間記録セッションを開始する。"""

import sqlite3

from rich.markup import escape

from task_recorder_cui.db import open_db
from task_recorder_cui.io import print_error, print_line, print_warning
from task_recorder_cui.models import Record
from task_recorder_cui.repo import find_active_record, find_category, insert_record
from task_recorder_cui.utils.time import now_utc


def run(category_key: str, description: str | None) -> int:
    """指定カテゴリでセッションを開始する。

    既に記録中のセッションがある、またはカテゴリキーが存在しない場合は
    エラーメッセージを表示して終了コード1で返す。時刻はUTCで保存する。

    Args:
        category_key: 対象カテゴリのkey。
        description: 活動内容 (任意)。

    Returns:
        0: 開始成功 / 1: 既に記録中、または未登録カテゴリ。

    """
    with open_db() as conn:
        category = find_category(conn, category_key)
        if category is None:
            print_error(
                f"カテゴリ '{category_key}' が存在しません。`tsk cat list` で一覧を確認してください"
            )
            return 1
        active = find_active_record(conn)
        if active is not None:
            _print_already_active(conn, active)
            return 1
        started_at = now_utc()
        with conn:
            insert_record(
                conn,
                category_key=category_key,
                description=description,
                started_at=started_at,
            )
        display_name = category.display_name

    local_hm = started_at.astimezone().strftime("%H:%M")
    detail = f" {escape(description)}" if description else ""
    print_line(f"開始: [{escape(display_name)}]{detail} ({local_hm}-)")
    return 0


def _print_already_active(conn: sqlite3.Connection, active: Record) -> None:
    """記録中セッションがあることを警告表示する。"""
    category = find_category(conn, active.category_key)
    display = category.display_name if category else active.category_key
    started_local = active.started_at.astimezone().strftime("%H:%M")
    detail = f" {active.description}" if active.description else ""
    print_warning(f"既に記録中のセッションがあります: [{display}]{detail} ({started_local}-)")
    print_line("先に `tsk stop` で停止してください")
