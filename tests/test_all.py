"""tsk all コマンドのテスト。"""

from pathlib import Path

import pytest

from task_recorder_cui.cli import main


def test_記録なしでも正常終了(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["all"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "全累計" in out
    assert "記録なし" in out


def test_全累計が表示される(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["add", "study", "30"])
    main(["add", "dev", "60"])
    capsys.readouterr()

    exit_code = main(["all"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "全累計" in out
    assert "学習" in out
    assert "開発" in out
    assert "1h30m" in out  # 合計 90分
