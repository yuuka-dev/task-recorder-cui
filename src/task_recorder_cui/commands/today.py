"""tsk today: 今日の記録一覧と合計を表示する。"""

from rich.markup import escape

from task_recorder_cui.commands._summary import (
    WEEKDAY_EN,
    aggregate_period,
    period_bounds_utc,
    render_category_totals,
    today_local,
)
from task_recorder_cui.db import open_db
from task_recorder_cui.io import print_line
from task_recorder_cui.repo import find_active_record, row_to_record
from task_recorder_cui.utils.time import format_duration, now_utc, to_iso


def run() -> int:
    """今日のタイムラインとカテゴリ別合計を表示する。

    Returns:
        常に 0 (情報照会として正常終了)。

    """
    today = today_local()

    with open_db() as conn:
        summary = aggregate_period(conn, today, today)

        start_utc, end_next_utc = period_bounds_utc(today, today)
        rows = conn.execute(
            "SELECT * FROM records WHERE started_at >= ? AND started_at < ? ORDER BY started_at",
            (to_iso(start_utc), to_iso(end_next_utc)),
        ).fetchall()
        records = [row_to_record(r) for r in rows]

        active = find_active_record(conn)
        if (
            active is not None
            and start_utc <= active.started_at < end_next_utc
            and all(r.id != active.id for r in records)
        ):
            records.append(active)

        display_names = summary.display_names

    header = f"{today.strftime('%Y-%m-%d')} ({WEEKDAY_EN[today.weekday()]})"
    print_line(header)

    if not records:
        print_line("記録なし")
        return 0

    now = now_utc()
    for rec in records:
        started_hm = rec.started_at.astimezone().strftime("%H:%M")
        display = display_names.get(rec.category_key, rec.category_key)
        desc = rec.description or ""
        label = f"[{escape(display)}] {escape(desc)}".rstrip()

        if rec.ended_at is not None and rec.duration_minutes is not None:
            ended_hm = rec.ended_at.astimezone().strftime("%H:%M")
            print_line(f"{started_hm}-{ended_hm}  {label}  {format_duration(rec.duration_minutes)}")
        else:
            elapsed = max(0, int((now - rec.started_at).total_seconds() / 60))
            print_line(f"{started_hm}-       {label}  (記録中 {format_duration(elapsed)})")

    note = " (記録中含む)" if summary.active_partial_minutes > 0 else ""
    print_line(f"合計: {format_duration(summary.total_minutes)}{note}")
    render_category_totals(summary, with_daily_avg=False)
    return 0
