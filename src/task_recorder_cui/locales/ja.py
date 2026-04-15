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
    "再有効化: {key} → '{display}' (以前 archived だったカテゴリを復帰、display_name を上書き)"
)
CAT_ALREADY_ARCHIVED = "'{key}' は既にアーカイブ済みです"
CAT_ARCHIVED = "アーカイブ: {key} ('{display}')"
CAT_ALREADY_ACTIVE = "'{key}' は既に有効です"
CAT_RESTORED = "復帰: {key} ('{display}')"
CAT_RENAMED = "変更: {key} '{old_display}' → '{new_display}'"

# === Validate ===
VALIDATE_KEY_EMPTY = "category key は空にできません"
VALIDATE_KEY_INVALID_CHARS = (
    "category key must match [a-z0-9_]+ (ASCII lowercase/digit/underscore): {key!r}"
)

# === Summary / 参照系共通 ===
SUMMARY_NO_RECORDS = "記録なし"
SUMMARY_TOTAL = "合計: {total}"
SUMMARY_TOTAL_WITH_ACTIVE = "合計: {total} (記録中含む)"
SUMMARY_DAILY_AVG_SUFFIX = "/ 日平均 {avg}"
SUMMARY_BREAKDOWN_TITLE = "日別"
SUMMARY_BREAKDOWN_COL_DATE = "日付"
SUMMARY_BREAKDOWN_COL_TOTAL = "合計"
SUMMARY_RECORDING_TAG = "記録中 {elapsed}"

# === Today ===
TODAY_HEADER = "{date_iso} ({weekday})"

# === Week ===
WEEK_LABEL_ROLLING = "直近7日"
WEEK_LABEL_CALENDAR = "今週"
WEEK_HEADER = "{label} ({from_date} 〜 {to_date})"

# === Month ===
MONTH_LABEL_ROLLING = "直近30日"
MONTH_LABEL_CALENDAR = "今月"
MONTH_HEADER = "{label} ({from_date} 〜 {to_date})"

# === Range ===
RANGE_HEADER = "期間指定 ({from_date} 〜 {to_date})"
RANGE_INVALID_FROM = "--from の日付形式が不正です (YYYY-MM-DD): {value!r}"
RANGE_INVALID_TO = "--to の日付形式が不正です (YYYY-MM-DD): {value!r}"
RANGE_FROM_AFTER_TO = "--from ({from_date}) は --to ({to_date}) 以前である必要があります"

# === All ===
ALL_TITLE = "全累計"
ALL_HEADER_SINCE = "全累計 ({from_date} 以降)"

# === Menu ===
MENU_TITLE = "tsk - task recorder"
MENU_ACTIVE_LINE = "現在: [{display}] {description} ({elapsed}経過)"
MENU_ACTIVE_NONE = "現在: 記録なし"
MENU_RECENT_LABEL = "直近:"
MENU_PROMPT_ACTION = "操作を選んでください"
MENU_CHOICE_START = "開始"
MENU_CHOICE_STOP = "停止"
MENU_CHOICE_STOP_DISABLED = "(記録中のセッションがありません)"
MENU_CHOICE_TODAY = "今日の一覧"
MENU_CHOICE_WEEK = "週集計"
MENU_CHOICE_MONTH = "月集計"
MENU_CHOICE_CAT = "カテゴリ管理"
MENU_CHOICE_HELP = "ヘルプ (CLI コマンド一覧)"
MENU_CHOICE_QUIT = "終了"
MENU_PROMPT_CATEGORY = "カテゴリを選んでください"
MENU_PROMPT_DESCRIPTION = "何をしましたか (任意、空欄可)"
MENU_NO_ACTIVE_CATEGORIES = "有効なカテゴリがありません。先に『カテゴリ管理 → 追加』してください。"
MENU_NO_ACTIVE_CATEGORIES_SHORT = "active なカテゴリがありません"
MENU_NO_ARCHIVED_CATEGORIES = "archived なカテゴリがありません"
MENU_PROMPT_PRESS_ENTER = "[Enter で戻る]"
MENU_INTERRUPTED = "(中断しました)"
MENU_UNKNOWN_CHOICE = "(未知の選択肢: {choice})"
MENU_CAT_TITLE = "カテゴリ管理"
MENU_CAT_CHOICE_LIST = "一覧表示"
MENU_CAT_CHOICE_ADD = "追加"
MENU_CAT_CHOICE_REMOVE = "アーカイブ"
MENU_CAT_CHOICE_RESTORE = "アーカイブから復帰"
MENU_CAT_CHOICE_RENAME = "表示名を変更"
MENU_CAT_CHOICE_BACK = "← 戻る"
MENU_CAT_PROMPT_NEW_KEY = "新しいカテゴリキー (ASCII 英小文字・数字・_)"
MENU_CAT_PROMPT_DISPLAY = "表示名"
MENU_CAT_PROMPT_REMOVE = "アーカイブするカテゴリを選んでください"
MENU_CAT_PROMPT_RESTORE = "復帰させるカテゴリを選んでください"
MENU_CAT_PROMPT_RENAME = "表示名を変更するカテゴリを選んでください"
MENU_CAT_PROMPT_NEW_DISPLAY = "新しい表示名"
MENU_CAT_CONFIRM_REMOVE = "{display} ({key}) をアーカイブしますか？"

# === Errors ===
ERROR_INVALID_KEY = "カテゴリ key が不正です: {key}"
