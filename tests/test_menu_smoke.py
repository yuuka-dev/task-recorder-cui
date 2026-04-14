"""menu.run() のスモークテスト (UI を最小モックして 0 終了することだけ確認)。"""

from task_recorder_cui.db import open_db


def test_menu_run_quit_returns_zero(isolated_db, monkeypatch) -> None:
    """quit を選んだら戻り値 0、DB は空のまま。"""
    monkeypatch.setattr(
        "task_recorder_cui.menu._show_main_menu",
        lambda *, recording: "quit",
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
        lambda *, recording: None,
    )

    from task_recorder_cui.menu import run

    assert run() == 0
