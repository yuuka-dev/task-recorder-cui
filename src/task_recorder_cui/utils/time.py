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
    """tz付きdatetimeをUTC正規化したISO8601文字列に変換する。

    DB内のタイムスタンプを常にUTC表記で統一することで、
    SQLの文字列大小比較・ORDER BYが正しく機能することを保証する。

    Args:
        dt: タイムゾーン情報を持つdatetime。

    Returns:
        UTC正規化されたISO8601形式の文字列 (例: '2026-04-14T12:00:00+00:00')。

    Raises:
        ValueError: naiveなdatetimeが渡された場合。

    """
    if dt.tzinfo is None:
        raise ValueError("naive datetime is not allowed; use timezone-aware datetime")
    return dt.astimezone(UTC).isoformat()


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


def humanize_relative(when: datetime, now: datetime) -> str:
    """ある時刻と現在時刻の差分を「たった今/N分前/N時間前/昨日/N日前」形式で返す。

    Args:
        when: 過去の時刻 (tz付き)。
        now: 基準とする現在時刻 (tz付き)。

    Returns:
        人間向けの相対時刻文字列。

    Raises:
        ValueError: いずれかが naive な datetime の場合。

    """
    if when.tzinfo is None or now.tzinfo is None:
        raise ValueError("naive datetime is not allowed; use timezone-aware datetime")
    delta = now - when
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return "たった今"
    if total_seconds < 60 * 60:
        return f"{total_seconds // 60}分前"
    if total_seconds < 24 * 60 * 60:
        return f"{total_seconds // 3600}時間前"
    if total_seconds < 48 * 60 * 60:
        return "昨日"
    return f"{delta.days}日前"


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
