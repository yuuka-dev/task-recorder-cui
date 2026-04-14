"""tsk stop: 記録中のセッションを終了する。"""

from rich.markup import escape

from task_recorder_cui.db import open_db
from task_recorder_cui.io import print_line
from task_recorder_cui.repo import find_active_record, find_category, update_record_end
from task_recorder_cui.utils.time import format_duration, now_utc


def run() -> int:
    """記録中のセッションに終了時刻と duration_minutes を書き込む。

    Returns:
        0: 停止成功 / 1: 記録中のセッションが無い場合。

    """
    with open_db() as conn:
        active = find_active_record(conn)
        if active is None:
            print_line("記録中のセッションはありません")
            return 1

        ended_at = now_utc()
        duration = int((ended_at - active.started_at).total_seconds() / 60)
        with conn:
            update_record_end(conn, active.id, ended_at=ended_at, duration_minutes=duration)

        category = find_category(conn, active.category_key)
        display = category.display_name if category else active.category_key

    started_hm = active.started_at.astimezone().strftime("%H:%M")
    ended_hm = ended_at.astimezone().strftime("%H:%M")
    detail = f" {escape(active.description)}" if active.description else ""
    print_line(
        f"停止: [{escape(display)}]{detail} ({started_hm}-{ended_hm}, {format_duration(duration)})"
    )
    return 0
