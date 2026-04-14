# CI セットアップ (Phase 7) 設計書

- 作成日: 2026-04-14
- 対象リポジトリ: `yuuka-dev/task-recorder-cui`
- 対象ブランチ: `chore/ci`
- 関連ドキュメント: ルートの `CLAUDE.md`(Phase 7 / CI バッジ / ブランチ戦略)

## 目的

GitHub Actions で以下を push / PR 時に自動実行する:

1. Lint (`ruff check`)
2. フォーマットチェック (`ruff format --check`)
3. テスト + カバレッジ (`pytest --cov`)
4. カバレッジを Codecov にアップロード

あわせて `README.md` の CI / Codecov バッジを実リポジトリ URL に揃える。

## 非対象 (スコープ外)

- リリース自動化 (PyPI publish, タグ付け等)
- Lint 以外の静的解析 (mypy, bandit 等)
- Windows / macOS ランナー対応
- Dependabot / auto-merge 設定
- カバレッジしきい値での fail (最初は上昇トレンドだけ見る)

## 変更ファイル

| パス | 変更種別 | 概要 |
|---|---|---|
| `.github/workflows/ci.yml` | 新規 | CI ワークフロー本体 |
| `pyproject.toml` | 更新 | `pytest-cov` を dev deps に追加 + `[tool.coverage.*]` 設定 |
| `README.md` | 更新 | CI バッジ URL 修正 + Codecov バッジ追加 |

## `.github/workflows/ci.yml` の設計

### トリガー

```yaml
on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]
```

### concurrency

同一ブランチで新しい run が起きたら古い run をキャンセルし、Actions 分を節約する。

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

### ジョブ構成

単一ジョブ `test`、`ubuntu-latest`、Python 3.11 / 3.12 / 3.13 のマトリクス。`fail-fast: false` にして 1 バージョンの失敗で他を止めない。

| ステップ | 内容 | 備考 |
|---|---|---|
| 1 | `actions/checkout@v4` | — |
| 2 | `actions/setup-python@v5` | `python-version: ${{ matrix.python-version }}` / `cache: pip` / `cache-dependency-path: pyproject.toml` |
| 3 | `pip install -e ".[dev]"` | — |
| 4 | `ruff check .` | — |
| 5 | `ruff format --check .` | フォーマット崩れで即 fail |
| 6 | `pytest --cov=task_recorder_cui --cov-report=xml --cov-report=term` | `coverage.xml` が出力される |
| 7 | `codecov/codecov-action@v5` | `if: matrix.python-version == '3.11'` / token 不要 (public repo) / `files: ./coverage.xml` |

### 重複アップロード防止

カバレッジアップロードはマトリクスの 1 バージョン (3.11) でのみ行い、同一 commit に対する重複レポートを防ぐ。

## `pyproject.toml` の変更

### dev deps に `pytest-cov` を追加

```toml
[project.optional-dependencies]
dev = [
    "ruff",
    "pytest",
    "pytest-cov",
    "jupyterlab",
    "pandas",
]
```

### coverage 設定

```toml
[tool.coverage.run]
source = ["task_recorder_cui"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
```

`branch = true` で分岐カバレッジも計測。`exclude_lines` で自明な行は除外。

### ローカル側の注意

dev deps に追加するので、既にローカルに `pip install -e ".[dev]"` 済みの開発者は PR マージ後にもう一度同コマンドを実行する必要がある(README の該当節にも軽く触れる)。

## `README.md` の変更

現状の README には License / Python の 2 バッジしか無いので、**CI バッジと Codecov バッジを追加**する (CLAUDE.md のテンプレにあった `yuuka_overdose/PROJECT_NAME/...` は単なるテンプレ値で、実 README には現在書かれていない)。

追加行:

```markdown
[![CI](https://github.com/yuuka-dev/task-recorder-cui/actions/workflows/ci.yml/badge.svg)](https://github.com/yuuka-dev/task-recorder-cui/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yuuka-dev/task-recorder-cui/branch/main/graph/badge.svg)](https://codecov.io/gh/yuuka-dev/task-recorder-cui)
```

既存の License / Python バッジはそのまま残し、CI → codecov → License → Python の順で 4 バッジ並べる。

- 「テスト/カバレッジ」節を追加し、`pytest` と `pytest --cov` の実行例を簡潔に書く。

## 成功基準

- [ ] `chore/ci` ブランチからの PR で Actions が起動し、全マトリクスがグリーン
- [ ] Codecov に初回レポートが上がり、バッジが `unknown` から実数値に変わる
- [ ] ローカルで `pytest --cov` が動く
- [ ] `ruff check .` と `ruff format --check .` がいずれもグリーン
- [ ] README 上のバッジが 2 つとも表示され、リンク先が正しい

## リスク / 留意点

1. **Codecov 初回アップロードの token 必要有無**: 公開リポジトリは token 無しで動作するが、Codecov 側の挙動変更で将来 token が必要になる可能性あり。失敗時は `secrets.CODECOV_TOKEN` を後追いで追加する方針。
2. **既存コードの `ruff format --check` 通過**: 現時点の main が `ruff format` 済みであるかは未検証。CI を入れる前にローカルで `ruff format --check .` を走らせて、未フォーマットがあれば同 PR 内で `ruff format .` 結果をコミットする。
3. **3.12 / 3.13 での挙動差**: 依存 (`rich`, `questionary`) のホイールは両版で供給されている見込みだが、最悪 3.13 で失敗した場合はマトリクスから一時的に 3.13 を除外し、issue を起票して追う。
4. **カバレッジの急変**: 初回導入時にカバレッジが想定より低い可能性があるが、Phase 7 はしきい値 fail を入れない方針なのでブロック要因にはならない。

## 実装順 (ざっくり)

1. `pyproject.toml` の dev deps と coverage 設定を追加
2. ローカルで `pip install -e ".[dev]"` → `ruff check .` / `ruff format --check .` / `pytest --cov` が通ることを確認 (必要なら `ruff format .` の結果もコミット)
3. `.github/workflows/ci.yml` を追加
4. `README.md` のバッジと開発節を更新
5. push → PR 作成 → Actions グリーンを確認 → マージはユーザが実施
