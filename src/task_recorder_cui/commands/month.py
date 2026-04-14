"""tsk month: 月集計。"""

from datetime import date, timedelta

from task_recorder_cui.commands._summary import (
    aggregate_period,
    render_breakdown_table,
    render_category_totals,
    today_local,
)
from task_recorder_cui.db import open_db
from task_recorder_cui.io import print_line, print_table
from task_recorder_cui.utils.time import format_duration


def _month_range(today: date, calendar: bool) -> tuple[date, date]:
    """表示対象の開始日と終了日 (inclusive) を返す。

    Args:
        today: 起点日。
        calendar: True なら今月 (1日〜今日)、False なら直近30日間。

    """
    if calendar:
        return today.replace(day=1), today
    return today - timedelta(days=29), today


def run(*, calendar: bool = False) -> int:
    """月集計を表示する。

    Args:
        calendar: True なら今月 (1日〜今日)、False なら直近30日 (rolling)。

    Returns:
        常に 0。

    """
    today = today_local()
    start, end = _month_range(today, calendar)

    with open_db() as conn:
        summary = aggregate_period(conn, start, end)

    label = "今月" if calendar else "直近30日"
    title = f"{label} ({start.isoformat()} 〜 {end.isoformat()})"
    print_line(title)

    if summary.total_minutes == 0:
        print_line("記録なし")
        return 0

    print_table(render_breakdown_table(summary, title="日別"))
    print_line(f"合計: {format_duration(summary.total_minutes)}")
    render_category_totals(summary, with_daily_avg=True)
    return 0
