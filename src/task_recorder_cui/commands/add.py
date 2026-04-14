"""tsk add: 事後に手動で時間記録を追加する。"""

from datetime import timedelta

from rich.markup import escape

from task_recorder_cui.db import open_db
from task_recorder_cui.io import print_error, print_line
from task_recorder_cui.repo import find_category, insert_record
from task_recorder_cui.utils.time import format_duration, now_utc


def run(category_key: str, minutes: int, description: str | None) -> int:
    """started_at = 現在 - minutes, ended_at = 現在 として1レコードを挿入する。

    Args:
        category_key: 対象カテゴリのkey。
        minutes: 記録する分数 (1以上の整数)。
        description: 活動内容 (任意)。

    Returns:
        0: 追加成功 / 1: 未登録カテゴリ、または不正な minutes。

    """
    if minutes <= 0:
        print_error(f"minutes は1以上である必要があります: {minutes}")
        return 1

    with open_db() as conn:
        category = find_category(conn, category_key)
        if category is None:
            print_error(
                f"カテゴリ '{category_key}' が存在しません。`tsk cat list` で一覧を確認してください"
            )
            return 1
        if category.archived:
            print_error(
                f"カテゴリ '{category_key}' はアーカイブ済みです。"
                f"`tsk cat restore {category_key}` または "
                f"`tsk cat add {category_key} <display_name>` で復帰させてください"
            )
            return 1
        ended_at = now_utc()
        started_at = ended_at - timedelta(minutes=minutes)
        with conn:
            insert_record(
                conn,
                category_key=category_key,
                description=description,
                started_at=started_at,
                ended_at=ended_at,
                duration_minutes=minutes,
            )
        display_name = category.display_name

    started_hm = started_at.astimezone().strftime("%H:%M")
    ended_hm = ended_at.astimezone().strftime("%H:%M")
    detail = f" {escape(description)}" if description else ""
    print_line(
        f"追加: [{escape(display_name)}]{detail}"
        f" ({started_hm}-{ended_hm}, {format_duration(minutes)})"
    )
    return 0
