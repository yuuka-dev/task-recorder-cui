"""cli.py のディスパッチとエントリ動作のテスト。

記録系コマンド (start/stop/now/add) の実ロジックは tests/test_start.py 等で
検証するため、本ファイルでは argparse の振る舞いと未実装スタブの応答を確認する。
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


def test_main_no_command_calls_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"n": 0}

    def fake_run() -> int:
        called["n"] += 1
        return 0

    monkeypatch.setattr("task_recorder_cui.menu.run", fake_run)

    rc = main([])
    assert rc == 0
    assert called["n"] == 1


def test_catサブコマンド無しはexit2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as ex:
        main(["cat"])
    assert ex.value.code == 2


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
