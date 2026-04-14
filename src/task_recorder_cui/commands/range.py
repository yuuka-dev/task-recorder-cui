"""tsk range: 任意期間の集計。"""

from datetime import date

from task_recorder_cui.commands._summary import (
    aggregate_period,
    render_breakdown_table,
    render_category_totals,
)
from task_recorder_cui.db import open_db
from task_recorder_cui.io import print_error, print_line, print_table
from task_recorder_cui.utils.time import format_duration


def run(from_date_str: str, to_date_str: str) -> int:
    """任意期間 [from, to] の集計を表示する。

    Args:
        from_date_str: 開始日の ISO形式 (YYYY-MM-DD)。
        to_date_str: 終了日の ISO形式 (YYYY-MM-DD, inclusive)。

    Returns:
        0: 成功 / 1: 日付パース失敗、または from > to。

    """
    try:
        start = date.fromisoformat(from_date_str)
    except ValueError:
        print_error(f"--from の日付形式が不正です (YYYY-MM-DD): {from_date_str!r}")
        return 1
    try:
        end = date.fromisoformat(to_date_str)
    except ValueError:
        print_error(f"--to の日付形式が不正です (YYYY-MM-DD): {to_date_str!r}")
        return 1
    if start > end:
        print_error(f"--from ({start}) は --to ({end}) 以前である必要があります")
        return 1

    with open_db() as conn:
        summary = aggregate_period(conn, start, end)

    title = f"期間指定 ({start.isoformat()} 〜 {end.isoformat()})"
    print_line(title)

    if summary.total_minutes == 0:
        print_line("記録なし")
        return 0

    print_table(render_breakdown_table(summary, title="日別"))
    print_line(f"合計: {format_duration(summary.total_minutes)}")
    render_category_totals(summary, with_daily_avg=True)
    return 0
