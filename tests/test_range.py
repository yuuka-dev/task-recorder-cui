"""tsk range コマンドのテスト。"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from task_recorder_cui.cli import main
from task_recorder_cui.db import open_db
from task_recorder_cui.repo import insert_record


def _local_noon() -> datetime:
    """テスト用: 今日のローカル正午 (tz付き)。日付境界のテスト不安定を防ぐ。"""
    return datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)


def test_任意期間の集計を表示(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    noon = _local_noon()
    with open_db() as conn, conn:
        insert_record(
            conn,
            category_key="dev",
            description=None,
            started_at=noon - timedelta(minutes=120),
            ended_at=noon,
            duration_minutes=120,
        )
    capsys.readouterr()

    today = noon.date().isoformat()
    exit_code = main(["range", "--from", today, "--to", today])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "期間指定" in out
    assert "2h00m" in out


def test_不正な日付形式はexit1(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["range", "--from", "2026/04/01", "--to", "2026-04-14"])
    assert exit_code == 1
    assert "形式が不正" in capsys.readouterr().err


def test_from_がto_より後ならexit1(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["range", "--from", "2026-04-14", "--to", "2026-04-01"])
    assert exit_code == 1
    assert "以前" in capsys.readouterr().err


def test_from_to_必須(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as ex:
        main(["range"])
    assert ex.value.code == 2


def test_range_english(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from task_recorder_cui.i18n import set_lang

    try:
        rc = main(["--lang", "en", "range", "--from", "2026-04-14", "--to", "2026-04-01"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "must be on or before" in err
    finally:
        set_lang(None)
