"""argparse ベースの CLI エントリポイント。

本モジュールではサブコマンドの受け口 (parser) と main ディスパッチャのみを
用意する。各サブコマンドの実処理は Phase 3-5 で commands/ 配下に実装するため、
現時点ではスタブが「未実装」メッセージを返す。
"""

import argparse

from task_recorder_cui import __version__
from task_recorder_cui.io import print_line

_SUBCOMMAND_PHASE: dict[str, str] = {
    "start": "Phase 3",
    "stop": "Phase 3",
    "add": "Phase 3",
    "now": "Phase 3",
    "today": "Phase 4",
    "week": "Phase 4",
    "month": "Phase 4",
}

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
    sub.add_parser("week", help="直近7日の集計")
    sub.add_parser("month", help="直近30日の集計")

    # --- カテゴリ管理 ---
    p_cat = sub.add_parser("cat", help="カテゴリ管理")
    cat_sub = p_cat.add_subparsers(dest="cat_action", metavar="<action>")
    cat_sub.add_parser("list", help="カテゴリ一覧")
    p_cat_add = cat_sub.add_parser("add", help="カテゴリを追加")
    p_cat_add.add_argument("key", help="新しいカテゴリキー")
    p_cat_add.add_argument("display_name", help="表示名")
    p_cat_remove = cat_sub.add_parser("remove", help="カテゴリをアーカイブ")
    p_cat_remove.add_argument("key")
    p_cat_restore = cat_sub.add_parser("restore", help="アーカイブから復帰")
    p_cat_restore.add_argument("key")
    p_cat_rename = cat_sub.add_parser("rename", help="表示名を変更")
    p_cat_rename.add_argument("key")
    p_cat_rename.add_argument("new_display_name")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI エントリポイント。

    Args:
        argv: 引数リスト。Noneの場合は sys.argv[1:] が使われる。

    Returns:
        終了コード (0: 成功、2: usage error)。
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        return _not_implemented("インタラクティブメニュー", _MENU_PHASE)

    if args.command == "cat":
        if args.cat_action is None:
            parser.parse_args(["cat", "--help"])
            return 2
        return _not_implemented(f"tsk cat {args.cat_action}", _CAT_PHASE)

    phase = _SUBCOMMAND_PHASE.get(args.command, "未定")
    return _not_implemented(f"tsk {args.command}", phase)
