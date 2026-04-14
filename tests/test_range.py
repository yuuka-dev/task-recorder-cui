"""tsk range コマンドのテスト。"""

from datetime import date
from pathlib import Path

import pytest

from task_recorder_cui.cli import main


def test_任意期間の集計を表示(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["add", "dev", "120"])
    capsys.readouterr()

    today = date.today().isoformat()
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
