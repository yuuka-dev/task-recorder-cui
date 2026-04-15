"""集計系コマンド (today/week/month/range/all) の共通ロジック。

SQLite からレコードを取得し、ローカル日付でグルーピングして日別×カテゴリの
集計を行う。表示は rich.Table を使って CJK 幅のズレを吸収する。

仕様:
- 日付境界はシステムのローカルタイムゾーンにおける 00:00〜翌00:00
- 日またぎレコードは started_at の日に計上 (分割しない)
- 記録中セッションは started_at が期間内のとき、現在時刻までの経過分を計上
- display_name は常に現在の categories テーブルから引く (rename 即時反映)
"""

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from rich.box import SIMPLE
from rich.markup import escape
from rich.table import Table

from task_recorder_cui.i18n import t
from task_recorder_cui.io import print_line, print_table
from task_recorder_cui.repo import find_active_record, row_to_record
from task_recorder_cui.utils.time import format_duration, now_utc, to_iso

WEEKDAY_EN: list[str] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@dataclass(frozen=True)
class DayTotal:
    """1日分のカテゴリ別集計。

    Attributes:
        local_date: 対象のローカル日付。
        per_category_minutes: カテゴリkey → 分数。
        total_minutes: 全カテゴリ合計分。

    """

    local_date: date
    per_category_minutes: dict[str, int]
    total_minutes: int


@dataclass(frozen=True)
class PeriodSummary:
    """期間全体の集計結果。

    Attributes:
        start_local: 集計期間の開始日 (inclusive)。
        end_local: 集計期間の終了日 (inclusive)。
        days: レコードがあった日の DayTotal リスト (昇順)。
        per_category_minutes: カテゴリkey → 期間内分数合計。
        total_minutes: 全カテゴリの期間内合計分。
        display_names: カテゴリkey → display_name (現在の値)。
        active_partial_minutes: 記録中セッションから計上された分数 (0 なら含まない)。

    """

    start_local: date
    end_local: date
    days: list[DayTotal]
    per_category_minutes: dict[str, int]
    total_minutes: int
    display_names: dict[str, str]
    active_partial_minutes: int


def today_local() -> date:
    """システムのローカルタイムゾーンにおける今日の日付を返す。"""
    return datetime.now().astimezone().date()


def _to_local_date(dt: datetime) -> date:
    """tz付き datetime をローカル日付に変換する。"""
    return dt.astimezone().date()


def period_bounds_utc(start_local_date: date, end_local_date: date) -> tuple[datetime, datetime]:
    """ローカル日付範囲を UTC の半開区間 [start_utc, end_next_utc) に変換。"""
    start_utc = datetime.combine(start_local_date, time.min).astimezone().astimezone(UTC)
    end_next_utc = (
        datetime.combine(end_local_date + timedelta(days=1), time.min).astimezone().astimezone(UTC)
    )
    return start_utc, end_next_utc


def aggregate_period(
    conn: sqlite3.Connection,
    start_local_date: date,
    end_local_date: date,
    *,
    include_active: bool = True,
) -> PeriodSummary:
    """指定ローカル日付区間 [start, end] の集計を返す (両端inclusive)。

    Args:
        conn: DB接続。
        start_local_date: 集計開始日 (local)。
        end_local_date: 集計終了日 (local, inclusive)。
        include_active: 記録中セッションを期間に含めるか。

    Returns:
        PeriodSummary。レコードが1件もなければ days=[]。

    """
    start_utc, end_next_utc = period_bounds_utc(start_local_date, end_local_date)

    rows = conn.execute(
        "SELECT * FROM records WHERE started_at >= ? AND started_at < ? ORDER BY started_at",
        (to_iso(start_utc), to_iso(end_next_utc)),
    ).fetchall()
    records = [row_to_record(r) for r in rows]

    if include_active:
        active = find_active_record(conn)
        if (
            active is not None
            and start_utc <= active.started_at < end_next_utc
            and all(r.id != active.id for r in records)
        ):
            records.append(
                active
            )  # pragma: no cover  # 防御的二重チェック (実走行では records に含まれる)

    now = now_utc()
    day_buckets: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_category: dict[str, int] = defaultdict(int)
    active_partial_minutes = 0

    for rec in records:
        local_d = _to_local_date(rec.started_at)
        if rec.duration_minutes is not None:
            minutes = rec.duration_minutes
        else:
            minutes = max(0, int((now - rec.started_at).total_seconds() / 60))
            active_partial_minutes += minutes
        day_buckets[local_d][rec.category_key] += minutes
        per_category[rec.category_key] += minutes

    days = [
        DayTotal(
            local_date=d,
            per_category_minutes=dict(buckets),
            total_minutes=sum(buckets.values()),
        )
        for d, buckets in sorted(day_buckets.items())
    ]

    category_keys = list(per_category.keys())
    display_names: dict[str, str] = {}
    if category_keys:
        placeholders = ",".join("?" for _ in category_keys)
        category_rows = conn.execute(
            f"SELECT key, display_name FROM categories WHERE key IN ({placeholders})",
            category_keys,
        ).fetchall()
        display_names = {row["key"]: row["display_name"] for row in category_rows}
    for key in category_keys:
        display_names.setdefault(key, key)

    return PeriodSummary(
        start_local=start_local_date,
        end_local=end_local_date,
        days=days,
        per_category_minutes=dict(per_category),
        total_minutes=sum(per_category.values()),
        display_names=display_names,
        active_partial_minutes=active_partial_minutes,
    )


def _sorted_category_keys(summary: PeriodSummary) -> list[str]:
    """合計分数の降順でカテゴリキーを並べる (同点は key 昇順)。"""
    return sorted(
        summary.per_category_minutes.keys(),
        key=lambda k: (-summary.per_category_minutes[k], k),
    )


def render_breakdown_table(summary: PeriodSummary, title: str) -> Table:
    """日別×カテゴリの内訳テーブルを組み立てる。

    Args:
        summary: 集計結果。
        title: テーブルタイトル。

    Returns:
        そのまま print_table() に渡せる Table。

    """
    keys = _sorted_category_keys(summary)
    table = Table(title=title, box=SIMPLE, show_edge=True, pad_edge=False)
    table.add_column(t("SUMMARY_BREAKDOWN_COL_DATE"), justify="left", no_wrap=True)
    for key in keys:
        table.add_column(escape(summary.display_names.get(key, key)), justify="right")
    table.add_column(t("SUMMARY_BREAKDOWN_COL_TOTAL"), justify="right", style="bold")

    for day in summary.days:
        weekday = WEEKDAY_EN[day.local_date.weekday()]
        date_cell = f"{day.local_date.strftime('%m-%d')} {weekday}"
        row = [date_cell]
        for key in keys:
            minutes = day.per_category_minutes.get(key, 0)
            row.append(format_duration(minutes) if minutes > 0 else "")
        row.append(format_duration(day.total_minutes))
        table.add_row(*row)

    return table


def render_category_totals(summary: PeriodSummary, *, with_daily_avg: bool = False) -> None:
    """カテゴリ別合計 (降順) を表示する。

    Args:
        summary: 集計結果。
        with_daily_avg: True のとき "/ 日平均 1h30m" を付記する (week/month/range用)。

    """
    total = summary.total_minutes
    if not summary.per_category_minutes:
        print_line(t("SUMMARY_NO_RECORDS"))
        return

    day_count = (summary.end_local - summary.start_local).days + 1
    keys = _sorted_category_keys(summary)

    grid = Table.grid(padding=(0, 1))
    grid.add_column()  # label:
    grid.add_column(justify="right")  # duration
    grid.add_column()  # percentage
    if with_daily_avg:
        grid.add_column()  # daily avg

    for key in keys:
        minutes = summary.per_category_minutes[key]
        name = summary.display_names.get(key, key)
        pct = round(minutes * 100 / total) if total > 0 else 0
        label = f"{escape(name)}:"
        duration = format_duration(minutes)
        percent = f"({pct}%)"
        if with_daily_avg:
            avg = minutes // day_count if day_count > 0 else 0
            grid.add_row(
                label,
                duration,
                percent,
                t("SUMMARY_DAILY_AVG_SUFFIX", avg=format_duration(avg)),
            )
        else:
            grid.add_row(label, duration, percent)

    print_table(grid)
