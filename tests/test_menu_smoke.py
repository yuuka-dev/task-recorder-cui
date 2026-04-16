"""menu.run() のスモークテスト (UI を最小モックして 0 終了することだけ確認)。"""

from task_recorder_cui.db import open_db


def test_menu_run_quit_returns_zero(isolated_db, monkeypatch) -> None:
    """quit を選んだら戻り値 0、DB は空のまま。"""
    monkeypatch.setattr(
        "task_recorder_cui.menu._show_main_menu",
        lambda *, recording, **_kw: "quit",
    )

    from task_recorder_cui.menu import run

    rc = run()
    assert rc == 0

    with open_db() as conn:
        rec_count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    assert rec_count == 0


def test_menu_run_returns_zero_on_none(isolated_db, monkeypatch) -> None:
    """ESC / Ctrl+C で None が返っても 0 終了。"""
    monkeypatch.setattr(
        "task_recorder_cui.menu._show_main_menu",
        lambda *, recording, **_kw: None,
    )

    from task_recorder_cui.menu import run

    assert run() == 0


def test_menu_run_holds_lock(isolated_db, monkeypatch, tmp_path) -> None:
    """menu.run() が呼ばれている間 menu lock が取得される。"""
    from task_recorder_cui.services.timer import is_menu_alive

    lock_path = tmp_path / "menu.lock"
    monkeypatch.setattr(
        "task_recorder_cui.services.timer.menu_lock_path",
        lambda: lock_path,
    )

    observed: list[bool] = []

    def fake_menu(*, recording, **_kw):
        observed.append(is_menu_alive())
        return "quit"

    monkeypatch.setattr("task_recorder_cui.menu._show_main_menu", fake_menu)

    from task_recorder_cui.menu import run

    rc = run()
    assert rc == 0
    assert observed == [True]
    assert not lock_path.exists()
