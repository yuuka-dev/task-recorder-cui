"""tsk week コマンドのテスト。"""

from pathlib import Path

import pytest

from task_recorder_cui.cli import main


def test_記録なしでも正常終了(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["week"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "直近7日" in out
    assert "記録なし" in out


def test_rollingでaddした記録が含まれる(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["add", "study", "60", "数学"])
    capsys.readouterr()

    exit_code = main(["week"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "直近7日" in out
    assert "学習" in out
    assert "1h00m" in out
    assert "日平均" in out


def test_calendarフラグで今週表記になる(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["add", "dev", "30"])
    capsys.readouterr()

    exit_code = main(["week", "--calendar"])
    assert exit_code == 0
    assert "今週" in capsys.readouterr().out
