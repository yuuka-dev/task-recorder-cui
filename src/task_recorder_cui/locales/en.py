"""English message catalog. Keys must match locales/ja.py."""

SESSION_NONE = "No active session"

# === Start ===
START_SUCCESS = "Started: [{display}]{detail} ({started_hm}-){timer_note}"
START_TIMER_NOTE = " [timer {duration}]"
START_CATEGORY_NOT_FOUND = (
    "Category '{key}' does not exist. Run `tsk cat list` to see available categories"
)
START_CATEGORY_ARCHIVED = (
    "Category '{key}' is archived. "
    "Use `tsk cat restore {key}` or "
    "`tsk cat add {key} <display_name>` to reactivate it"
)
START_ALREADY_ACTIVE = "A session is already active: [{display}]{detail} ({started_hm}-)"
START_HINT_STOP_FIRST = "Stop it first with `tsk stop`"

# === Stop ===
STOP_NO_ACTIVE = "No active session"
STOP_SUCCESS = "Stopped: [{display}]{detail} ({started_hm}-{ended_hm}, {duration})"

# === Add ===
ADD_SUCCESS = "Added: [{display}]{detail} ({started_hm}-{ended_hm}, {duration})"
ADD_INVALID_MINUTES = "minutes must be >= 1: {minutes}"

# === Now ===
NOW_ACTIVE = "Active: [{display}]{detail} ({elapsed})"
NOW_NONE = "No active session"
NOW_STARTED = "Started at: {started_hm}"
NOW_TIMER_FIRED = "  Timer: fired"
NOW_TIMER_REMAINING = "  Timer: {remaining} remaining"

# === Category ===
CAT_LIST_TABLE_TITLE = "Categories"
CAT_COL_KEY = "key"
CAT_COL_DISPLAY_NAME = "display_name"
CAT_COL_ARCHIVED = "archived"
CAT_LIST_EMPTY = "No categories"
CAT_LIST_EMPTY_ACTIVE = "No active categories"
CAT_LIST_EMPTY_ARCHIVED = "No archived categories"
CAT_DISPLAY_NAME_EMPTY = "display_name must not be empty"
CAT_NEW_DISPLAY_NAME_EMPTY = "new display_name must not be empty"
CAT_ALREADY_EXISTS = "Category '{key}' already exists (display_name='{display}')"
CAT_NOT_FOUND = "Category '{key}' does not exist"
CAT_ADDED = "Added: {key} -> '{display}'"
CAT_REACTIVATED = (
    "Reactivated: {key} -> '{display}' (restored from archive, display_name overwritten)"
)
CAT_ALREADY_ARCHIVED = "'{key}' is already archived"
CAT_ARCHIVED = "Archived: {key} ('{display}')"
CAT_ALREADY_ACTIVE = "'{key}' is already active"
CAT_RESTORED = "Restored: {key} ('{display}')"
CAT_RENAMED = "Renamed: {key} '{old_display}' -> '{new_display}'"

# === Validate ===
VALIDATE_KEY_EMPTY = "category key must not be empty"
VALIDATE_KEY_INVALID_CHARS = (
    "category key must match [a-z0-9_]+ (ASCII lowercase/digit/underscore): {key!r}"
)

# === Summary / 参照系共通 ===
SUMMARY_NO_RECORDS = "No records"
SUMMARY_TOTAL = "Total: {total}"
SUMMARY_TOTAL_WITH_ACTIVE = "Total: {total} (includes active)"
SUMMARY_DAILY_AVG_SUFFIX = "/ daily avg {avg}"
SUMMARY_BREAKDOWN_TITLE = "Daily"
SUMMARY_BREAKDOWN_COL_DATE = "Date"
SUMMARY_BREAKDOWN_COL_TOTAL = "Total"
SUMMARY_RECORDING_TAG = "recording {elapsed}"

# === Today ===
TODAY_HEADER = "{date_iso} ({weekday})"

# === Week ===
WEEK_LABEL_ROLLING = "Last 7 days"
WEEK_LABEL_CALENDAR = "This week"
WEEK_HEADER = "{label} ({from_date} to {to_date})"

# === Month ===
MONTH_LABEL_ROLLING = "Last 30 days"
MONTH_LABEL_CALENDAR = "This month"
MONTH_HEADER = "{label} ({from_date} to {to_date})"

# === Range ===
RANGE_HEADER = "Range ({from_date} to {to_date})"
RANGE_INVALID_FROM = "--from has invalid date format (YYYY-MM-DD): {value!r}"
RANGE_INVALID_TO = "--to has invalid date format (YYYY-MM-DD): {value!r}"
RANGE_FROM_AFTER_TO = "--from ({from_date}) must be on or before --to ({to_date})"

# === All ===
ALL_TITLE = "All time"
ALL_HEADER_SINCE = "All time (since {from_date})"

# === Menu ===
MENU_TITLE = "tsk - task recorder"
MENU_ACTIVE_LINE = "Active: [{display}] {description} ({elapsed})"
MENU_ACTIVE_NONE = "Active: none"
MENU_RECENT_LABEL = "Recent:"
MENU_PROMPT_ACTION = "Select an action"
MENU_CHOICE_START = "Start"
MENU_CHOICE_STOP = "Stop"
MENU_CHOICE_STOP_DISABLED = "(no active session)"
MENU_CHOICE_TODAY = "Today"
MENU_CHOICE_WEEK = "This week"
MENU_CHOICE_MONTH = "This month"
MENU_CHOICE_CAT = "Categories"
MENU_CHOICE_HELP = "Help (CLI commands)"
MENU_CHOICE_QUIT = "Quit"
MENU_PROMPT_CATEGORY = "Select a category"
MENU_PROMPT_DESCRIPTION = "What did you do? (optional, blank to skip)"
MENU_NO_ACTIVE_CATEGORIES = "No active categories. Add one first via 'Categories -> Add'."
MENU_NO_ACTIVE_CATEGORIES_SHORT = "No active categories"
MENU_NO_ARCHIVED_CATEGORIES = "No archived categories"
MENU_PROMPT_PRESS_ENTER = "[Press Enter to go back]"
MENU_INTERRUPTED = "(Interrupted)"
MENU_UNKNOWN_CHOICE = "(Unknown choice: {choice})"
MENU_CAT_TITLE = "Category management"
MENU_CAT_CHOICE_LIST = "List"
MENU_CAT_CHOICE_ADD = "Add"
MENU_CAT_CHOICE_REMOVE = "Archive"
MENU_CAT_CHOICE_RESTORE = "Restore from archive"
MENU_CAT_CHOICE_RENAME = "Rename (display_name)"
MENU_CAT_CHOICE_BACK = "<- Back"
MENU_CAT_PROMPT_NEW_KEY = "New category key (ASCII lowercase/digit/_)"
MENU_CAT_PROMPT_DISPLAY = "Display name"
MENU_CAT_PROMPT_REMOVE = "Select a category to archive"
MENU_CAT_PROMPT_RESTORE = "Select a category to restore"
MENU_CAT_PROMPT_RENAME = "Select a category to rename"
MENU_CAT_PROMPT_NEW_DISPLAY = "New display name"
MENU_CAT_CONFIRM_REMOVE = "Archive {display} ({key})?"

# === Errors ===
ERROR_INVALID_KEY = "Invalid category key: {key}"
