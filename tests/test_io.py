"""io.py のテスト。

rich のマークアップをユーザ入力と混ぜた際に、意図しない解釈が起きないことを確認する。
"""

import pytest

from task_recorder_cui import io


def test_print_warningはブラケットをエスケープする(capsys: pytest.CaptureFixture[str]) -> None:
    io.print_warning("カテゴリ [game] が見つかりません")
    err = capsys.readouterr().err
    assert "[game]" in err


def test_print_errorはブラケットをエスケープする(capsys: pytest.CaptureFixture[str]) -> None:
    io.print_error("key [bold]abc[/bold] は不正です")
    err = capsys.readouterr().err
    assert "[bold]abc[/bold]" in err


def test_print_lineは標準出力に出る(capsys: pytest.CaptureFixture[str]) -> None:
    io.print_line("hello")
    out = capsys.readouterr().out
    assert "hello" in out
