"""tsk today コマンドのテスト。"""

from pathlib import Path

import pytest

from task_recorder_cui.cli import main


def test_記録なしでも正常終了(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["today"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "記録なし" in out


def test_addした記録がtimelineとsummaryに出る(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["add", "study", "45", "ABC"])
    main(["add", "game", "30", "HOI4"])
    capsys.readouterr()

    exit_code = main(["today"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "学習" in out
    assert "ゲーム" in out
    assert "ABC" in out
    assert "HOI4" in out
    assert "合計" in out


def test_記録中セッションは記録中マークで表示(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["start", "dev", "実装中"])
    capsys.readouterr()

    exit_code = main(["today"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "記録中" in out
    assert "実装中" in out
