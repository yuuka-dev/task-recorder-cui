"""tsk cat 系サブコマンドのテスト。"""

import sqlite3
from pathlib import Path

import pytest

from task_recorder_cui.cli import main


def _fetch_category(db_path: Path, key: str) -> sqlite3.Row | None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM categories WHERE key = ?", (key,)).fetchone()
    finally:
        conn.close()


class TestList:
    def test_初期3件が表示される(
        self, isolated_db: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["cat", "list"])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "game" in out
        assert "study" in out
        assert "dev" in out

    def test_activeフラグでarchivedが出ない(
        self, isolated_db: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["cat", "remove", "game"])
        capsys.readouterr()
        exit_code = main(["cat", "list", "--active"])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "game" not in out
        assert "study" in out

    def test_archivedフラグでactiveが出ない(
        self, isolated_db: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["cat", "remove", "game"])
        capsys.readouterr()
        exit_code = main(["cat", "list", "--archived"])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "game" in out
        assert "study" not in out

    def test_active_archived併用はexit2(
        self, isolated_db: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as ex:
            main(["cat", "list", "--active", "--archived"])
        assert ex.value.code == 2


class TestAdd:
    def test_新規keyを追加できる(
        self, isolated_db: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["cat", "add", "reading", "読書"])
        assert exit_code == 0
        row = _fetch_category(isolated_db, "reading")
        assert row is not None
        assert row["display_name"] == "読書"
        assert row["archived"] == 0

    def test_不正keyはexit1(self, isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["cat", "add", "Reading", "読書"])  # 大文字
        assert exit_code == 1
        err = capsys.readouterr().err
        assert "Reading" in err

    def test_重複activeはexit1(self, isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["cat", "add", "game", "ゲーム2"])  # 既存active
        assert exit_code == 1
        assert "既に存在" in capsys.readouterr().err
        # display_name は変わらない
        assert _fetch_category(isolated_db, "game")["display_name"] == "ゲーム"

    def test_archived同名を復帰して表示名を上書き(
        self, isolated_db: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["cat", "remove", "game"])
        capsys.readouterr()
        exit_code = main(["cat", "add", "game", "ゲーム改"])
        assert exit_code == 0
        assert "再有効化" in capsys.readouterr().out
        row = _fetch_category(isolated_db, "game")
        assert row["archived"] == 0
        assert row["display_name"] == "ゲーム改"


class TestRemove:
    def test_archivedにできる(self, isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["cat", "remove", "game"])
        assert exit_code == 0
        row = _fetch_category(isolated_db, "game")
        assert row["archived"] == 1

    def test_未存在はexit1(self, isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["cat", "remove", "nonexistent"])
        assert exit_code == 1

    def test_既にarchivedでもexit0(
        self, isolated_db: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["cat", "remove", "game"])
        capsys.readouterr()
        exit_code = main(["cat", "remove", "game"])
        assert exit_code == 0
        assert "既にアーカイブ" in capsys.readouterr().out


class TestRestore:
    def test_archivedを戻せる(self, isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
        main(["cat", "remove", "game"])
        capsys.readouterr()
        exit_code = main(["cat", "restore", "game"])
        assert exit_code == 0
        assert _fetch_category(isolated_db, "game")["archived"] == 0

    def test_未存在はexit1(self, isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["cat", "restore", "nonexistent"])
        assert exit_code == 1


class TestRename:
    def test_display_nameを変更できる(
        self, isolated_db: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["cat", "rename", "game", "ガチャゲー"])
        assert exit_code == 0
        assert _fetch_category(isolated_db, "game")["display_name"] == "ガチャゲー"

    def test_未存在はexit1(self, isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["cat", "rename", "nonexistent", "x"])
        assert exit_code == 1

    def test_空display_nameはexit1(
        self, isolated_db: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["cat", "rename", "game", ""])
        assert exit_code == 1


class TestEnglishOutput:
    """--lang en で英語メッセージが出力されることを確認する。"""

    def test_cat_list_english(self, isolated_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from task_recorder_cui.i18n import set_lang

        try:
            rc = main(["--lang", "en", "cat", "list"])
            assert rc == 0
            out = capsys.readouterr().out
            assert "Categories" in out
            assert "display_name" in out
        finally:
            set_lang(None)

    def test_cat_not_found_english(
        self, isolated_db: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from task_recorder_cui.i18n import set_lang

        try:
            rc = main(["--lang", "en", "cat", "remove", "nope"])
            assert rc == 1
            assert "does not exist" in capsys.readouterr().err
        finally:
            set_lang(None)


# --- 追加: 未カバー分岐 ---


def test_list_categories_empty_with_archived_only(
    isolated_db, capsys: pytest.CaptureFixture[str]
) -> None:
    """archived_only でヒットなし → CAT_LIST_EMPTY_ARCHIVED。"""
    from task_recorder_cui.commands import cat as cat_cmd

    rc = cat_cmd.list_categories(active_only=False, archived_only=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "archived" in out or "アーカイブ" in out


def test_list_categories_empty_with_active_only(
    isolated_db, capsys: pytest.CaptureFixture[str]
) -> None:
    """active_only でヒットなし → CAT_LIST_EMPTY_ACTIVE。"""
    from task_recorder_cui.commands import cat as cat_cmd
    from task_recorder_cui.db import open_db

    with open_db() as conn, conn:
        for key in ("game", "study", "dev"):
            conn.execute("UPDATE categories SET archived = 1 WHERE key = ?", (key,))

    rc = cat_cmd.list_categories(active_only=True, archived_only=False)
    assert rc == 0
    out = capsys.readouterr().out
    assert "active" in out.lower() or "有効" in out or "active" in out


def test_list_categories_empty_when_no_rows(
    isolated_db, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """フィルタ無しで 0 件 → CAT_LIST_EMPTY。

    初期データ自動投入で通常は到達しない分岐なので `list_all_categories` を
    空返しに差し替える。
    """
    from task_recorder_cui.commands import cat as cat_cmd

    monkeypatch.setattr(cat_cmd, "list_all_categories", lambda *a, **kw: [])
    rc = cat_cmd.list_categories(active_only=False, archived_only=False)
    assert rc == 0
    out = capsys.readouterr().out
    assert "カテゴリがありません" in out or "No categories" in out


def test_add_category_empty_display_name_rejected(
    isolated_db, capsys: pytest.CaptureFixture[str]
) -> None:
    from task_recorder_cui.commands import cat as cat_cmd

    rc = cat_cmd.add_category("reading", "")
    assert rc == 1
    assert "空" in capsys.readouterr().err


def test_restore_category_noop_when_already_active(
    isolated_db, capsys: pytest.CaptureFixture[str]
) -> None:
    """既に active なカテゴリを restore しても no-op で exit 0。"""
    from task_recorder_cui.commands import cat as cat_cmd

    rc = cat_cmd.restore_category("dev")  # dev は初期データで active
    assert rc == 0
    out = capsys.readouterr().out
    assert "既に有効" in out or "already active" in out
