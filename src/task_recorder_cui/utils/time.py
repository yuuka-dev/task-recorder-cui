"""時刻処理のユーティリティ。

時刻は全て timezone-aware な datetime で扱い、DBにはISO8601文字列で保存する。
表示時にローカルタイムへ変換する方針。
"""

from datetime import UTC, datetime


def now_utc() -> datetime:
    """現在時刻をUTCで返す。

    Returns:
        tz=UTC の現在時刻。

    """
    return datetime.now(UTC)


def now_local() -> datetime:
    """現在時刻をシステムのローカルタイムゾーンで返す。

    Returns:
        tz付きの現在時刻 (システムのlocal tz)。

    """
    return datetime.now().astimezone()


def to_iso(dt: datetime) -> str:
    """tz付きdatetimeをISO8601文字列に変換する。

    Args:
        dt: タイムゾーン情報を持つdatetime。

    Returns:
        ISO8601形式の文字列 (例: '2026-04-14T12:00:00+00:00')。

    Raises:
        ValueError: naiveなdatetimeが渡された場合。

    """
    if dt.tzinfo is None:
        raise ValueError("naive datetime is not allowed; use timezone-aware datetime")
    return dt.isoformat()


def from_iso(s: str) -> datetime:
    """ISO8601文字列をtz付きdatetimeに変換する。

    DBへの書き込みは必ずtz付き文字列で行う方針 (`to_iso` を通す) のため、
    tz情報を持たない文字列が来た場合は暗黙変換せず `ValueError` を投げる。

    Args:
        s: ISO8601形式の文字列 (tz情報必須)。

    Returns:
        tz付きdatetime。

    Raises:
        ValueError: tz情報を持たないISO8601文字列の場合、または不正な形式の場合。

    """
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise ValueError(f"ISO8601文字列にtz情報がありません: {s!r}")
    return dt


def format_duration(minutes: int) -> str:
    """分を '2h30m' 形式に整形する。

    1時間未満は分のみ (例: '45m')、1時間以上は時間+分ゼロ埋め2桁 (例: '1h30m', '4h02m')。

    Args:
        minutes: 非負の整数。

    Returns:
        整形された文字列。

    Raises:
        ValueError: minutes が負の場合。

    """
    if minutes < 0:
        raise ValueError(f"minutes must be non-negative: {minutes}")
    hours, mins = divmod(minutes, 60)
    if hours == 0:
        return f"{mins}m"
    return f"{hours}h{mins:02d}m"
