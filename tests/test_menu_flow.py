"""menu.py の UI フロー (questionary 経由) を網羅するテスト。

`questionary.select`, `questionary.text`, `questionary.confirm` を
monkeypatch で差し替え、`.ask()` が返す値を制御して分岐を網羅する。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from task_recorder_cui import menu
from task_recorder_cui.db import open_db
from task_recorder_cui.repo import insert_record, set_timer_target
from task_recorder_cui.utils.time import now_utc


class _FakePrompt:
    """questionary 関数の戻り値を差し替えるための最小スタブ。"""

    def __init__(self, value: Any) -> None:
        self._value = value

    def ask(self) -> Any:
        return self._value


def _queue_prompts(
    monkeypatch: pytest.MonkeyPatch,
    *,
    selects: list[Any] | None = None,
    texts: list[Any] | None = None,
    confirms: list[Any] | None = None,
) -> None:
    """questionary.select / text / confirm を順番に値を返すよう差し替える。"""
    select_iter = iter(selects or [])
    text_iter = iter(texts or [])
    confirm_iter = iter(confirms or [])

    def _select(*_args: Any, **_kwargs: Any) -> _FakePrompt:
        return _FakePrompt(next(select_iter))

    def _text(*_args: Any, **_kwargs: Any) -> _FakePrompt:
        return _FakePrompt(next(text_iter))

    def _confirm(*_args: Any, **_kwargs: Any) -> _FakePrompt:
        return _FakePrompt(next(confirm_iter))

    monkeypatch.setattr(menu.questionary, "select", _select)
    monkeypatch.setattr(menu.questionary, "text", _text)
    monkeypatch.setattr(menu.questionary, "confirm", _confirm)


# === _rainbow_text / _gradient_text ===


def test_rainbow_text_rotates_colors() -> None:
    text = menu._rainbow_text("abcdef", phase_seconds=0)
    for color in ("red", "yellow", "green", "cyan", "blue", "magenta"):
        assert f"[{color}]" in text


def test_rainbow_text_phase_shift() -> None:
    a = menu._rainbow_text("a", phase_seconds=0)
    b = menu._rainbow_text("a", phase_seconds=1)
    assert a != b


def test_gradient_text_known_color() -> None:
    text = menu._gradient_text("abcdef", "cyan")
    assert "[cyan]" in text
    assert "[white]" in text


def test_gradient_text_unknown_color_falls_back() -> None:
    text = menu._gradient_text("abc", "puce")
    assert "[puce]" in text
    assert "[white]" in text


# === render_timer_bar の style / flash 分岐 ===


def test_render_timer_bar_solid_style_uses_solid_color() -> None:
    now = datetime(2026, 4, 14, 14, 30, tzinfo=UTC)
    started = datetime(2026, 4, 14, 13, 0, tzinfo=UTC)
    target = datetime(2026, 4, 14, 15, 30, tzinfo=UTC)
    text = menu.render_timer_bar(
        now=now,
        started_at=started,
        target_at=target,
        fired_at=None,
        bar_color="cyan",
        bar_style="solid",
        width=10,
    )
    assert "[cyan]" in text


def test_render_timer_bar_gradient_style() -> None:
    now = datetime(2026, 4, 14, 14, tzinfo=UTC)
    started = datetime(2026, 4, 14, 13, tzinfo=UTC)
    target = datetime(2026, 4, 14, 15, tzinfo=UTC)
    text = menu.render_timer_bar(
        now=now,
        started_at=started,
        target_at=target,
        fired_at=None,
        bar_color="cyan",
        bar_style="gradient",
        width=10,
    )
    assert "[cyan]" in text
    assert "[white]" in text


def test_render_timer_bar_rainbow_style() -> None:
    now = datetime(2026, 4, 14, 14, tzinfo=UTC)
    started = datetime(2026, 4, 14, 13, tzinfo=UTC)
    target = datetime(2026, 4, 14, 15, tzinfo=UTC)
    text = menu.render_timer_bar(
        now=now,
        started_at=started,
        target_at=target,
        fired_at=None,
        bar_color="cyan",
        bar_style="rainbow",
        width=6,
    )
    assert "[red]" in text or "[yellow]" in text


def test_render_timer_bar_unknown_style_no_markup() -> None:
    now = datetime(2026, 4, 14, 14, tzinfo=UTC)
    started = datetime(2026, 4, 14, 13, tzinfo=UTC)
    target = datetime(2026, 4, 14, 15, tzinfo=UTC)
    text = menu.render_timer_bar(
        now=now,
        started_at=started,
        target_at=target,
        fired_at=None,
        bar_color="cyan",
        bar_style="weird",
        width=10,
    )
    assert "[cyan]" not in text


def test_render_timer_bar_flash_suffix_within_window() -> None:
    now = datetime(2026, 4, 14, 15, 30, 2, tzinfo=UTC)
    started = datetime(2026, 4, 14, 13, tzinfo=UTC)
    target = datetime(2026, 4, 14, 15, 30, tzinfo=UTC)
    fired = datetime(2026, 4, 14, 15, 30, 0, tzinfo=UTC)
    text = menu.render_timer_bar(
        now=now,
        started_at=started,
        target_at=target,
        fired_at=fired,
        bar_color="cyan",
        bar_style="solid",
        width=10,
    )
    assert "blink" in text


def test_render_timer_bar_fired_outside_window_bold_only() -> None:
    now = datetime(2026, 4, 14, 16, 0, tzinfo=UTC)
    started = datetime(2026, 4, 14, 13, tzinfo=UTC)
    target = datetime(2026, 4, 14, 15, 30, tzinfo=UTC)
    fired = datetime(2026, 4, 14, 15, 30, tzinfo=UTC)
    text = menu.render_timer_bar(
        now=now,
        started_at=started,
        target_at=target,
        fired_at=fired,
        bar_color="cyan",
        bar_style="solid",
        width=10,
    )
    assert "bold" in text
    assert "blink" not in text


def test_render_timer_bar_no_fill_when_elapsed_zero() -> None:
    now = datetime(2026, 4, 14, 13, 0, tzinfo=UTC)
    started = datetime(2026, 4, 14, 13, 0, tzinfo=UTC)
    target = datetime(2026, 4, 14, 15, 0, tzinfo=UTC)
    text = menu.render_timer_bar(
        now=now,
        started_at=started,
        target_at=target,
        fired_at=None,
        bar_color="cyan",
        bar_style="solid",
        width=10,
    )
    # filled == 0 の分岐: bar_core が空で空白だけが入る
    assert "=" not in text
    assert "0%" in text


# === _render_header ===


def test_render_header_without_active_prints_active_none(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with open_db() as conn:
        menu._render_header(now_utc(), conn)
    out = capsys.readouterr().out
    assert "記録なし" in out or "No active session" in out


def test_render_header_with_timer_prints_bar(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    started = now_utc()
    with open_db() as conn, conn:
        rec_id = insert_record(conn, category_key="dev", description="x", started_at=started)
        set_timer_target(conn, rec_id, target_at=started + timedelta(minutes=30))
    with open_db() as conn:
        menu._render_header(started, conn)
    out = capsys.readouterr().out
    assert "%" in out  # タイマーバーが必ず "X%" を含む


def test_render_header_with_recent_records_prints_recent(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    now = now_utc()
    with open_db() as conn, conn:
        from task_recorder_cui.repo import update_record_end

        rec_id = insert_record(
            conn, category_key="dev", description="past", started_at=now - timedelta(hours=2)
        )
        update_record_end(conn, rec_id, ended_at=now - timedelta(hours=1), duration_minutes=60)
    with open_db() as conn:
        menu._render_header(now, conn)
    out = capsys.readouterr().out
    assert "past" in out


# === _pause ===


def test_pause_returns_on_enter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    menu._pause()


def test_pause_swallows_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_prompt: str = "") -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", _raise)
    menu._pause()  # 例外を漏らさなければ OK


def test_pause_swallows_eof_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_prompt: str = "") -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", _raise)
    menu._pause()


# === _show_main_menu ===


def test_show_main_menu_recording_enables_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def _select(_label: str, *, choices: list[Any], **_kw: Any) -> _FakePrompt:
        captured["choices"] = choices
        return _FakePrompt("quit")

    monkeypatch.setattr(menu.questionary, "select", _select)
    result = menu._show_main_menu(recording=True)
    assert result == "quit"
    stop_choice = next(c for c in captured["choices"] if c.value == "stop")
    assert stop_choice.disabled is False


def test_show_main_menu_not_recording_disables_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def _select(_label: str, *, choices: list[Any], **_kw: Any) -> _FakePrompt:
        captured["choices"] = choices
        return _FakePrompt(None)

    monkeypatch.setattr(menu.questionary, "select", _select)
    result = menu._show_main_menu(recording=False)
    assert result is None
    stop_choice = next(c for c in captured["choices"] if c.value == "stop")
    assert stop_choice.disabled  # truthy な文字列


# === _show_help ===


def test_show_help_prints_command_overview(capsys: pytest.CaptureFixture[str]) -> None:
    menu._show_help()
    out = capsys.readouterr().out
    assert "tsk start" in out
    assert "tsk cat" in out


# === _start_flow ===


def test_start_flow_no_active_categories(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with open_db() as conn, conn:
        for key in ("game", "study", "dev"):
            conn.execute("UPDATE categories SET archived = 1 WHERE key = ?", (key,))

    menu._start_flow()
    out = capsys.readouterr().out
    assert "有効なカテゴリがありません" in out or "No active categories" in out


def test_start_flow_cancel_on_category(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _queue_prompts(monkeypatch, selects=[None])
    menu._start_flow()  # return で抜けるだけで OK


def test_start_flow_cancel_on_description(
    isolated_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _queue_prompts(monkeypatch, selects=["dev"], texts=[None])
    menu._start_flow()


def test_start_flow_cancel_on_timer(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _queue_prompts(monkeypatch, selects=["dev"], texts=["desc", None])
    menu._start_flow()


def test_start_flow_success(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _queue_prompts(monkeypatch, selects=["dev"], texts=["desc", ""])
    calls: list[tuple[Any, ...]] = []

    def _fake_run(*args: Any, **kwargs: Any) -> int:
        calls.append((args, kwargs))
        return 0

    monkeypatch.setattr(menu.start_cmd, "run", _fake_run)
    menu._start_flow()
    assert calls == [(("dev", "desc"), {"timer_spec": None})]


def test_start_flow_with_timer_spec(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _queue_prompts(monkeypatch, selects=["dev"], texts=["desc", "30m"])
    calls: list[tuple[Any, ...]] = []

    def _fake_run(*args: Any, **kwargs: Any) -> int:
        calls.append((args, kwargs))
        return 0

    monkeypatch.setattr(menu.start_cmd, "run", _fake_run)
    menu._start_flow()
    assert calls == [(("dev", "desc"), {"timer_spec": "30m"})]


# === _prompt_to_start_params ===


def test_prompt_to_start_params_all_filled() -> None:
    result = menu._prompt_to_start_params(
        {"category": "dev", "description": "  desc  ", "timer": "30m"}
    )
    assert result == ("dev", "desc", "30m")


def test_prompt_to_start_params_blank_to_none() -> None:
    result = menu._prompt_to_start_params({"category": "dev", "description": "", "timer": "   "})
    assert result == ("dev", None, None)


# === _cat_submenu ===


def _patch_cat_cmd(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    calls: dict[str, list[Any]] = {"list": [], "add": [], "remove": [], "restore": [], "rename": []}

    def _list(*args: Any, **kwargs: Any) -> None:
        calls["list"].append((args, kwargs))

    def _add(*args: Any, **kwargs: Any) -> None:
        calls["add"].append((args, kwargs))

    def _remove(*args: Any, **kwargs: Any) -> None:
        calls["remove"].append((args, kwargs))

    def _restore(*args: Any, **kwargs: Any) -> None:
        calls["restore"].append((args, kwargs))

    def _rename(*args: Any, **kwargs: Any) -> None:
        calls["rename"].append((args, kwargs))

    monkeypatch.setattr(menu.cat_cmd, "list_categories", _list)
    monkeypatch.setattr(menu.cat_cmd, "add_category", _add)
    monkeypatch.setattr(menu.cat_cmd, "remove_category", _remove)
    monkeypatch.setattr(menu.cat_cmd, "restore_category", _restore)
    monkeypatch.setattr(menu.cat_cmd, "rename_category", _rename)
    return calls


def test_cat_submenu_back_returns(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _queue_prompts(monkeypatch, selects=["back"])
    menu._cat_submenu()


def test_cat_submenu_cancel_returns(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _queue_prompts(monkeypatch, selects=[None])
    menu._cat_submenu()


def test_cat_submenu_list_then_back(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(monkeypatch, selects=["list", "back"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    menu._cat_submenu()
    assert len(calls["list"]) == 1


def test_cat_submenu_add_then_back(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(
        monkeypatch,
        selects=["add", "back"],
        texts=["reading", "読書"],
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    menu._cat_submenu()
    assert calls["add"] == [(("reading", "読書"), {})]


def test_cat_submenu_remove_then_back(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(
        monkeypatch,
        selects=["remove", "dev", "back"],
        confirms=[True],
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    menu._cat_submenu()
    assert calls["remove"] == [(("dev",), {})]


def test_cat_submenu_restore_then_back(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with open_db() as conn, conn:
        conn.execute("UPDATE categories SET archived = 1 WHERE key = 'game'")

    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(
        monkeypatch,
        selects=["restore", "game", "back"],
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    menu._cat_submenu()
    assert calls["restore"] == [(("game",), {})]


def test_cat_submenu_rename_then_back(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(
        monkeypatch,
        selects=["rename", "dev", "back"],
        texts=["新開発"],
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    menu._cat_submenu()
    assert calls["rename"] == [(("dev", "新開発"), {})]


# === _cat_add ===


def test_cat_add_cancel_on_key(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(monkeypatch, texts=[None])
    menu._cat_add()
    assert calls["add"] == []


def test_cat_add_empty_key(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(monkeypatch, texts=["   "])
    menu._cat_add()
    assert calls["add"] == []


def test_cat_add_cancel_on_display(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(monkeypatch, texts=["reading", None])
    menu._cat_add()
    assert calls["add"] == []


def test_cat_add_empty_display(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(monkeypatch, texts=["reading", "  "])
    menu._cat_add()
    assert calls["add"] == []


# === _cat_remove ===


def test_cat_remove_no_actives(
    isolated_db: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with open_db() as conn, conn:
        for key in ("game", "study", "dev"):
            conn.execute("UPDATE categories SET archived = 1 WHERE key = ?", (key,))

    calls = _patch_cat_cmd(monkeypatch)
    menu._cat_remove()
    out = capsys.readouterr().out
    assert "active" in out.lower() or "アーカイブから" in out or "active なカテゴリ" in out
    assert calls["remove"] == []


def test_cat_remove_cancel_on_select(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(monkeypatch, selects=[None])
    menu._cat_remove()
    assert calls["remove"] == []


def test_cat_remove_confirm_denied(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(monkeypatch, selects=["dev"], confirms=[False])
    menu._cat_remove()
    assert calls["remove"] == []


# === _cat_restore ===


def test_cat_restore_no_archived(
    isolated_db: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    menu._cat_restore()
    out = capsys.readouterr().out
    assert "archived" in out.lower() or "アーカイブ" in out
    assert calls["restore"] == []


def test_cat_restore_cancel_on_select(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with open_db() as conn, conn:
        conn.execute("UPDATE categories SET archived = 1 WHERE key = 'game'")

    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(monkeypatch, selects=[None])
    menu._cat_restore()
    assert calls["restore"] == []


# === _cat_rename ===


def test_cat_rename_no_actives(
    isolated_db: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with open_db() as conn, conn:
        for key in ("game", "study", "dev"):
            conn.execute("UPDATE categories SET archived = 1 WHERE key = ?", (key,))

    calls = _patch_cat_cmd(monkeypatch)
    menu._cat_rename()
    capsys.readouterr()  # consume
    assert calls["rename"] == []


def test_cat_rename_cancel_on_select(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(monkeypatch, selects=[None])
    menu._cat_rename()
    assert calls["rename"] == []


def test_cat_rename_cancel_on_new_display(
    isolated_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(monkeypatch, selects=["dev"], texts=[None])
    menu._cat_rename()
    assert calls["rename"] == []


def test_cat_rename_empty_new_display(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_cat_cmd(monkeypatch)
    _queue_prompts(monkeypatch, selects=["dev"], texts=["   "])
    menu._cat_rename()
    assert calls["rename"] == []


# === _dispatch ===


def test_dispatch_start(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []
    monkeypatch.setattr(menu, "_start_flow", lambda: called.append("start"))
    menu._dispatch("start")
    assert called == ["start"]


def test_dispatch_stop(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []
    monkeypatch.setattr(menu.stop_cmd, "run", lambda: called.append("stop") or 0)
    menu._dispatch("stop")
    assert called == ["stop"]


def test_dispatch_today(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []
    monkeypatch.setattr(menu.today_cmd, "run", lambda: called.append("today") or 0)
    menu._dispatch("today")
    assert called == ["today"]


def test_dispatch_week(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[Any] = []
    monkeypatch.setattr(
        menu.week_cmd, "run", lambda calendar: called.append(("week", calendar)) or 0
    )
    menu._dispatch("week")
    assert called == [("week", False)]


def test_dispatch_month(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[Any] = []
    monkeypatch.setattr(
        menu.month_cmd, "run", lambda calendar: called.append(("month", calendar)) or 0
    )
    menu._dispatch("month")
    assert called == [("month", False)]


def test_dispatch_cat(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []
    monkeypatch.setattr(menu, "_cat_submenu", lambda: called.append("cat"))
    menu._dispatch("cat")
    assert called == ["cat"]


def test_dispatch_help(capsys: pytest.CaptureFixture[str]) -> None:
    menu._dispatch("help")
    assert "tsk start" in capsys.readouterr().out


def test_dispatch_unknown(capsys: pytest.CaptureFixture[str]) -> None:
    menu._dispatch("bogus")
    out = capsys.readouterr().out
    assert "bogus" in out


# === run / _run_loop ===


def test_run_loop_quit_immediately(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _queue_prompts(monkeypatch, selects=["quit"])
    rc = menu._run_loop()
    assert rc == 0


def test_run_loop_cancel_is_quit(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _queue_prompts(monkeypatch, selects=[None])
    rc = menu._run_loop()
    assert rc == 0


def test_run_loop_dispatches_then_quits(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _queue_prompts(monkeypatch, selects=["today", "quit"])
    monkeypatch.setattr(menu.today_cmd, "run", lambda: 0)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    rc = menu._run_loop()
    assert rc == 0


def test_run_loop_cat_skips_pause(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pause_calls: list[int] = []

    def _count_pause() -> None:
        pause_calls.append(1)

    monkeypatch.setattr(menu, "_pause", _count_pause)
    monkeypatch.setattr(menu, "_cat_submenu", lambda: None)
    _queue_prompts(monkeypatch, selects=["cat", "quit"])
    rc = menu._run_loop()
    assert rc == 0
    assert pause_calls == []  # cat 経路では _pause が呼ばれない


def test_run_loop_swallows_dispatch_keyboard_interrupt(
    isolated_db: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _raise(_choice: str) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(menu, "_dispatch", _raise)
    _queue_prompts(monkeypatch, selects=["today", "quit"])
    rc = menu._run_loop()
    assert rc == 0
    out = capsys.readouterr().out
    assert "中断" in out or "Interrupted" in out


def test_run_wraps_loop_with_menu_lock(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    entered: list[str] = []

    class _FakeLock:
        def __enter__(self) -> None:
            entered.append("in")

        def __exit__(self, *_args: Any) -> None:
            entered.append("out")

    monkeypatch.setattr(menu, "menu_lock", lambda: _FakeLock())
    monkeypatch.setattr(menu, "_run_loop", lambda: 0)
    rc = menu.run()
    assert rc == 0
    assert entered == ["in", "out"]
