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

# === Errors ===
ERROR_INVALID_KEY = "Invalid category key: {key}"
