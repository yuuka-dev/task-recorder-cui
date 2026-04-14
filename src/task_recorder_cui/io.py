"""出力用の薄いラッパ層。

将来のカラー化/i18nのため、print直書きではなくこの層を経由する。
ユーザ入力 (カテゴリkey等) を埋め込む可能性があるため、rich のマークアップは
`escape()` で必ずエスケープする。
"""

from rich.console import Console
from rich.markup import escape
from rich.table import Table

_console = Console(highlight=False)
_err_console = Console(stderr=True, highlight=False)


def print_line(msg: str = "") -> None:
    """通常の標準出力に1行出力する (情報表示の共通エントリ)。"""
    _console.print(msg)


def print_table(table: Table) -> None:
    """rich.Table を標準出力に描画する (CJK幅の自動調整に対応)。"""
    _console.print(table)


def print_warning(msg: str) -> None:
    """警告メッセージ (黄色) を標準エラー出力に。"""
    _err_console.print(f"[yellow]{escape(msg)}[/yellow]")


def print_error(msg: str) -> None:
    """エラーメッセージ (赤) を標準エラー出力に。"""
    _err_console.print(f"[red]{escape(msg)}[/red]")
