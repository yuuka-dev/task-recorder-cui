"""タイマー機能の中核ロジック。

時刻パーサ、daemon プロセスの起動、音・デスクトップ通知の再生を集約する。
CLI / commands 層からはここだけを呼ぶ。
"""

import re

# 2h30m / 30m / 2h / 150 / 150m を許容
_TIMER_SPEC_RE = re.compile(r"^(?:(\d+)h)?(?:(\d+)m?)?$")


def parse_timer_spec(spec: str) -> int:
    """人間向けの時刻指定文字列を分に変換する。

    受理する書式:
        '2h30m' -> 150
        '30m'   -> 30
        '2h'    -> 120
        '150m'  -> 150
        '150'   -> 150 (数字だけなら分単位)

    Args:
        spec: ユーザ入力文字列。空白なし、小文字 h/m。

    Returns:
        分数 (1 以上の整数)。

    Raises:
        ValueError: 書式不一致、または 0 分以下の場合。

    """
    match = _TIMER_SPEC_RE.fullmatch(spec)
    if match is None or (match.group(1) is None and match.group(2) is None):
        raise ValueError(f"タイマー書式が不正です: {spec!r}")
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    total = hours * 60 + minutes
    if total < 1:
        raise ValueError(f"タイマーは 1 分以上を指定してください: {spec!r}")
    return total
