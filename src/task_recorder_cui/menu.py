"""tsk のインタラクティブメニュー実装。

`tsk` をサブコマンドなしで起動した時に呼ばれる。pure 関数 (DB 読み取りのみ、
副作用なし) と UI 層 (questionary + print) を同一ファイルに同居させ、テストは
pure 関数中心に当てる方針。
"""

from datetime import datetime

from task_recorder_cui.db import open_db
from task_recorder_cui.repo import (
    find_active_record,
    find_category,
    list_all_categories,
    list_recent_records,
)
from task_recorder_cui.utils.time import format_duration, humanize_relative


def _active_session_line(now: datetime) -> str:
    """記録中セッションの 1 行表示を返す (副作用なし)。

    Args:
        now: 経過時間計算の基準時刻 (tz付き)。

    Returns:
        "現在: [<display>] <desc> (<経過>経過)" もしくは "現在: 記録なし"。

    """
    with open_db() as conn:
        active = find_active_record(conn)
        if active is None:
            return "現在: 記録なし"
        category = find_category(conn, active.category_key)
        display = category.display_name if category is not None else active.category_key

    elapsed_minutes = max(0, int((now - active.started_at).total_seconds() // 60))
    elapsed = format_duration(elapsed_minutes)
    desc = active.description or ""
    return f"現在: [{display}] {desc} ({elapsed}経過)"


def _recent_records_lines(now: datetime, limit: int = 5) -> list[str]:
    """直近の完了済みレコードを 1 行ずつ整形して返す (副作用なし)。

    Args:
        now: 相対時刻計算の基準時刻 (tz付き)。
        limit: 取得件数。

    Returns:
        各行は "  [<display>] <desc>  <duration>  <relative>" 形式。

    """
    with open_db() as conn:
        records = list_recent_records(conn, limit)
        if not records:
            return []
        cats = {c.key: c.display_name for c in list_all_categories(conn)}

    lines: list[str] = []
    for r in records:
        display = cats.get(r.category_key, r.category_key)
        desc = r.description or ""
        duration = format_duration(r.duration_minutes or 0)
        relative = humanize_relative(r.started_at, now)
        lines.append(f"  [{display}] {desc}  {duration}  {relative}")
    return lines
