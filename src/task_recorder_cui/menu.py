"""tsk のインタラクティブメニュー実装。

`tsk` をサブコマンドなしで起動した時に呼ばれる。pure 関数 (DB 読み取りのみ、
副作用なし) と UI 層 (questionary + print) を同一ファイルに同居させ、テストは
pure 関数中心に当てる方針。
"""

import contextlib
import sqlite3
from datetime import datetime

import questionary
from rich.markup import escape

from task_recorder_cui.commands import cat as cat_cmd
from task_recorder_cui.commands import month as month_cmd
from task_recorder_cui.commands import start as start_cmd
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
from task_recorder_cui.services.timer import menu_lock
from task_recorder_cui.utils.time import format_duration, humanize_relative, now_utc

_RAINBOW_COLORS = ["red", "yellow", "green", "cyan", "blue", "magenta"]


def _rainbow_text(text: str, *, phase_seconds: int) -> str:
    """tick ごとに色が回る virtual rainbow バー。"""
    segments: list[str] = []
    for i, ch in enumerate(text):
        color = _RAINBOW_COLORS[(i + phase_seconds) % len(_RAINBOW_COLORS)]
        segments.append(f"[{color}]{ch}[/{color}]")
    return "".join(segments)


def _gradient_text(text: str, base_color: str) -> str:
    """静的グラデーション (base_color → white)。"""
    gradient_pairs = {
        "cyan": ["cyan", "bright_cyan", "white"],
        "red": ["red", "bright_red", "white"],
        "green": ["green", "bright_green", "white"],
        "blue": ["blue", "bright_blue", "white"],
        "magenta": ["magenta", "bright_magenta", "white"],
        "yellow": ["yellow", "bright_yellow", "white"],
    }
    palette = gradient_pairs.get(base_color, [base_color, "white"])
    segments: list[str] = []
    chunk = max(1, len(text) // len(palette))
    for i, ch in enumerate(text):
        color = palette[min(i // chunk, len(palette) - 1)]
        segments.append(f"[{color}]{ch}[/{color}]")
    return "".join(segments)


def should_flash(
    *,
    now: datetime,
    fired_at: datetime | None,
    window_seconds: int,
) -> bool:
    """直近の発火から window_seconds 以内なら True (= 点滅表示する)。

    Args:
        now: 現在時刻 (tz付き)。
        fired_at: タイマー発火時刻 (未発火なら None)。
        window_seconds: 点滅表示する秒数の閾値。

    Returns:
        窓内なら True、それ以外は False。

    """
    if fired_at is None:
        return False
    delta = (now - fired_at).total_seconds()
    return 0 <= delta < window_seconds


def render_timer_bar(
    *,
    now: datetime,
    started_at: datetime,
    target_at: datetime | None,
    fired_at: datetime | None,
    bar_color: str,
    bar_style: str,
    width: int = 30,
) -> str:
    """タイマー状態を rich 用のマークアップ付き文字列に整形する (pure)。

    Args:
        now: 現在時刻 (tz付き)。
        started_at: セッション開始時刻。
        target_at: タイマー目標時刻 (未設定なら None)。
        fired_at: 発火済なら時刻、未発火なら None。
        bar_color: 'cyan' 等の rich カラー名。
        bar_style: 'solid' / 'rainbow' / 'gradient'。
        width: バーの幅 (文字数)。

    Returns:
        バーを含む 1 行の文字列。タイマー未設定なら空文字。

    """
    if target_at is None:
        return ""

    total_seconds = max(1, int((target_at - started_at).total_seconds()))
    elapsed_seconds = max(0, int((now - started_at).total_seconds()))
    ratio = min(1.0, elapsed_seconds / total_seconds)
    filled = int(width * ratio)
    if filled >= width:
        bar_core = "=" * width
    elif filled > 0:
        bar_core = "=" * (filled - 1) + ">"
    else:
        bar_core = ""
    bar_body = (bar_core + " " * (width - len(bar_core)))[:width]

    if bar_style == "solid":
        colored = f"[{bar_color}]{bar_body}[/{bar_color}]"
    elif bar_style == "gradient":
        colored = _gradient_text(bar_body, bar_color)
    elif bar_style == "rainbow":
        colored = _rainbow_text(bar_body, phase_seconds=elapsed_seconds)
    else:
        colored = bar_body

    elapsed_m = elapsed_seconds // 60
    target_m = total_seconds // 60
    pct = int(ratio * 100)
    suffix = ""
    if should_flash(now=now, fired_at=fired_at, window_seconds=5):
        suffix = " [bold red blink]タイマー経過[/bold red blink]"
    elif fired_at is not None:
        suffix = " [bold]タイマー経過[/bold]"
    elapsed_s = format_duration(elapsed_m)
    target_s = format_duration(target_m)
    return f"[{colored}] {elapsed_s} / {target_s} ({pct}%){suffix}"


def _active_session_line(now: datetime, conn: sqlite3.Connection) -> str:
    """記録中セッションの 1 行表示を返す (副作用なし)。

    Args:
        now: 経過時間計算の基準時刻 (tz付き)。
        conn: 読み取りに使う DB 接続。

    Returns:
        "現在: [<display>] <desc> (<経過>経過)" もしくは "現在: 記録なし"。

    """
    active = find_active_record(conn)
    if active is None:
        return "現在: 記録なし"
    category = find_category(conn, active.category_key)
    display = category.display_name if category is not None else active.category_key

    elapsed_minutes = max(0, int((now - active.started_at).total_seconds() // 60))
    elapsed = format_duration(elapsed_minutes)
    desc = active.description or ""
    return f"現在: [{escape(display)}] {escape(desc)} ({elapsed}経過)"


def _recent_records_lines(now: datetime, conn: sqlite3.Connection, limit: int = 5) -> list[str]:
    """直近の完了済みレコードを 1 行ずつ整形して返す (副作用なし)。

    Args:
        now: 相対時刻計算の基準時刻 (tz付き)。
        conn: 読み取りに使う DB 接続。
        limit: 取得件数。

    Returns:
        各行は "  [<display>] <desc>  <duration>  <relative>" 形式。

    """
    records = list_recent_records(conn, limit)
    if not records:
        return []
    cats = {c.key: c.display_name for c in list_all_categories(conn)}

    lines: list[str] = []
    for r in records:
        display = escape(cats.get(r.category_key, r.category_key))
        desc = escape(r.description or "")
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


def _render_header(now: datetime, conn: sqlite3.Connection) -> None:
    """ヘッダ (タイトル + 現在のセッション + タイマーバー + 直近) を描画する。"""
    from task_recorder_cui.config import load_config

    print_line()
    print_line("tsk - task recorder")
    print_line()
    print_line(_active_session_line(now, conn))
    active = find_active_record(conn)
    if active is not None and active.timer_target_at is not None:
        cfg = load_config()
        bar = render_timer_bar(
            now=now,
            started_at=active.started_at,
            target_at=active.timer_target_at,
            fired_at=active.timer_fired_at,
            bar_color=cfg.ui.bar_color,
            bar_style=cfg.ui.bar_style,
            width=30,
        )
        if bar:
            print_line(bar)
    recent = _recent_records_lines(now, conn)
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


def _prompt_to_start_params(
    form: dict[str, str],
) -> tuple[str, str | None, str | None]:
    """メニュー入力 dict を `start_cmd.run` 引数に整形する (pure)。

    Args:
        form: questionary のフォーム結果 (category / description / timer キーを持つ)。

    Returns:
        (category_key, description | None, timer_spec | None) のタプル。
        description と timer は空白 or 空文字なら None にする。

    """
    category = form["category"]
    desc_raw = form.get("description", "").strip()
    timer_raw = form.get("timer", "").strip()
    description = desc_raw if desc_raw else None
    timer_spec = timer_raw if timer_raw else None
    return category, description, timer_spec


def _start_flow() -> None:
    """カテゴリ選択 → description 入力 → タイマー入力 → start 実行。

    active カテゴリが 0 件なら案内のみ。キャンセル (Ctrl+C/ESC) で安全に戻る。
    """
    with open_db() as conn:
        actives = list_all_categories(conn, active_only=True)

    if not actives:
        print_line("有効なカテゴリがありません。先に『カテゴリ管理 → 追加』してください。")
        return

    key = questionary.select(
        "カテゴリを選んでください",
        choices=[
            questionary.Choice(title=f"{c.display_name} ({c.key})", value=c.key) for c in actives
        ],
    ).ask()
    if key is None:
        return

    desc = questionary.text("何をしましたか (任意、空欄可)", default="").ask()
    if desc is None:
        return

    timer_answer = questionary.text(
        "タイマー (例: 2h30m、空欄でスキップ)",
        default="",
    ).ask()
    if timer_answer is None:
        return

    form = {
        "category": key,
        "description": desc,
        "timer": timer_answer,
    }
    category, desc_or_none, timer_spec = _prompt_to_start_params(form)
    start_cmd.run(category, desc_or_none, timer_spec=timer_spec)


def _cat_submenu() -> None:
    """カテゴリ管理サブメニュー (list/add/remove/restore/rename/back のループ)。"""
    while True:
        action = questionary.select(
            "カテゴリ管理",
            choices=[
                questionary.Choice("一覧表示", value="list"),
                questionary.Choice("追加", value="add"),
                questionary.Choice("アーカイブ", value="remove"),
                questionary.Choice("アーカイブから復帰", value="restore"),
                questionary.Choice("表示名を変更", value="rename"),
                questionary.Choice("← 戻る", value="back"),
            ],
        ).ask()
        if action is None or action == "back":
            return

        if action == "list":
            cat_cmd.list_categories(active_only=False, archived_only=False)
        elif action == "add":
            _cat_add()
        elif action == "remove":
            _cat_remove()
        elif action == "restore":
            _cat_restore()
        elif action == "rename":
            _cat_rename()

        _pause()


def _cat_add() -> None:
    """カテゴリ追加 (key / display_name を順に入力)。"""
    key = questionary.text("新しいカテゴリキー (ASCII 英小文字・数字・_)").ask()
    if key is None or not key.strip():
        return
    display_name = questionary.text("表示名").ask()
    if display_name is None or not display_name.strip():
        return
    cat_cmd.add_category(key.strip(), display_name.strip())


def _cat_remove() -> None:
    """カテゴリのアーカイブ (active から選択 → confirm)。"""
    with open_db() as conn:
        actives = list_all_categories(conn, active_only=True)
    if not actives:
        print_line("active なカテゴリがありません")
        return
    key = questionary.select(
        "アーカイブするカテゴリを選んでください",
        choices=[
            questionary.Choice(title=f"{c.display_name} ({c.key})", value=c.key) for c in actives
        ],
    ).ask()
    if key is None:
        return
    target = next(c for c in actives if c.key == key)
    confirmed = questionary.confirm(
        f"{target.display_name} ({target.key}) をアーカイブしますか？",
        default=False,
    ).ask()
    if not confirmed:
        return
    cat_cmd.remove_category(key)


def _cat_restore() -> None:
    """archived カテゴリの復帰。"""
    with open_db() as conn:
        archived = list_all_categories(conn, archived_only=True)
    if not archived:
        print_line("archived なカテゴリがありません")
        return
    key = questionary.select(
        "復帰させるカテゴリを選んでください",
        choices=[
            questionary.Choice(title=f"{c.display_name} ({c.key})", value=c.key) for c in archived
        ],
    ).ask()
    if key is None:
        return
    cat_cmd.restore_category(key)


def _cat_rename() -> None:
    """display_name の変更 (active から選択 → 新名入力)。"""
    with open_db() as conn:
        actives = list_all_categories(conn, active_only=True)
    if not actives:
        print_line("active なカテゴリがありません")
        return
    key = questionary.select(
        "表示名を変更するカテゴリを選んでください",
        choices=[
            questionary.Choice(title=f"{c.display_name} ({c.key})", value=c.key) for c in actives
        ],
    ).ask()
    if key is None:
        return
    target = next(c for c in actives if c.key == key)
    new_name = questionary.text("新しい表示名", default=target.display_name).ask()
    if new_name is None or not new_name.strip():
        return
    cat_cmd.rename_category(key, new_name.strip())


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

    実行中は menu_lock を取得し、タイマー daemon 側が「メニュー起動中」を
    検出できるようにする (閉時の MessageBox 抑止のため)。

    Returns:
        常に 0。

    """
    with menu_lock():
        return _run_loop()


def _run_loop() -> int:
    while True:
        now = now_utc()
        with open_db() as conn:
            _render_header(now, conn)
            recording = find_active_record(conn) is not None
        choice = _show_main_menu(recording=recording)
        if choice is None or choice == "quit":
            return 0
        try:
            _dispatch(choice)
        except KeyboardInterrupt:
            print_line("(中断しました)")
            continue
        # カテゴリ管理は submenu 側で各アクション後に _pause するため、
        # 戻った直後に再度 Enter 要求するのは UX 的に冗長。
        if choice != "cat":
            _pause()
