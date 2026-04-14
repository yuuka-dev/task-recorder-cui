"""tsk cat サブコマンド群 (list/add/remove/restore/rename)。

各関数は cli.py から `args.cat_action` に応じて呼び出される。
"""

from rich.box import SIMPLE
from rich.markup import escape
from rich.table import Table

from task_recorder_cui.db import open_db
from task_recorder_cui.io import print_error, print_line, print_table
from task_recorder_cui.repo import (
    find_category,
    insert_category,
    list_all_categories,
    update_category_archived,
    update_category_display_name,
)
from task_recorder_cui.utils.validate import validate_category_key


def list_categories(*, active_only: bool = False, archived_only: bool = False) -> int:
    """カテゴリ一覧を表示する。

    Args:
        active_only: True なら archived=0 のみ表示。
        archived_only: True なら archived=1 のみ表示。

    Returns:
        常に 0。

    """
    with open_db() as conn:
        categories = list_all_categories(conn, active_only=active_only, archived_only=archived_only)

    if not categories:
        if archived_only:
            print_line("archived カテゴリはありません")
        elif active_only:
            print_line("active カテゴリはありません")
        else:
            print_line("カテゴリがありません")
        return 0

    table = Table(title="カテゴリ", box=SIMPLE, show_edge=True, pad_edge=False)
    table.add_column("key", style="bold")
    table.add_column("表示名")
    table.add_column("archived", justify="center")
    for cat in categories:
        table.add_row(escape(cat.key), escape(cat.display_name), "✓" if cat.archived else "")
    print_table(table)
    return 0


def add_category(key: str, display_name: str) -> int:
    """カテゴリを新規追加する。

    同じ key が archived 状態で既に存在する場合は、archived=0 に戻し、
    display_name を今回指定された値に更新する (実質 restore + rename)。
    active 状態で存在する場合は重複エラー。

    Args:
        key: 新しいカテゴリキー (ASCII 英小文字+数字+_)。
        display_name: 表示名。

    Returns:
        0: 追加または再有効化成功 / 1: 不正key、空 display_name、重複。

    """
    try:
        validate_category_key(key)
    except ValueError as exc:
        print_error(str(exc))
        return 1
    if not display_name:
        print_error("display_name は空にできません")
        return 1

    with open_db() as conn:
        existing = find_category(conn, key)
        if existing is not None:
            if not existing.archived:
                print_error(
                    f"カテゴリ '{key}' は既に存在します (display_name='{existing.display_name}')"
                )
                return 1
            with conn:
                update_category_archived(conn, key, archived=False)
                update_category_display_name(conn, key, display_name)
            print_line(
                f"再有効化: {key} → '{escape(display_name)}' "
                "(以前 archived だったカテゴリを復帰、display_name を上書き)"
            )
            return 0

        with conn:
            insert_category(conn, key, display_name)
    print_line(f"追加: {key} → '{escape(display_name)}'")
    return 0


def remove_category(key: str) -> int:
    """カテゴリを archived にする (物理削除はしない)。

    Args:
        key: 対象カテゴリキー。

    Returns:
        0: 成功、または既に archived (no-op) / 1: 未存在。

    """
    with open_db() as conn:
        existing = find_category(conn, key)
        if existing is None:
            print_error(f"カテゴリ '{key}' が存在しません")
            return 1
        if existing.archived:
            print_line(f"'{key}' は既にアーカイブ済みです")
            return 0
        with conn:
            update_category_archived(conn, key, archived=True)
    print_line(f"アーカイブ: {key} ('{escape(existing.display_name)}')")
    return 0


def restore_category(key: str) -> int:
    """archived カテゴリを active に戻す。display_name は維持する。

    Args:
        key: 対象カテゴリキー。

    Returns:
        0: 成功、または既に active (no-op) / 1: 未存在。

    """
    with open_db() as conn:
        existing = find_category(conn, key)
        if existing is None:
            print_error(f"カテゴリ '{key}' が存在しません")
            return 1
        if not existing.archived:
            print_line(f"'{key}' は既に有効です")
            return 0
        with conn:
            update_category_archived(conn, key, archived=False)
    print_line(f"復帰: {key} ('{escape(existing.display_name)}')")
    return 0


def rename_category(key: str, new_display_name: str) -> int:
    """display_name のみを変更する。key は不変 (履歴保持のため)。

    Args:
        key: 対象カテゴリキー。
        new_display_name: 新しい表示名。

    Returns:
        0: 成功 / 1: 未存在、空 display_name。

    """
    if not new_display_name:
        print_error("新しい display_name は空にできません")
        return 1
    with open_db() as conn:
        existing = find_category(conn, key)
        if existing is None:
            print_error(f"カテゴリ '{key}' が存在しません")
            return 1
        with conn:
            update_category_display_name(conn, key, new_display_name)
    print_line(f"変更: {key} '{escape(existing.display_name)}' → '{escape(new_display_name)}'")
    return 0
