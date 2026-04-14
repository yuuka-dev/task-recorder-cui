"""pytest の共通フィクスチャ。

各テストで独立したSQLiteファイルを使うため、`TSK_DB_PATH` 環境変数を
tmp_path 以下の一時ファイルに差し替える。
"""

from pathlib import Path

import pytest


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """テスト用の隔離DBパスを返し、環境変数 TSK_DB_PATH を上書きする。

    Args:
        tmp_path: pytest組み込みの一時ディレクトリ。
        monkeypatch: 環境変数を自動で元に戻すための monkeypatch。

    Returns:
        DBファイルのパス (まだ未作成)。commandsから open_db() 経由で作成される。

    """
    db_path = tmp_path / "records.db"
    monkeypatch.setenv("TSK_DB_PATH", str(db_path))
    return db_path
