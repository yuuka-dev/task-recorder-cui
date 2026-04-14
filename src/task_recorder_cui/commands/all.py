"""tsk all: 全累計。"""

from datetime import date

from task_recorder_cui.commands._summary import (
    aggregate_period,
    render_category_totals,
    today_local,
)
from task_recorder_cui.db import open_db
from task_recorder_cui.io import print_line
from task_recorder_cui.utils.time import format_duration, from_iso


def run() -> int:
    """最古の記録日から今日までの全累計を表示する (日別内訳は出さない)。

    Returns:
        常に 0。

    """
    today = today_local()

    with open_db() as conn:
        row = conn.execute("SELECT MIN(started_at) AS earliest FROM records").fetchone()
        if row is None or row["earliest"] is None:
            print_line("全累計")
            print_line("記録なし")
            return 0
        start: date = from_iso(row["earliest"]).astimezone().date()
        summary = aggregate_period(conn, start, today)

    title = f"全累計 ({start.isoformat()} 以降)"
    print_line(title)
    print_line(f"合計: {format_duration(summary.total_minutes)}")
    render_category_totals(summary, with_daily_avg=True)
    return 0
