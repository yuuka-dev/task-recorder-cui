"""services.timer の時刻パーサのテスト。"""

import pytest

from task_recorder_cui.services.timer import parse_timer_spec


def test_parse_timer_spec_h_and_m() -> None:
    """'2h30m' は 150 分。"""
    assert parse_timer_spec("2h30m") == 150


def test_parse_timer_spec_m_only() -> None:
    assert parse_timer_spec("30m") == 30


def test_parse_timer_spec_h_only() -> None:
    assert parse_timer_spec("2h") == 120


def test_parse_timer_spec_plain_number_is_minutes() -> None:
    """'150' は分単体扱い。"""
    assert parse_timer_spec("150") == 150


def test_parse_timer_spec_150m() -> None:
    assert parse_timer_spec("150m") == 150


def test_parse_timer_spec_rejects_zero() -> None:
    with pytest.raises(ValueError, match="1 分以上"):
        parse_timer_spec("0m")


def test_parse_timer_spec_rejects_negative_hidden() -> None:
    """負の数値は正規表現自体で弾かれる。"""
    with pytest.raises(ValueError, match="不正"):
        parse_timer_spec("-5m")


def test_parse_timer_spec_rejects_empty() -> None:
    with pytest.raises(ValueError, match="不正"):
        parse_timer_spec("")


def test_parse_timer_spec_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="不正"):
        parse_timer_spec("abc")


def test_parse_timer_spec_rejects_whitespace() -> None:
    with pytest.raises(ValueError, match="不正"):
        parse_timer_spec("2h 30m")


# --- Task 10: play_sound / show_notification ---

from pathlib import Path  # noqa: E402


def test_play_sound_invokes_powershell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """play_sound は powershell.exe を SoundPlayer で呼び出す。"""
    import subprocess

    from task_recorder_cui.services import timer as timer_mod
    from task_recorder_cui.services.timer import play_sound

    wav = tmp_path / "a.wav"
    wav.write_bytes(b"")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(timer_mod, "to_windows_path", lambda p: f"C:\\fake\\{p.name}")
    monkeypatch.setattr(timer_mod.subprocess, "run", fake_run)

    play_sound(wav)

    assert len(calls) == 1
    assert calls[0][0] == "powershell.exe"
    joined = " ".join(calls[0])
    assert "Media.SoundPlayer" in joined
    assert "PlaySync" in joined
    assert "C:\\fake\\a.wav" in joined


def test_show_notification_invokes_powershell(monkeypatch: pytest.MonkeyPatch) -> None:
    """show_notification は powershell.exe で MessageBox を呼び出す。"""
    import subprocess

    from task_recorder_cui.services import timer as timer_mod
    from task_recorder_cui.services.timer import show_notification

    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(timer_mod.subprocess, "run", fake_run)

    show_notification("タイマー経過", "task-recorder-cui")

    assert len(calls) == 1
    assert calls[0][0] == "powershell.exe"
    joined = " ".join(calls[0])
    assert "MessageBox" in joined
    assert "タイマー経過" in joined


def test_play_sound_logs_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """powershell 呼び出しに失敗してもログファイルに記録して例外を握りつぶす。"""
    from task_recorder_cui.services import timer as timer_mod
    from task_recorder_cui.services.timer import play_sound

    wav = tmp_path / "a.wav"
    wav.write_bytes(b"")

    monkeypatch.setattr(timer_mod, "to_windows_path", lambda p: "C:\\x")
    monkeypatch.setattr(
        timer_mod, "timer_log_path", lambda: tmp_path / "timer.log"
    )

    def fake_run(*_: object, **__: object) -> object:
        raise OSError("no powershell")

    monkeypatch.setattr(timer_mod.subprocess, "run", fake_run)

    play_sound(wav)  # 例外伝搬しない

    log = (tmp_path / "timer.log").read_text()
    assert "no powershell" in log or "play_sound" in log


# --- Task 11: menu_lock / is_menu_alive ---


def test_menu_lock_acquire_and_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from task_recorder_cui.services.timer import is_menu_alive, menu_lock

    lock_path = tmp_path / "menu.lock"
    monkeypatch.setattr(
        "task_recorder_cui.services.timer.menu_lock_path", lambda: lock_path
    )

    assert not is_menu_alive()

    with menu_lock():
        assert lock_path.exists()
        assert is_menu_alive()

    assert not lock_path.exists()
    assert not is_menu_alive()


def test_is_menu_alive_false_for_dead_pid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """lock ファイルに死んだ PID が書かれてたら is_menu_alive=False。"""
    from task_recorder_cui.services.timer import is_menu_alive

    lock_path = tmp_path / "menu.lock"
    lock_path.write_text("99999999")  # 存在しない PID
    monkeypatch.setattr(
        "task_recorder_cui.services.timer.menu_lock_path", lambda: lock_path
    )

    assert not is_menu_alive()


# --- Task 13: spawn_daemon ---


def test_spawn_daemon_invokes_popen(monkeypatch: pytest.MonkeyPatch) -> None:
    """spawn_daemon は subprocess.Popen を start_new_session=True で呼ぶ。"""
    from task_recorder_cui.services import timer as timer_mod

    captured: dict[str, object] = {}

    class FakePopen:
        def __init__(self, args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs

    monkeypatch.setattr(timer_mod.subprocess, "Popen", FakePopen)
    monkeypatch.delenv("TSK_DAEMON_ENTRY", raising=False)

    timer_mod.spawn_daemon(42)

    args = captured["args"]
    assert isinstance(args, list)
    assert args[0:2] == ["tsk", "_timer-daemon"]
    assert "42" in args
    kwargs = captured["kwargs"]
    assert kwargs.get("start_new_session") is True


def test_spawn_daemon_uses_python_m_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """TSK_DAEMON_ENTRY 環境変数で 'python -m task_recorder_cui' 経由に切替可能。"""
    from task_recorder_cui.services import timer as timer_mod

    captured: dict[str, object] = {}

    class FakePopen:
        def __init__(self, args, **kwargs):
            captured["args"] = args

    monkeypatch.setattr(timer_mod.subprocess, "Popen", FakePopen)
    monkeypatch.setenv("TSK_DAEMON_ENTRY", "python-m")

    timer_mod.spawn_daemon(7)

    args = captured["args"]
    assert args[0:4] == ["python", "-m", "task_recorder_cui", "_timer-daemon"]
    assert "7" in args
