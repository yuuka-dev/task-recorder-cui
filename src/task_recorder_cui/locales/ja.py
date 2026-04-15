"""日本語メッセージカタログ。

キーは UPPER_SNAKE_CASE で統一。値は str.format() 互換のプレースホルダ
({name}) を含んでよい。UI からは `i18n.t(key, **fmt)` 経由で参照する。
"""

# === Session ===
SESSION_NONE = "現在: 記録なし"

# === Start ===
START_SUCCESS = "開始: [{display}]{detail} ({started_hm}-){timer_note}"
START_TIMER_NOTE = " [タイマー {duration}]"
START_CATEGORY_NOT_FOUND = (
    "カテゴリ '{key}' が存在しません。`tsk cat list` で一覧を確認してください"
)
START_CATEGORY_ARCHIVED = (
    "カテゴリ '{key}' はアーカイブ済みです。 "
    "`tsk cat restore {key}` または "
    "`tsk cat add {key} <display_name>` で復帰させてください"
)
START_ALREADY_ACTIVE = "既に記録中のセッションがあります: [{display}]{detail} ({started_hm}-)"
START_HINT_STOP_FIRST = "先に `tsk stop` で停止してください"

# === Stop ===
STOP_NO_ACTIVE = "記録中のセッションはありません"
STOP_SUCCESS = "停止: [{display}]{detail} ({started_hm}-{ended_hm}, {duration})"

# === Errors ===
ERROR_INVALID_KEY = "カテゴリ key が不正です: {key}"
