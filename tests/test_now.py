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
