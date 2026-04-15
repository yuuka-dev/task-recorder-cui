"""WSL2 環境でのパス変換ユーティリティ。

ユーザが Windows 形式のパス (C:\\...) を入力しても内部では POSIX パスで統一する。
powershell.exe に渡す際は逆方向の変換を行う。
"""

import re
import subprocess
from pathlib import Path

_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_UNC_RE = re.compile(r"^\\\\")


def is_windows_path(value: str) -> bool:
    """文字列が Windows スタイルのパスなら True。

    Args:
        value: 判定対象の文字列。

    Returns:
        'C:\\foo' や '\\\\wsl$\\...' のような Windows パスなら True、
        それ以外 ('/mnt/c/...', '/home/...', '~/...') は False。

    """
    return bool(_WINDOWS_DRIVE_RE.match(value) or _UNC_RE.match(value))


def normalize_user_path(value: str) -> Path:
    """ユーザ入力のパスを POSIX な Path に正規化する。

    Windows スタイルなら `wslpath -u` で変換、POSIX なら ~ 展開のみ行う。
    どちらも最終的にファイルの存在確認を行い、無ければ FileNotFoundError。

    Args:
        value: ユーザ入力のパス文字列。

    Returns:
        存在確認済みの Path (絶対パス)。

    Raises:
        FileNotFoundError: 変換後のパスが存在しない。
        RuntimeError: wslpath が失敗した (非 WSL 環境など)。

    """
    if is_windows_path(value):
        result = subprocess.run(
            ["wslpath", "-u", value],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"wslpath に失敗しました: {result.stderr.strip() or 'unknown error'}"
            )
        path = Path(result.stdout.strip())
    else:
        path = Path(value).expanduser()

    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"パスが存在しません: {path}")
    return path


def to_windows_path(path: Path) -> str:
    """POSIX な Path を Windows 形式の文字列に変換する (wslpath -w)。

    powershell.exe に渡すとき用。失敗時は RuntimeError。

    Args:
        path: 変換元 Path。

    Returns:
        'C:\\...' 形式の Windows パス文字列。

    Raises:
        RuntimeError: wslpath が失敗した場合。

    """
    result = subprocess.run(
        ["wslpath", "-w", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"wslpath に失敗しました: {result.stderr.strip() or 'unknown error'}"
        )
    return result.stdout.strip()
