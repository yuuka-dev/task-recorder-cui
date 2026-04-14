"""データモデル (dataclass)。

DBの categories / records テーブルに対応。
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Category:
    """カテゴリ (集計単位)。

    Attributes:
        id: 主キー。
        key: 内部キー (ASCII英小文字+数字+_のみ)。
        display_name: 表示名 (日本語可)。
        created_at: 作成日時 (tz付き)。
        archived: アーカイブ済みなら True (メニューには出ないが集計には含まれる)。
    """

    id: int
    key: str
    display_name: str
    created_at: datetime
    archived: bool


@dataclass(frozen=True)
class Record:
    """時間記録1件。

    ended_at と duration_minutes が None の場合は記録中セッション。

    Attributes:
        id: 主キー。
        category_key: 参照するカテゴリのkey。
        description: 具体的な活動内容 (任意)。
        started_at: 開始時刻 (tz付き)。
        ended_at: 終了時刻 (記録中ならNone)。
        duration_minutes: 記録時間の分数 (記録中ならNone)。
    """

    id: int
    category_key: str
    description: str | None
    started_at: datetime
    ended_at: datetime | None
    duration_minutes: int | None
