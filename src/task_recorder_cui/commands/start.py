"""tsk start: 新しい時間記録セッションを開始する。"""

import sqlite3
from datetime import timedelta

from rich.markup import escape

from task_recorder_cui.db import open_db
from task_recorder_cui.i18n import t
from task_recorder_cui.io import print_error, print_line, print_warning
from task_recorder_cui.models import Record
from task_recorder_cui.repo import (
    find_active_record,
    find_category,
    insert_record,
    set_timer_target,
)
from task_recorder_cui.services.timer import parse_timer_spec, spawn_daemon
from task_recorder_cui.utils.time import format_duration, now_utc


def run(
    category_key: str,
    description: str | None,
    *,
    timer_spec: str | None = None,
) -> int:
    """指定カテゴリでセッションを開始する。

    Args:
        category_key: 対象カテゴリのkey。
        description: 活動内容 (任意)。
        timer_spec: '2h30m' 形式のタイマー指定 (任意)。設定時はタイマー daemon
            を起動する。書式不正の場合はレコードを書かずエラー終了する。

    Returns:
        0: 開始成功 / 1: 既に記録中、未登録カテゴリ、タイマー書式不正。

    """
    timer_minutes: int | None = None
    if timer_spec is not None:
        try:
            timer_minutes = parse_timer_spec(timer_spec)
        except ValueError as e:
            print_error(str(e))
            return 1

    with open_db() as conn:
        category = find_category(conn, category_key)
        if category is None:
            print_error(t("START_CATEGORY_NOT_FOUND", key=category_key))
            return 1
        if category.archived:
            print_error(t("START_CATEGORY_ARCHIVED", key=category_key))
            return 1
        active = find_active_record(conn)
        if active is not None:
            _print_already_active(conn, active)
            return 1
        started_at = now_utc()
        with conn:
            rec_id = insert_record(
                conn,
                category_key=category_key,
                description=description,
                started_at=started_at,
            )
            if timer_minutes is not None:
                target = started_at + timedelta(minutes=timer_minutes)
                set_timer_target(conn, rec_id, target_at=target)
        display_name = category.display_name

    if timer_minutes is not None:
        spawn_daemon(rec_id)

    local_hm = started_at.astimezone().strftime("%H:%M")
    detail = f" {escape(description)}" if description else ""
    timer_note = ""
    if timer_minutes is not None:
        timer_note = t("START_TIMER_NOTE", duration=format_duration(timer_minutes))
    print_line(
        t(
            "START_SUCCESS",
            display=escape(display_name),
            detail=detail,
            started_hm=local_hm,
            timer_note=timer_note,
        )
    )
    return 0


def _print_already_active(conn: sqlite3.Connection, active: Record) -> None:
    """記録中セッションがあることを警告表示する。"""
    category = find_category(conn, active.category_key)
    display = category.display_name if category else active.category_key
    started_local = active.started_at.astimezone().strftime("%H:%M")
    detail = f" {active.description}" if active.description else ""
    print_warning(
        t(
            "START_ALREADY_ACTIVE",
            display=display,
            detail=detail,
            started_hm=started_local,
        )
    )
    print_line(t("START_HINT_STOP_FIRST"))
