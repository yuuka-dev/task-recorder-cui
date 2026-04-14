"""argparse ベースの CLI エントリポイント。

本モジュールはサブコマンドの受け口 (parser) と main ディスパッチャを持つ。
記録系 (start/stop/now/add) と参照系 (today/week/month/range/all) は
commands/ 配下の実装に dispatch する。カテゴリ管理 (cat ...)、インタラクティブ
メニューは対応 Phase まで未実装スタブで応答する。
"""

import argparse

from task_recorder_cui import __version__
from task_recorder_cui.commands import add as add_cmd
from task_recorder_cui.commands import all as all_cmd
from task_recorder_cui.commands import month as month_cmd
from task_recorder_cui.commands import now as now_cmd
from task_recorder_cui.commands import range as range_cmd
from task_recorder_cui.commands import start as start_cmd
from task_recorder_cui.commands import stop as stop_cmd
from task_recorder_cui.commands import today as today_cmd
from task_recorder_cui.commands import week as week_cmd
from task_recorder_cui.io import print_line

_CAT_PHASE = "Phase 5"
_MENU_PHASE = "Phase 6"


def _not_implemented(feature: str, phase: str) -> int:
    """未実装コマンド用のスタブ応答。

    Args:
        feature: 機能名 (ユーザ向け表示)。
        phase: 実装予定のフェーズ名。

    Returns:
        常に 0 (エラー扱いしない)。

    """
    print_line(f"({feature} は {phase} で実装予定)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """tsk の引数パーサを構築する。

    Returns:
        サブコマンドを含む設定済み ArgumentParser。

    """
    parser = argparse.ArgumentParser(
        prog="tsk",
        description="日々の時間の使い方を記録して、週平均・月平均で可視化するCUIツール",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"tsk {__version__}",
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # --- 記録系 ---
    p_start = sub.add_parser("start", help="新しいセッションを開始")
    p_start.add_argument("category_key", help="カテゴリキー (例: game, study, dev)")
    p_start.add_argument("description", nargs="?", default=None, help="活動内容 (任意)")

    sub.add_parser("stop", help="記録中のセッションを終了")

    p_add = sub.add_parser("add", help="事後に手動で追加")
    p_add.add_argument("category_key", help="カテゴリキー")
    p_add.add_argument("minutes", type=int, help="記録する分数")
    p_add.add_argument("description", nargs="?", default=None, help="活動内容 (任意)")

    sub.add_parser("now", help="記録中のセッションを表示")

    # --- 参照系 ---
    sub.add_parser("today", help="今日の記録一覧")
    p_week = sub.add_parser("week", help="直近7日 (default) または今週 (--calendar)")
    p_week.add_argument(
        "--calendar",
        action="store_true",
        help="月曜〜今日の今週集計にする",
    )
    p_month = sub.add_parser("month", help="直近30日 (default) または今月 (--calendar)")
    p_month.add_argument(
        "--calendar",
        action="store_true",
        help="今月1日〜今日の集計にする",
    )
    p_range = sub.add_parser("range", help="任意期間の集計")
    p_range.add_argument("--from", dest="from_date", required=True, help="開始日 YYYY-MM-DD")
    p_range.add_argument(
        "--to", dest="to_date", required=True, help="終了日 YYYY-MM-DD (inclusive)"
    )
    sub.add_parser("all", help="全累計")

    # --- カテゴリ管理 ---
    p_cat = sub.add_parser("cat", help="カテゴリ管理")
    cat_sub = p_cat.add_subparsers(dest="cat_action", metavar="<action>", required=True)
    cat_sub.add_parser("list", help="カテゴリ一覧")
    p_cat_add = cat_sub.add_parser("add", help="カテゴリを追加")
    p_cat_add.add_argument("key", help="新しいカテゴリキー")
    p_cat_add.add_argument("display_name", help="表示名")
    p_cat_remove = cat_sub.add_parser("remove", help="カテゴリをアーカイブ")
    p_cat_remove.add_argument("key", help="アーカイブするカテゴリキー")
    p_cat_restore = cat_sub.add_parser("restore", help="アーカイブから復帰")
    p_cat_restore.add_argument("key", help="復帰させるカテゴリキー")
    p_cat_rename = cat_sub.add_parser("rename", help="表示名を変更")
    p_cat_rename.add_argument("key", help="変更するカテゴリキー")
    p_cat_rename.add_argument("new_display_name", help="新しい表示名")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI エントリポイント。

    Args:
        argv: 引数リスト。Noneの場合は sys.argv[1:] が使われる。

    Returns:
        終了コード (0: 成功)。

    Raises:
        SystemExit: --help / --version 表示時、または usage error 時に
            argparse が送出する。正常終了は code=0、usage error は code=2。

    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        return _not_implemented("インタラクティブメニュー", _MENU_PHASE)

    # --- 記録系 (Phase 3) ---
    if args.command == "start":
        return start_cmd.run(args.category_key, args.description)
    if args.command == "stop":
        return stop_cmd.run()
    if args.command == "now":
        return now_cmd.run()
    if args.command == "add":
        return add_cmd.run(args.category_key, args.minutes, args.description)

    # --- 参照系 (Phase 4) ---
    if args.command == "today":
        return today_cmd.run()
    if args.command == "week":
        return week_cmd.run(calendar=args.calendar)
    if args.command == "month":
        return month_cmd.run(calendar=args.calendar)
    if args.command == "range":
        return range_cmd.run(args.from_date, args.to_date)
    if args.command == "all":
        return all_cmd.run()

    # --- 未実装スタブ ---
    if args.command == "cat":
        return _not_implemented(f"tsk cat {args.cat_action}", _CAT_PHASE)

    return _not_implemented(f"tsk {args.command}", "未定")
