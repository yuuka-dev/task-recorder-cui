"""tsk month コマンドのテスト。"""

from pathlib import Path

import pytest

from task_recorder_cui.cli import main


def test_記録なしでも正常終了(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["month"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "直近30日" in out
    assert "記録なし" in out


def test_rollingでaddした記録が含まれる(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["add", "game", "90"])
    capsys.readouterr()

    exit_code = main(["month"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "直近30日" in out
    assert "ゲーム" in out
    assert "1h30m" in out


def test_calendarフラグで今月表記になる(
    isolated_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["add", "study", "20"])
    capsys.readouterr()

    exit_code = main(["month", "--calendar"])
    assert exit_code == 0
    assert "今月" in capsys.readouterr().out


def test_month_english(isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from task_recorder_cui.i18n import set_lang

    try:
        rc = main(["--lang", "en", "month"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Last 30 days" in out
    finally:
        set_lang(None)
