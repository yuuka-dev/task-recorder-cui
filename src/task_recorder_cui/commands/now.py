"""tsk now: 記録中のセッションを経過時間付きで表示する。"""

from rich.markup import escape

from task_recorder_cui.db import open_db
from task_recorder_cui.io import print_line
from task_recorder_cui.repo import find_active_record, find_category
from task_recorder_cui.utils.time import format_duration, now_utc


def run() -> int:
    """記録中セッションを表示する。参照系なので無い場合もエラーにしない。

    Returns:
        常に 0 (情報表示として正常終了)。

    """
    with open_db() as conn:
        active = find_active_record(conn)
        if active is None:
            print_line("記録中のセッションはありません")
            return 0
        category = find_category(conn, active.category_key)
        display = category.display_name if category else active.category_key

    elapsed_min = int((now_utc() - active.started_at).total_seconds() / 60)
    started_hm = active.started_at.astimezone().strftime("%H:%M")
    detail = f" {escape(active.description)}" if active.description else ""
    print_line(f"現在: [{escape(display)}]{detail} ({format_duration(elapsed_min)}経過)")
    print_line(f"開始: {started_hm}")
    return 0
