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


def test_all_english(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from task_recorder_cui.i18n import set_lang

    try:
        rc = main(["--lang", "en", "all"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "All time" in out
        assert "No records" in out
    finally:
        set_lang(None)
