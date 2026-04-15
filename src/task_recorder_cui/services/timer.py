"""タイマー機能の中核ロジック。

時刻パーサ、daemon プロセスの起動、音・デスクトップ通知の再生を集約する。
CLI / commands 層からはここだけを呼ぶ。
"""

import contextlib
import os
import re
import subprocess
import time as _time
import traceback
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path

from task_recorder_cui.utils.paths import to_windows_path
from task_recorder_cui.utils.time import now_utc

# 2h30m / 30m / 2h / 150 / 150m を許容
_TIMER_SPEC_RE = re.compile(r"^(?:(\d+)h)?(?:(\d+)m?)?$")


def parse_timer_spec(spec: str) -> int:
    """人間向けの時刻指定文字列を分に変換する。

    受理する書式:
        '2h30m' -> 150
        '30m'   -> 30
        '2h'    -> 120
        '150m'  -> 150
        '150'   -> 150 (数字だけなら分単位)

    Args:
        spec: ユーザ入力文字列。空白なし、小文字 h/m。

    Returns:
        分数 (1 以上の整数)。

    Raises:
        ValueError: 書式不一致、または 0 分以下の場合。

    """
    match = _TIMER_SPEC_RE.fullmatch(spec)
    if match is None or (match.group(1) is None and match.group(2) is None):
        raise ValueError(f"タイマー書式が不正です: {spec!r}")
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    total = hours * 60 + minutes
    if total < 1:
        raise ValueError(f"タイマーは 1 分以上を指定してください: {spec!r}")
    return total


def timer_log_path() -> Path:
    """タイマー機能のログファイルのパスを返す (テストで差し替え可能にする目的で関数化)。"""
    return Path.home() / ".local" / "share" / "tsk" / "timer.log"


def _log_failure(context: str, exc: BaseException) -> None:
    """エラーをログに追記する (無害な best-effort)。"""
    path = timer_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fp:
            fp.write(f"[{datetime.now().isoformat()}] {context}: {type(exc).__name__}: {exc}\n")
            fp.write(traceback.format_exc())
            fp.write("\n")
    except OSError:
        pass


def play_sound(wav_path: Path) -> None:
    """WAV ファイルを Windows 側のスピーカーで再生する。

    エラーは握りつぶしてログに記録する (タイマー処理は音が鳴らなくても継続する
    べき)。

    Args:
        wav_path: 再生する WAV ファイル (POSIX パス、存在前提)。

    """
    try:
        win_path = to_windows_path(wav_path)
        win_path_escaped = win_path.replace("'", "''")
        ps_cmd = f"(New-Object Media.SoundPlayer '{win_path_escaped}').PlaySync()"
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            check=False,
        )
    except Exception as e:
        _log_failure("play_sound", e)


def show_notification(message: str, title: str = "task-recorder-cui") -> None:
    """Windows のデスクトップに MessageBox を表示する。

    Args:
        message: 本文。
        title: ウィンドウタイトル。

    """
    try:
        msg_escaped = message.replace("'", "''")
        title_escaped = title.replace("'", "''")
        ps_cmd = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            f"[System.Windows.Forms.MessageBox]::Show('{msg_escaped}', '{title_escaped}')"
        )
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            check=False,
        )
    except Exception as e:
        _log_failure("show_notification", e)


def menu_lock_path() -> Path:
    """menu 起動検出用 lock ファイルのパス。"""
    return Path.home() / ".local" / "share" / "tsk" / "menu.lock"


def is_menu_alive() -> bool:
    """tsk メニューが現在起動中かを判定する。

    lock ファイルから PID を読み、その PID のプロセスが存在するかで判定。

    Returns:
        生存中なら True。lock が無い / PID 死亡は False。

    """
    path = menu_lock_path()
    if not path.exists():
        return False
    try:
        pid_text = path.read_text().strip()
        pid = int(pid_text)
    except (OSError, ValueError):
        return False
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False
    return True


@contextlib.contextmanager
def menu_lock() -> Iterator[None]:
    """menu 実行中であることを示す lock を取得する。

    コンテキスト終了時に lock ファイルを削除する。二重取得は許容 (上書き)。
    """
    path = menu_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(os.getpid()))
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)


def _load_record(conn, record_id: int):
    """指定 id の Record を返す。存在しなければ None。"""
    from task_recorder_cui.repo import row_to_record

    row = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    return row_to_record(row) if row else None


def run_daemon_loop(
    record_id: int,
    *,
    sleep_fn: Callable[[float], None] = _time.sleep,
    fire_fn: Callable[..., None] | None = None,
    tick_seconds: float = 1.0,
    max_iterations: int | None = None,
) -> int:
    """タイマー daemon のメインループ。

    1 秒ごとに DB を開き直して対象レコードの状態を確認し、target_at を過ぎたら
    fire_fn を呼ぶ。以下のいずれかで即座に exit する:

        - レコードが削除されている
        - timer_target_at が NULL に戻された (キャンセル)
        - timer_fired_at が既に set されている
        - セッションが終了済 (ended_at set)
        - 発火完了

    Args:
        record_id: 対象レコード id。
        sleep_fn: 1 tick の sleep 関数 (テスト時にモック)。
        fire_fn: 発火時に呼ぶ関数。None なら _default_fire を使う。
        tick_seconds: ループ間隔秒数。
        max_iterations: テスト用の上限 (None なら無制限)。

    Returns:
        exit code (常に 0)。

    """
    from task_recorder_cui.db import open_db as _open_db

    if fire_fn is None:
        fire_fn = _default_fire

    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        iterations += 1
        with _open_db() as conn:
            record = _load_record(conn, record_id)
            if record is None:
                return 0
            if record.timer_target_at is None:
                return 0
            if record.timer_fired_at is not None:
                return 0
            if record.ended_at is not None:
                return 0
            if now_utc() >= record.timer_target_at:
                fire_fn(record)
                return 0
        sleep_fn(tick_seconds)
    return 0


def spawn_daemon(record_id: int) -> None:
    """detach された子プロセスでタイマー daemon を起動する。

    子プロセスは親の tsk CLI が終了しても生き続ける (start_new_session=True)。
    標準入出力は /dev/null にリダイレクト。

    Args:
        record_id: daemon が監視するレコード id。

    """
    entry = os.environ.get("TSK_DAEMON_ENTRY", "tsk")
    if entry == "python-m":
        cmd = ["python", "-m", "task_recorder_cui", "_timer-daemon", str(record_id)]
    else:
        cmd = ["tsk", "_timer-daemon", str(record_id)]

    subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _default_fire(record) -> None:
    """発火時のデフォルト動作: 音 + (メニュー閉時なら) 通知 + DB に fired_at 記録。"""
    from task_recorder_cui.config import load_config
    from task_recorder_cui.db import open_db as _open_db
    from task_recorder_cui.repo import mark_timer_fired

    cfg = load_config()
    if not cfg.timer.enabled:
        with _open_db() as conn, conn:
            mark_timer_fired(conn, record.id, fired_at=now_utc())
        return
    wav = Path(cfg.timer.sound_path).expanduser()
    if wav.exists():
        play_sound(wav)
    if cfg.timer.notify_when_closed and not is_menu_alive():
        show_notification("タイマー経過しました")
    with _open_db() as conn, conn:
        mark_timer_fired(conn, record.id, fired_at=now_utc())
