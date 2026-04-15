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
    "Reactivated: {key} -> '{display}' "
    "(restored from archive, display_name overwritten)"
)
CAT_ALREADY_ARCHIVED = "'{key}' is already archived"
CAT_ARCHIVED = "Archived: {key} ('{display}')"
CAT_ALREADY_ACTIVE = "'{key}' is already active"
CAT_RESTORED = "Restored: {key} ('{display}')"
CAT_RENAMED = "Renamed: {key} '{old_display}' -> '{new_display}'"

# === Validate ===
VALIDATE_KEY_EMPTY = "category key must not be empty"
VALIDATE_KEY_INVALID_CHARS = (
    "category key must match [a-z0-9_]+ "
    "(ASCII lowercase/digit/underscore): {key!r}"
)

# === Errors ===
ERROR_INVALID_KEY = "Invalid category key: {key}"
