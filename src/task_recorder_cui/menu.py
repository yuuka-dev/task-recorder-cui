"""tsk のインタラクティブメニュー実装。

`tsk` をサブコマンドなしで起動した時に呼ばれる。pure 関数 (DB 読み取りのみ、
副作用なし) と UI 層 (questionary + print) を同一ファイルに同居させ、テストは
pure 関数中心に当てる方針。
"""

import contextlib
from datetime import datetime

import questionary

from task_recorder_cui.commands import month as month_cmd
from task_recorder_cui.commands import stop as stop_cmd
from task_recorder_cui.commands import today as today_cmd
from task_recorder_cui.commands import week as week_cmd
from task_recorder_cui.db import open_db
from task_recorder_cui.io import print_line
from task_recorder_cui.repo import (
    find_active_record,
    find_category,
    list_all_categories,
    list_recent_records,
)
from task_recorder_cui.utils.time import format_duration, humanize_relative, now_utc


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


# NOTE: CLI の仕様変更時はここも更新すること (cli.py / argparse が真実)
_HELP_TEXT = """tsk コマンド一覧

記録:
  tsk start <cat> ["<desc>"]             新しいセッションを開始
  tsk stop                                記録中のセッションを終了
  tsk add   <cat> <分> ["<desc>"]        事後に手動で追加
  tsk now                                 記録中セッションを表示

集計:
  tsk today                               今日の一覧
  tsk week  [--calendar]                  直近7日 / 今週
  tsk month [--calendar]                  直近30日 / 今月
  tsk range --from YYYY-MM-DD --to YYYY-MM-DD   任意期間
  tsk all                                 全累計

カテゴリ:
  tsk cat list [--active|--archived]
  tsk cat add     <key> "<表示名>"
  tsk cat remove  <key>
  tsk cat restore <key>
  tsk cat rename  <key> "<新表示名>"

その他:
  tsk --version / --help
  tsk (引数なし)                          このメニューを起動
"""


def _render_header(now: datetime) -> None:
    """ヘッダ (タイトル + 現在のセッション + 直近) を描画する。"""
    print_line()
    print_line("tsk - task recorder")
    print_line()
    print_line(_active_session_line(now))
    recent = _recent_records_lines(now)
    if recent:
        print_line()
        print_line("直近:")
        for line in recent:
            print_line(line)
    print_line()


def _pause() -> None:
    """Enter で戻る。Ctrl+C / EOF は握りつぶしてループに戻す。"""
    with contextlib.suppress(KeyboardInterrupt, EOFError):
        input("[Enter で戻る]")


def _show_main_menu(*, recording: bool) -> str | None:
    """メインメニューを表示し選択値 (value 文字列) を返す。Ctrl+C / ESC で None。"""
    stop_disabled: str | bool = False if recording else "(記録中のセッションがありません)"
    return questionary.select(
        "操作を選んでください",
        choices=[
            questionary.Choice("開始", value="start"),
            questionary.Choice("停止", value="stop", disabled=stop_disabled),
            questionary.Choice("今日の一覧", value="today"),
            questionary.Choice("週集計", value="week"),
            questionary.Choice("月集計", value="month"),
            questionary.Choice("カテゴリ管理", value="cat"),
            questionary.Choice("ヘルプ (CLI コマンド一覧)", value="help"),
            questionary.Choice("終了", value="quit"),
        ],
    ).ask()


def _show_help() -> None:
    """ヘルプテキストを表示する。"""
    print_line(_HELP_TEXT)


def _start_flow() -> None:
    """[Task 5 で本実装] カテゴリ選択 → description 入力 → start 実行。"""
    print_line("(start フローは Task 5 で実装)")


def _cat_submenu() -> None:
    """[Task 5 で本実装] カテゴリ管理サブメニュー。"""
    print_line("(カテゴリ管理サブメニューは Task 5 で実装)")


def _dispatch(choice: str) -> None:
    """選択値に応じて各アクションを呼ぶ。戻り値は捨てる。"""
    if choice == "start":
        _start_flow()
        return
    if choice == "stop":
        stop_cmd.run()
        return
    if choice == "today":
        today_cmd.run()
        return
    if choice == "week":
        week_cmd.run(calendar=False)
        return
    if choice == "month":
        month_cmd.run(calendar=False)
        return
    if choice == "cat":
        _cat_submenu()
        return
    if choice == "help":
        _show_help()
        return
    # 未知の値は安全に無視
    print_line(f"(未知の選択肢: {choice})")


def run() -> int:
    """メニューのメインループ。常に 0 を返す。

    内部で呼ぶ commands.*.run() の戻り値は意図的に捨てる: メニューはラッパー層で
    あり、終了コードでの成否伝搬は CLI 単発呼び出しの責務とする。

    Returns:
        常に 0。

    """
    while True:
        now = now_utc()
        _render_header(now)
        with open_db() as conn:
            recording = find_active_record(conn) is not None
        choice = _show_main_menu(recording=recording)
        if choice is None or choice == "quit":
            return 0
        try:
            _dispatch(choice)
        except KeyboardInterrupt:
            print_line("(中断しました)")
            continue
        _pause()
