"""tsk timer サブコマンド: set / cancel。"""

from datetime import timedelta

from task_recorder_cui.db import open_db
from task_recorder_cui.io import print_error, print_line
from task_recorder_cui.repo import (
    clear_timer_target,
    find_active_record,
    set_timer_target,
)
from task_recorder_cui.services.timer import parse_timer_spec, spawn_daemon
from task_recorder_cui.utils.time import format_duration, now_utc


def set_(spec: str) -> int:
    """記録中セッションにタイマーを設定する。

    Args:
        spec: '2h30m' 形式の時刻指定文字列。

    Returns:
        0: 成功 / 1: 記録中セッション無し / 1: 書式不正。

    """
    try:
        minutes = parse_timer_spec(spec)
    except ValueError as e:
        print_error(str(e))
        return 1

    with open_db() as conn:
        active = find_active_record(conn)
        if active is None:
            print_error("記録中のセッションがありません。`tsk start` で開始してください")
            return 1
        target = now_utc() + timedelta(minutes=minutes)
        with conn:
            set_timer_target(conn, active.id, target_at=target)
        rec_id = active.id

    spawn_daemon(rec_id)
    print_line(f"タイマー設定: {format_duration(minutes)} 後に発火します")
    return 0


def cancel() -> int:
    """記録中セッションのタイマーをキャンセルする。

    Returns:
        0: キャンセル成功 / 1: セッション無し or タイマー未設定。

    """
    with open_db() as conn:
        active = find_active_record(conn)
        if active is None:
            print_error("記録中のセッションがありません")
            return 1
        if active.timer_target_at is None:
            print_error("タイマーは設定されていません")
            return 1
        with conn:
            clear_timer_target(conn, active.id)

    print_line("タイマーをキャンセルしました")
    return 0
