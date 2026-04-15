"""tsk timer set / cancel サブコマンドのテスト。"""

import pytest

from task_recorder_cui.commands import timer as timer_cmd
from task_recorder_cui.db import open_db
from task_recorder_cui.repo import find_active_record, insert_record
from task_recorder_cui.utils.time import now_utc


@pytest.fixture()
def mock_spawn(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """spawn_daemon をモックして呼び出し record_id を収集する。"""
    calls: list[int] = []

    def fake_spawn(rid: int) -> None:
        calls.append(rid)

    monkeypatch.setattr(
        "task_recorder_cui.commands.timer.spawn_daemon", fake_spawn
    )
    return calls


def test_set_no_active_session_errors(
    isolated_db, mock_spawn, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = timer_cmd.set_("30m")
    assert rc == 1
    assert "記録中" in capsys.readouterr().err


def test_set_writes_target_and_spawns_daemon(isolated_db, mock_spawn) -> None:
    with open_db() as conn, conn:
        rec_id = insert_record(
            conn, category_key="dev", description="x", started_at=now_utc()
        )
    rc = timer_cmd.set_("30m")
    assert rc == 0
    with open_db() as conn:
        rec = find_active_record(conn)
        assert rec is not None
        assert rec.timer_target_at is not None
    assert mock_spawn == [rec_id]


def test_set_invalid_spec_errors(
    isolated_db, mock_spawn, capsys: pytest.CaptureFixture[str]
) -> None:
    with open_db() as conn:
        insert_record(
            conn, category_key="dev", description="x", started_at=now_utc()
        )
    rc = timer_cmd.set_("bogus")
    assert rc == 1
    assert "不正" in capsys.readouterr().err


def test_cancel_clears_target(isolated_db, mock_spawn) -> None:
    with open_db() as conn, conn:
        insert_record(
            conn, category_key="dev", description="x", started_at=now_utc()
        )
    timer_cmd.set_("30m")
    rc = timer_cmd.cancel()
    assert rc == 0
    with open_db() as conn:
        rec = find_active_record(conn)
        assert rec is not None
        assert rec.timer_target_at is None


def test_cancel_no_timer_errors(
    isolated_db, mock_spawn, capsys: pytest.CaptureFixture[str]
) -> None:
    with open_db() as conn, conn:
        insert_record(
            conn, category_key="dev", description="x", started_at=now_utc()
        )
    rc = timer_cmd.cancel()
    assert rc == 1
    assert "タイマー" in capsys.readouterr().err
