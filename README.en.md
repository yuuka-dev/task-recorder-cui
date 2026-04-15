English | [日本語](README.md)

# task-recorder-cui

[![CI](https://github.com/yuuka-dev/task-recorder-cui/actions/workflows/ci.yml/badge.svg)](https://github.com/yuuka-dev/task-recorder-cui/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yuuka-dev/task-recorder-cui/branch/main/graph/badge.svg)](https://codecov.io/gh/yuuka-dev/task-recorder-cui)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)

> **In one line**: A CUI tool that records how you spend your time and visualizes it as weekly / monthly averages. Focused on *time tracking*, not task management.

## Overview

### Why I built it

Time-tracking tools like Toggl are feature-rich, but many people (myself included) can't keep using them because of the friction. This tool strips the workflow down to the essentials — *what / how long / when* — and shows weekly and monthly averages as plain numbers.

Designed to be light enough that daily use never feels like a chore.

## Main features

- `tsk start` / `tsk stop` — stopwatch-style time tracking
- `tsk add` — add a past entry manually
- `tsk today` / `tsk week` / `tsk month` — summaries
- Categories are freely added / archived (initial set: `game` / `study` / `dev`)
- Run without arguments to enter a hierarchical interactive menu
- `--lang ja|en` or `LANG=en_US.UTF-8` for language switching

## Tech stack

| Category | Technology |
|---|---|
| Language | Python 3.11+ |
| Data store | SQLite (stdlib `sqlite3`) |
| CLI | `argparse` |
| Output formatting | `rich` |
| Interactive picker | `questionary` |
| Packaging | `pyproject.toml` + `pip install -e .` |

## Getting started

### Prerequisites

- Python 3.11 or later
- Tested on WSL2 Ubuntu (should work on any Linux / macOS)

### Setup

```bash
git clone https://github.com/yuuka-dev/task-recorder-cui.git
cd task-recorder-cui
pip install -e ".[dev]"
```

After install, the `tsk` command is available. Data is stored at `~/.local/share/tsk/records.db`.

### Language

The tool is bilingual (Japanese / English). The Japanese locale is the default.

```bash
tsk --lang en now            # one-shot English
tsk --lang ja now            # one-shot Japanese
LANG=en_US.UTF-8 tsk today   # via environment variable
```

Priority (highest first): `--lang` flag > `ui.lang` in config file > `LC_ALL` / `LANG` env var > `ja`.

Note: category `display_name` is user-provided and stays as-is (not translated). Rename with `tsk cat rename <key> "<new name>"` if desired. The argparse `--help` output is English-only in this release.

### Tests / coverage

```bash
pytest                                                  # all tests
pytest --cov=task_recorder_cui --cov-report=term        # with coverage
```

After updating dev dependencies, re-run `pip install -e ".[dev]"`.

## Basic usage

### Start recording

```bash
tsk start dev "ObatLog Firestore implementation"
```

### Stop recording

```bash
tsk stop
```

### Check today's records

```bash
tsk today
```

Sample output:

```
2026-04-14 (Tue)
14:00-15:30  [ゲーム] HOI4 日本プレイ        1h30m
15:45-17:00  [開発]   task-recorder-cui実装  1h15m
17:30-18:15  [学習]   ABC B問題              45m
19:00-       [開発]   ObatLog Firestore      (recording 32m)
Total: 4h02m (includes active)
ゲーム: 1h30m (37%)
開発:   1h47m (44%)
学習:   45m   (19%)
```

(display_names are shown exactly as stored — typically Japanese if you kept the defaults.)

### Add an entry after the fact

```bash
tsk add study 45 "ABC B problem"
```

### Weekly / monthly summaries

```bash
tsk week   # last 7 days
tsk month  # last 30 days
```

### Interactive menu

Run without arguments to launch the hierarchical menu.

```bash
tsk
```

Use arrow keys + Enter to choose. Ctrl+C / ESC exits safely at any time (any in-progress session is preserved).

## CLI subcommand reference

### Recording

| Command | Description |
|---|---|
| `tsk start <category_key> ["<description>"]` | Start a new session |
| `tsk stop` | Stop the currently active session |
| `tsk add <category_key> <minutes> ["<description>"]` | Add a past entry manually |
| `tsk now` | Show the currently active session and elapsed time |

### Reporting

| Command | Description |
|---|---|
| `tsk today` | Today's timeline + per-category total |
| `tsk week` | Last 7 days daily breakdown + weekly total + average |
| `tsk month` | Last 30 days, same format |
| `tsk range --from YYYY-MM-DD --to YYYY-MM-DD` | Arbitrary range |
| `tsk all` | All-time totals |

### Categories

| Command | Description |
|---|---|
| `tsk cat list` | List categories |
| `tsk cat add <key> "<display_name>"` | Add a category |
| `tsk cat remove <key>` | Archive a category (no physical delete) |
| `tsk cat restore <key>` | Restore from archive |
| `tsk cat rename <key> "<new_display_name>"` | Rename the display name |

> `key` must be ASCII lowercase / digits / underscore only. To avoid breaking historical records, categories are **archived**, not deleted.

## Out of scope (what this tool does not do)

Task management, cloud sync, notifications, graph rendering, pomodoro timing, tags, and priority fields are intentionally excluded. The tool only records time.

## License

[MIT License](./LICENSE)
