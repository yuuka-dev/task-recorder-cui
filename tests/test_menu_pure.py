"""menu.py の pure 関数の単体テスト (副作用なし、DB 読み取りのみ)。"""

from datetime import UTC, datetime, timedelta

from task_recorder_cui.db import open_db
from task_recorder_cui.menu import _active_session_line, _recent_records_lines
from task_recorder_cui.repo import insert_record, update_record_end


def test_active_session_line_when_recording(isolated_db) -> None:
    started = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    now = started + timedelta(minutes=32)
    with open_db() as conn, conn:
        insert_record(conn, category_key="dev", description="ObatLog実装", started_at=started)

    with open_db() as conn:
        line = _active_session_line(now, conn)
    assert "現在:" in line
    assert "[開発]" in line  # display_name が解決される
    assert "ObatLog実装" in line
    assert "32m" in line
    assert "経過" in line


def test_active_session_line_when_no_description(isolated_db) -> None:
    started = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    now = started + timedelta(minutes=10)
    with open_db() as conn, conn:
        insert_record(conn, category_key="game", description=None, started_at=started)

    with open_db() as conn:
        line = _active_session_line(now, conn)
    assert "[ゲーム]" in line
    assert "10m" in line


def test_active_session_line_when_idle(isolated_db) -> None:
    now = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    with open_db() as conn:
        line = _active_session_line(now, conn)
    assert line == "現在: 記録なし"


def test_recent_records_lines_empty(isolated_db) -> None:
    now = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    with open_db() as conn:
        lines = _recent_records_lines(now, conn, limit=5)
    assert lines == []


def test_recent_records_lines_format_and_order(isolated_db) -> None:
    base = datetime(2026, 4, 15, 8, 0, 0, tzinfo=UTC)
    now = datetime(2026, 4, 15, 13, 0, 0, tzinfo=UTC)
    with open_db() as conn, conn:
        for i, key in enumerate(["dev", "game", "study"]):
            started = base + timedelta(hours=i)
            ended = started + timedelta(minutes=30 + i * 15)
            rec_id = insert_record(
                conn, category_key=key, description=f"item-{i}", started_at=started
            )
            duration = int((ended - started).total_seconds() // 60)
            update_record_end(conn, rec_id, ended_at=ended, duration_minutes=duration)

    with open_db() as conn:
        lines = _recent_records_lines(now, conn, limit=5)
    assert len(lines) == 3
    # 新しい順
    assert "item-2" in lines[0]
    assert "item-1" in lines[1]
    assert "item-0" in lines[2]
    # display_name が解決される (dev → 開発、game → ゲーム、study → 学習)
    assert "[学習]" in lines[0]
    assert "[ゲーム]" in lines[1]
    assert "[開発]" in lines[2]
    # 各行は 2 スペースインデント
    for line in lines:
        assert line.startswith("  ")


def test_recent_records_lines_respects_limit(isolated_db) -> None:
    base = datetime(2026, 4, 15, 8, 0, 0, tzinfo=UTC)
    now = datetime(2026, 4, 15, 14, 0, 0, tzinfo=UTC)
    with open_db() as conn, conn:
        for i in range(7):
            started = base + timedelta(minutes=i * 30)
            ended = started + timedelta(minutes=10)
            rec_id = insert_record(
                conn, category_key="dev", description=f"#{i}", started_at=started
            )
            duration = int((ended - started).total_seconds() // 60)
            update_record_end(conn, rec_id, ended_at=ended, duration_minutes=duration)

    with open_db() as conn:
        lines = _recent_records_lines(now, conn, limit=3)
    assert len(lines) == 3


# --- Task 20: render_timer_bar ---


def test_render_timer_bar_with_active_timer() -> None:
    """活性タイマー (未発火) の場合、'<経過>m / <目標>m (<%>%)' を返す。"""
    from task_recorder_cui.menu import render_timer_bar

    now = datetime(2026, 4, 14, 14, 30, tzinfo=UTC)
    started = datetime(2026, 4, 14, 13, 0, tzinfo=UTC)
    target = datetime(2026, 4, 14, 15, 30, tzinfo=UTC)
    text = render_timer_bar(
        now=now,
        started_at=started,
        target_at=target,
        fired_at=None,
        bar_color="cyan",
        bar_style="solid",
        width=20,
    )
    assert "1h30m" in text
    assert "2h30m" in text
    assert "60%" in text
    assert "[" in text and "]" in text
    assert "[[" not in text


def test_render_timer_bar_fired_shows_expired() -> None:

    from task_recorder_cui.menu import render_timer_bar

    now = datetime(2026, 4, 14, 16, 0, tzinfo=UTC)
    started = datetime(2026, 4, 14, 13, 0, tzinfo=UTC)
    target = datetime(2026, 4, 14, 15, 30, tzinfo=UTC)
    fired = datetime(2026, 4, 14, 15, 30, tzinfo=UTC)
    text = render_timer_bar(
        now=now,
        started_at=started,
        target_at=target,
        fired_at=fired,
        bar_color="cyan",
        bar_style="solid",
        width=20,
    )
    assert "経過" in text or "expired" in text.lower() or "100%" in text


def test_render_timer_bar_no_timer_returns_empty() -> None:
    """タイマー未設定なら空文字 (呼び出し側が行を出さない)。"""
    from task_recorder_cui.menu import render_timer_bar

    now = datetime(2026, 4, 14, 14, tzinfo=UTC)
    started = datetime(2026, 4, 14, 13, tzinfo=UTC)
    text = render_timer_bar(
        now=now,
        started_at=started,
        target_at=None,
        fired_at=None,
        bar_color="cyan",
        bar_style="solid",
        width=20,
    )
    assert text == ""


# --- Task 23: should_flash ---


def test_should_flash_when_fired_recently() -> None:
    """fired_at が 5 秒以内なら点滅対象。"""
    from task_recorder_cui.menu import should_flash

    now = datetime(2026, 4, 14, 14, 30, tzinfo=UTC)
    fired = datetime(2026, 4, 14, 14, 29, 57, tzinfo=UTC)
    assert should_flash(now=now, fired_at=fired, window_seconds=5) is True


def test_should_flash_false_after_window() -> None:

    from task_recorder_cui.menu import should_flash

    now = datetime(2026, 4, 14, 14, 30, tzinfo=UTC)
    fired = datetime(2026, 4, 14, 14, 29, 50, tzinfo=UTC)
    assert should_flash(now=now, fired_at=fired, window_seconds=5) is False


def test_should_flash_false_when_none() -> None:

    from task_recorder_cui.menu import should_flash

    now = datetime(2026, 4, 14, 14, 30, tzinfo=UTC)
    assert should_flash(now=now, fired_at=None, window_seconds=5) is False


# --- _build_tick_lines ---


def test_build_tick_lines_no_active_returns_single_line(isolated_db) -> None:
    """記録なし → 「現在: 記録なし」1 要素。"""
    from task_recorder_cui.menu import _build_tick_lines

    now = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    with open_db() as conn:
        lines = _build_tick_lines(now, conn, bar_color="cyan", bar_style="solid")
    assert len(lines) == 1
    assert "記録なし" in lines[0]


def test_build_tick_lines_active_no_timer_returns_single_line(isolated_db) -> None:
    """記録中・タイマーなし → 経過時間付き 1 要素。"""
    from task_recorder_cui.menu import _build_tick_lines

    started = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    now = started + timedelta(minutes=45)
    with open_db() as conn, conn:
        insert_record(conn, category_key="dev", description="test", started_at=started)
    with open_db() as conn:
        lines = _build_tick_lines(now, conn, bar_color="cyan", bar_style="solid")
    assert len(lines) == 1
    assert "45m" in lines[0]


def test_build_tick_lines_active_with_timer_returns_two_lines(isolated_db) -> None:
    """記録中・タイマーあり → 2 要素 (経過行 + バー行)。"""
    from task_recorder_cui.menu import _build_tick_lines
    from task_recorder_cui.repo import set_timer_target

    started = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    now = started + timedelta(minutes=30)
    target = started + timedelta(minutes=60)
    with open_db() as conn, conn:
        rec_id = insert_record(conn, category_key="dev", description="x", started_at=started)
        set_timer_target(conn, rec_id, target_at=target)
    with open_db() as conn:
        lines = _build_tick_lines(now, conn, bar_color="cyan", bar_style="solid")
    assert len(lines) == 2
    assert "30m" in lines[0]
    assert "%" in lines[1]


def test_active_session_line_english(isolated_db) -> None:
    from task_recorder_cui.i18n import set_lang

    now = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    set_lang("en")
    try:
        with open_db() as conn:
            line = _active_session_line(now, conn)
        assert line == "Active: none"
    finally:
        set_lang(None)
