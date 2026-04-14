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
