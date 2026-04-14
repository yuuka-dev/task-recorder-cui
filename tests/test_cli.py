"""cli.py のテスト。

Phase 2 時点ではサブコマンドのディスパッチとエントリ動作のみを検証する。
実ロジックは Phase 3-5 で追加されるため、ここでは「未実装メッセージが出る」
「exit code が正しい」を確認する。
"""

import pytest

from task_recorder_cui import __version__
from task_recorder_cui.cli import build_parser, main


def test_parserはversionを返す(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as ex:
        parser.parse_args(["--version"])
    assert ex.value.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_helpは正常終了(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as ex:
        main(["--help"])
    assert ex.value.code == 0
    assert "tsk" in capsys.readouterr().out


def test_サブコマンド無しはメニュースタブ(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])
    assert exit_code == 0
    assert "Phase 6" in capsys.readouterr().out


def test_記録系サブコマンドはPhase3スタブ(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["start", "game", "HOI4"])
    assert exit_code == 0
    assert "Phase 3" in capsys.readouterr().out


def test_参照系サブコマンドはPhase4スタブ(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["today"])
    assert exit_code == 0
    assert "Phase 4" in capsys.readouterr().out


def test_cat_addはPhase5スタブ(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["cat", "add", "reading", "読書"])
    assert exit_code == 0
    assert "Phase 5" in capsys.readouterr().out


def test_未知コマンドはexit2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as ex:
        main(["no_such_command"])
    assert ex.value.code == 2


def test_start引数不足はexit2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as ex:
        main(["start"])  # category_key 必須
    assert ex.value.code == 2


def test_add_minutesは整数必須(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as ex:
        main(["add", "study", "abc"])  # 整数でない
    assert ex.value.code == 2
