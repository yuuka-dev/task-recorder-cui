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

# === Add ===
ADD_SUCCESS = "追加: [{display}]{detail} ({started_hm}-{ended_hm}, {duration})"
ADD_INVALID_MINUTES = "minutes は1以上である必要があります: {minutes}"

# === Now ===
NOW_ACTIVE = "現在: [{display}]{detail} ({elapsed}経過)"
NOW_NONE = "記録中のセッションはありません"
NOW_STARTED = "開始: {started_hm}"
NOW_TIMER_FIRED = "  タイマー: 経過済"
NOW_TIMER_REMAINING = "  タイマー: 残り {remaining}"

# === Category ===
CAT_LIST_TABLE_TITLE = "カテゴリ"
CAT_COL_KEY = "key"
CAT_COL_DISPLAY_NAME = "表示名"
CAT_COL_ARCHIVED = "archived"
CAT_LIST_EMPTY = "カテゴリがありません"
CAT_LIST_EMPTY_ACTIVE = "active カテゴリはありません"
CAT_LIST_EMPTY_ARCHIVED = "archived カテゴリはありません"
CAT_DISPLAY_NAME_EMPTY = "display_name は空にできません"
CAT_NEW_DISPLAY_NAME_EMPTY = "新しい display_name は空にできません"
CAT_ALREADY_EXISTS = "カテゴリ '{key}' は既に存在します (display_name='{display}')"
CAT_NOT_FOUND = "カテゴリ '{key}' が存在しません"
CAT_ADDED = "追加: {key} → '{display}'"
CAT_REACTIVATED = (
    "再有効化: {key} → '{display}' "
    "(以前 archived だったカテゴリを復帰、display_name を上書き)"
)
CAT_ALREADY_ARCHIVED = "'{key}' は既にアーカイブ済みです"
CAT_ARCHIVED = "アーカイブ: {key} ('{display}')"
CAT_ALREADY_ACTIVE = "'{key}' は既に有効です"
CAT_RESTORED = "復帰: {key} ('{display}')"
CAT_RENAMED = "変更: {key} '{old_display}' → '{new_display}'"

# === Validate ===
VALIDATE_KEY_EMPTY = "category key は空にできません"
VALIDATE_KEY_INVALID_CHARS = (
    "category key must match [a-z0-9_]+ "
    "(ASCII lowercase/digit/underscore): {key!r}"
)

# === Errors ===
ERROR_INVALID_KEY = "カテゴリ key が不正です: {key}"
