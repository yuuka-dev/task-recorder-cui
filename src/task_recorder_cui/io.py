"""出力用の薄いラッパ層。

将来のカラー化/i18nのため、print直書きではなくこの層を経由する。
"""

from rich.console import Console

_console = Console(highlight=False)
_err_console = Console(stderr=True, highlight=False)


def print_line(msg: str = "") -> None:
    """通常の標準出力に1行出力する。"""
    _console.print(msg)


def print_info(msg: str) -> None:
    """情報メッセージ (通常色)。"""
    _console.print(msg)


def print_warning(msg: str) -> None:
    """警告メッセージ (黄色) を標準エラー出力に。"""
    _err_console.print(f"[yellow]{msg}[/yellow]")


def print_error(msg: str) -> None:
    """エラーメッセージ (赤) を標準エラー出力に。"""
    _err_console.print(f"[red]{msg}[/red]")
