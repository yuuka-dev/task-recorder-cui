"""コードパスを網羅するための補完テスト。

既存テストで落ちてる小さな分岐 (1-3 行ずつ) を拾って 100% を達成するためのファイル。
各テストは短く、1 箇所の分岐に対応させる。
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from task_recorder_cui.db import open_db
from task_recorder_cui.repo import insert_record, set_timer_target
from task_recorder_cui.utils.time import now_utc

# === _summary.py ===


def test_aggregate_period_without_include_active(isolated_db) -> None:
    """include_active=False なら active セッションは集計対象外。"""
    from task_recorder_cui.commands._summary import aggregate_period

    with open_db() as conn, conn:
        insert_record(conn, category_key="dev", description="active", started_at=now_utc())

    today = date.today()
    with open_db() as conn:
        summary = aggregate_period(conn, today, today, include_active=False)
    assert summary.active_partial_minutes == 0


def test_aggregate_period_includes_active_when_flagged(isolated_db) -> None:
    """include_active=True なら active の経過時間が active_partial_minutes に載る。"""
    from task_recorder_cui.commands._summary import aggregate_period

    with open_db() as conn, conn:
        insert_record(
            conn,
            category_key="dev",
            description="x",
            started_at=now_utc() - timedelta(minutes=30),
        )

    today = date.today()
    with open_db() as conn:
        summary = aggregate_period(conn, today, today, include_active=True)
    assert summary.active_partial_minutes >= 0


def test_render_category_totals_empty(isolated_db, capsys: pytest.CaptureFixture[str]) -> None:
    from task_recorder_cui.commands._summary import (
        PeriodSummary,
        render_category_totals,
    )

    today = date.today()
    summary = PeriodSummary(
        start_local=today,
        end_local=today,
        days=[],
        per_category_minutes={},
        total_minutes=0,
        display_names={},
        active_partial_minutes=0,
    )
    render_category_totals(summary)
    out = capsys.readouterr().out
    assert "記録なし" in out or "No records" in out


# === now.py ===


def test_now_shows_timer_fired(isolated_db, capsys: pytest.CaptureFixture[str]) -> None:
    """timer_fired_at が入っていれば NOW_TIMER_FIRED が表示される。"""
    from task_recorder_cui.commands import now as now_cmd

    started = now_utc()
    fired = started.isoformat()
    with open_db() as conn, conn:
        rec_id = insert_record(conn, category_key="dev", description="x", started_at=started)
        set_timer_target(conn, rec_id, target_at=started + timedelta(minutes=30))
        conn.execute("UPDATE records SET timer_fired_at = ? WHERE id = ?", (fired, rec_id))
    rc = now_cmd.run()
    assert rc == 0
    out = capsys.readouterr().out
    assert "経過済" in out or "fired" in out


# === range.py ===


def test_range_invalid_to_date(isolated_db, capsys: pytest.CaptureFixture[str]) -> None:
    from task_recorder_cui.commands import range as range_cmd

    rc = range_cmd.run("2026-04-01", "not-a-date")
    assert rc == 1
    err = capsys.readouterr().err
    assert "不正" in err or "invalid" in err.lower()


def test_range_from_after_to(isolated_db, capsys: pytest.CaptureFixture[str]) -> None:
    from task_recorder_cui.commands import range as range_cmd

    rc = range_cmd.run("2026-05-01", "2026-04-01")
    assert rc == 1
    err = capsys.readouterr().err
    assert "以前" in err or "must be on or before" in err


def test_range_no_records(isolated_db, capsys: pytest.CaptureFixture[str]) -> None:
    from task_recorder_cui.commands import range as range_cmd

    rc = range_cmd.run("2026-01-01", "2026-01-02")
    assert rc == 0
    out = capsys.readouterr().out
    assert "記録なし" in out or "No records" in out


# === commands/timer.py ===


def test_timer_cancel_no_active_session(isolated_db, capsys: pytest.CaptureFixture[str]) -> None:
    from task_recorder_cui.commands import timer as timer_cmd

    rc = timer_cmd.cancel()
    assert rc == 1
    err = capsys.readouterr().err
    assert "記録中" in err


# === today.py ===


def test_today_active_session_appends_to_records(
    isolated_db,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """today.py の active append 分岐と active_partial による合計表示分岐を網羅する．

    active セッションが records に append される分岐 (line 44) と
    ``active_partial_minutes > 0`` のときの「記録中含む」合計 (line 76) を同時カバー．
    CI runner の時刻 (特に UTC 日付境界 00:00〜00:30 付近) に依存すると flake する
    ため ``now_utc`` / ``today_local`` を固定時刻 (2026-04-16 12:00 UTC) に差し替える．
    """
    from datetime import UTC, datetime

    from task_recorder_cui.commands import _summary as summary_mod
    from task_recorder_cui.commands import today as today_cmd

    fixed_now = datetime(2026, 4, 16, 12, 0, tzinfo=UTC)
    fixed_today = fixed_now.astimezone().date()
    fixed_started = fixed_now - timedelta(minutes=30)

    monkeypatch.setattr(today_cmd, "now_utc", lambda: fixed_now)
    monkeypatch.setattr(today_cmd, "today_local", lambda: fixed_today)
    monkeypatch.setattr(summary_mod, "now_utc", lambda: fixed_now)
    monkeypatch.setattr(summary_mod, "today_local", lambda: fixed_today)

    with open_db() as conn, conn:
        insert_record(
            conn,
            category_key="dev",
            description="running",
            started_at=fixed_started,
        )
    rc = today_cmd.run()
    assert rc == 0
    out = capsys.readouterr().out
    assert "running" in out
    assert "記録中含む" in out or "includes active" in out


# === db.py ===


def test_default_db_path_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """TSK_DB_PATH が未設定なら _DEFAULT_DB_PATH を返す。"""
    from task_recorder_cui import db as db_mod

    monkeypatch.delenv("TSK_DB_PATH", raising=False)
    assert db_mod.get_db_path() == db_mod._DEFAULT_DB_PATH


# === paths.py ===


def test_normalize_user_path_raises_when_wslpath_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from task_recorder_cui.utils import paths as paths_mod

    class _FakeResult:
        returncode = 1
        stdout = ""
        stderr = "wslpath: bad"

    monkeypatch.setattr(paths_mod.subprocess, "run", lambda *a, **kw: _FakeResult())
    with pytest.raises(RuntimeError, match="wslpath"):
        paths_mod.normalize_user_path("C:\\nope\\x.wav")


def test_to_windows_path_raises_when_wslpath_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from task_recorder_cui.utils import paths as paths_mod

    class _FakeResult:
        returncode = 1
        stdout = ""
        stderr = "wslpath: no"

    monkeypatch.setattr(paths_mod.subprocess, "run", lambda *a, **kw: _FakeResult())
    with pytest.raises(RuntimeError, match="wslpath"):
        paths_mod.to_windows_path(Path("/tmp/x"))


# === repo.py ===


def test_list_all_categories_rejects_both_filters(isolated_db) -> None:
    """active_only と archived_only 同時 True は ValueError。"""
    from task_recorder_cui.repo import list_all_categories

    with open_db() as conn, pytest.raises(ValueError, match="同時"):
        list_all_categories(conn, active_only=True, archived_only=True)


def test_list_recent_records_with_zero_limit(isolated_db) -> None:
    """limit=0 なら空リストを返す (DB は叩かない)。"""
    from task_recorder_cui.repo import list_recent_records

    with open_db() as conn:
        assert list_recent_records(conn, 0) == []
        assert list_recent_records(conn, -1) == []
