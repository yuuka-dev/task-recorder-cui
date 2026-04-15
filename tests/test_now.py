"""tsk now コマンドのテスト。"""

from pathlib import Path

import pytest

from task_recorder_cui.cli import main


def test_記録中セッションを経過時間付きで表示(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["start", "dev", "ObatLog"])
    capsys.readouterr()

    exit_code = main(["now"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "現在" in out
    assert "ObatLog" in out
    assert "経過" in out


def test_記録中セッションが無くてもexit0(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["now"])
    assert exit_code == 0
    assert "記録中" in capsys.readouterr().out


def test_now_shows_timer_remaining(isolated_db, capsys: pytest.CaptureFixture[str]) -> None:
    """タイマー設定済の now は残り時間を表示する。"""
    from datetime import timedelta

    from task_recorder_cui.commands import now as now_cmd
    from task_recorder_cui.db import open_db
    from task_recorder_cui.repo import insert_record, set_timer_target
    from task_recorder_cui.utils.time import now_utc

    with open_db() as conn, conn:
        started = now_utc()
        rec_id = insert_record(conn, category_key="dev", description="t", started_at=started)
        set_timer_target(conn, rec_id, target_at=started + timedelta(minutes=45))

    rc = now_cmd.run()
    assert rc == 0
    out = capsys.readouterr().out
    assert "タイマー" in out
    assert "44m" in out or "45m" in out


def test_now_no_timer_hides_timer_line(isolated_db, capsys: pytest.CaptureFixture[str]) -> None:
    from task_recorder_cui.commands import now as now_cmd
    from task_recorder_cui.db import open_db
    from task_recorder_cui.repo import insert_record
    from task_recorder_cui.utils.time import now_utc

    with open_db() as conn, conn:
        insert_record(conn, category_key="dev", description="t", started_at=now_utc())
    rc = now_cmd.run()
    assert rc == 0
    out = capsys.readouterr().out
    assert "タイマー" not in out


def test_now_english(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from task_recorder_cui.i18n import set_lang

    try:
        rc = main(["--lang", "en", "now"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No active session" in out
    finally:
        set_lang(None)
