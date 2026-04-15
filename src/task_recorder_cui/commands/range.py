"""tsk range: 任意期間の集計。"""

from datetime import date

from task_recorder_cui.commands._summary import (
    aggregate_period,
    render_breakdown_table,
    render_category_totals,
)
from task_recorder_cui.db import open_db
from task_recorder_cui.i18n import t
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
        print_error(t("RANGE_INVALID_FROM", value=from_date_str))
        return 1
    try:
        end = date.fromisoformat(to_date_str)
    except ValueError:
        print_error(t("RANGE_INVALID_TO", value=to_date_str))
        return 1
    if start > end:
        print_error(t("RANGE_FROM_AFTER_TO", from_date=start, to_date=end))
        return 1

    with open_db() as conn:
        summary = aggregate_period(conn, start, end)

    title = t("RANGE_HEADER", from_date=start.isoformat(), to_date=end.isoformat())
    print_line(title)

    if summary.total_minutes == 0:
        print_line(t("SUMMARY_NO_RECORDS"))
        return 0

    print_table(render_breakdown_table(summary, title=t("SUMMARY_BREAKDOWN_TITLE")))
    print_line(t("SUMMARY_TOTAL", total=format_duration(summary.total_minutes)))
    render_category_totals(summary, with_daily_avg=True)
    return 0
