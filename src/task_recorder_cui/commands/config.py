"""tsk config サブコマンド: get / set / list / reset。"""

from task_recorder_cui.config import (
    all_keys,
    get_value,
    load_config,
    reset_value,
    save_config,
    set_value,
)
from task_recorder_cui.io import print_error, print_line
from task_recorder_cui.utils.paths import normalize_user_path


def list_all() -> int:
    """全設定キーと現在値を表示する。"""
    cfg = load_config()
    for key in sorted(all_keys()):
        val = get_value(cfg, key)
        print_line(f"{key} = {val}")
    return 0


def get(key: str) -> int:
    """単一キーの値を表示する。"""
    cfg = load_config()
    try:
        val = get_value(cfg, key)
    except KeyError as e:
        print_error(str(e))
        return 1
    print_line(str(val))
    return 0


def set_(key: str, value: str) -> int:
    """単一キーを更新して保存する。

    timer.sound_path の場合は Windows パスを POSIX に自動変換する。
    """
    cfg = load_config()
    try:
        if key == "timer.sound_path":
            value = str(normalize_user_path(value))
        updated = set_value(cfg, key, value)
    except (KeyError, ValueError, FileNotFoundError, RuntimeError) as e:
        print_error(str(e))
        return 1
    save_config(updated)
    print_line(f"{key} = {get_value(updated, key)}")
    return 0


def reset(key: str) -> int:
    """単一キーをデフォルト値に戻して保存する。"""
    cfg = load_config()
    try:
        updated = reset_value(cfg, key)
    except KeyError as e:
        print_error(str(e))
        return 1
    save_config(updated)
    print_line(f"{key} = {get_value(updated, key)}")
    return 0
