"""utils/time.py のテスト。"""

from datetime import UTC, datetime

import pytest

from task_recorder_cui.utils.time import (
    format_duration,
    from_iso,
    now_local,
    now_utc,
    to_iso,
)


class TestFormatDuration:
    """format_duration の整形ロジックを検証する。"""

    def test_0分は0mになる(self) -> None:
        assert format_duration(0) == "0m"

    def test_1時間未満は分のみ表示(self) -> None:
        assert format_duration(45) == "45m"

    def test_1時間ちょうどは1h00m(self) -> None:
        assert format_duration(60) == "1h00m"

    def test_1時間30分は1h30m(self) -> None:
        assert format_duration(90) == "1h30m"

    def test_分がゼロ埋めされる(self) -> None:
        assert format_duration(242) == "4h02m"

    def test_負の値はValueError(self) -> None:
        with pytest.raises(ValueError):
            format_duration(-1)


class TestIsoConversion:
    """ISO8601文字列とdatetimeの相互変換。"""

    def test_tz付きdatetimeをISO8601化できる(self) -> None:
        dt = datetime(2026, 4, 14, 12, 0, 0, tzinfo=UTC)
        assert to_iso(dt) == "2026-04-14T12:00:00+00:00"

    def test_naiveなdatetimeはValueError(self) -> None:
        dt = datetime(2026, 4, 14, 12, 0, 0)
        with pytest.raises(ValueError):
            to_iso(dt)

    def test_ISO8601からtz付きdatetimeに戻せる(self) -> None:
        s = "2026-04-14T12:00:00+00:00"
        dt = from_iso(s)
        assert dt == datetime(2026, 4, 14, 12, 0, 0, tzinfo=UTC)
        assert dt.tzinfo is not None


class TestNow:
    """現在時刻取得関数。"""

    def test_now_utcはUTCタイムゾーン(self) -> None:
        dt = now_utc()
        assert dt.tzinfo == UTC

    def test_now_localはtz付き(self) -> None:
        dt = now_local()
        assert dt.tzinfo is not None
