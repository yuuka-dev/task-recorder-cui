# task-recorder-cui

日々の時間の使い方を記録して、週平均・月平均で可視化するCUIツール。
タスク管理ではなく時間記録(タイムトラッキング)に特化する。

## コンセプト
- 「何を・何時間・いつやったか」をざっくり記録する
- カテゴリは最初は3つ(game/study/dev)、追加削除可能
- 週平均・月平均を数字で見る
- 既存ツール(Toggl等)が続かなかった人向けの、極限まで削ぎ落とした版
- 毎日使うのが苦にならない軽さを最優先

## コマンド名
`tsk` (pyproject.tomlの[project.scripts]で登録)

## 技術スタック
- Python 3.11+
- SQLite (標準ライブラリ `sqlite3`)
- CLI パーサ: `argparse` (標準ライブラリ)
- 出力整形: `rich` (Table の CJK 幅吸収・マークアップエスケープ)
- インタラクティブメニュー: `questionary` (矢印キーで選択する軽量 prompt。フルスクリーン TUI は使わない)
- 環境: WSL2 Ubuntu
- パッケージ管理: pyproject.toml + pip install -e .

## データモデル

SQLiteファイル1個で完結: `~/.local/share/tsk/records.db`

### テーブル: categories

| カラム | 型 | 説明 |
|---|---|---|
| id | INTEGER PRIMARY KEY | |
| key | TEXT UNIQUE NOT NULL | 内部キー (例: 'game', 'study', 'dev'), ASCII英小文字+数字+アンダースコアのみ |
| display_name | TEXT NOT NULL | 表示名 (例: 'ゲーム', '学習', '開発'), 日本語OK |
| created_at | TEXT NOT NULL | ISO8601 |
| archived | INTEGER NOT NULL DEFAULT 0 | 1ならメニューの選択肢から非表示、集計には含める |

初期データ:
- ('game', 'ゲーム')
- ('study', '学習')
- ('dev', '開発')

### テーブル: records

| カラム | 型 | 説明 |
|---|---|---|
| id | INTEGER PRIMARY KEY | |
| category_key | TEXT NOT NULL | categories.key を参照 (FKは張らない、CUI段階なのでシンプルに) |
| description | TEXT | 具体的に何をしたか (NULL可) |
| started_at | TEXT NOT NULL | ISO8601 (timezone-aware) |
| ended_at | TEXT | ISO8601 (NULLなら記録中) |
| duration_minutes | INTEGER | 終了時に計算して埋める (NULLなら記録中) |
| timer_target_at | TEXT | タイマー発火予定時刻 (ISO8601 UTC、NULLならタイマー未設定) |
| timer_fired_at | TEXT | 実際の発火時刻 (NULLなら未発火) |

### 設計メモ

- **key と display_name を分ける理由**: 集計出力時に日本語表示できる。将来i18n対応したくなっても崩れない。archive後にkeyが衝突しない。
- **category_key は TEXT で保持 (正規化しない)**: CUI段階ではJOINレスで扱える方が実装がシンプル。Android版移植時にRoomのリレーションで綺麗にすることは可能。
- **archived は物理削除しない**: 過去レコードが参照しているkeyを消すと履歴集計が壊れるため。アーカイブはメニュー表示から消えるだけで、`tsk week` 等の集計には含まれ続ける。
- **時刻は全てISO8601文字列で保存、コード内ではdatetime(timezone-aware)で扱う**。
- **層構造**: `cli/menu` → `commands/*` → `repo.py` → `db.py` (sqlite3) の順。`commands/` から直接 SQL は書かず `repo.py` 経由にする。

## CLIサブコマンド (MVP)

### 記録系
- `tsk start <category_key> ["<description>"]`
  - 例: `tsk start game "Anno 117 街づくり"`
  - 例: `tsk start dev` (descriptionは省略可、後で補完する運用)
  - 既に記録中のセッションがある場合は警告して中断
- `tsk stop`
  - ended_at IS NULL のレコードに現在時刻を入れて duration_minutes を計算
  - 記録中のものがなければその旨を表示
- `tsk add <category_key> <minutes> ["<description>"]`
  - 事後に手動で追加 (例: `tsk add study 45 "ABC B問題"`)
  - started_at は現在時刻 - minutes で計算、ended_at は現在時刻
- `tsk now`
  - 現在記録中のセッションを表示 (started_atからの経過時間付き)

### 参照系
- `tsk today`
  - 今日の記録一覧 (時刻順) + カテゴリ別合計 + 合計時間
- `tsk week`
  - 直近7日の日別内訳 + 週合計 + カテゴリ別平均
- `tsk month`
  - 直近30日の同様の集計
- `tsk range <from> <to>`
  - 例: `tsk range 2026-04-01 2026-04-14` (任意期間の日別・カテゴリ別集計)
- `tsk all`
  - 全累計 (カテゴリ別内訳 + 日平均)

### カテゴリ管理
- `tsk cat list`
  - カテゴリ一覧 (key, display_name, archived状態を表示)
- `tsk cat add <key> "<display_name>"`
  - 例: `tsk cat add reading "読書"`
  - keyの検証: ASCII英小文字+数字+アンダースコアのみ
- `tsk cat remove <key>`
  - archivedフラグを1にする (物理削除しない)
- `tsk cat restore <key>`
  - archivedフラグを0に戻す
- `tsk cat rename <key> "<new_display_name>"`
  - display_nameのみ変更、keyは不変

### インタラクティブメニュー
- `tsk` (サブコマンドなし) で階層メニューを表示

メニュー構造:
```
┌─────────────────────────────────────┐
│ tsk - task recorder                 │
├─────────────────────────────────────┤
│ 現在: [開発] ObatLog実装 (32m経過)  │  ← 記録中の場合
│   or                                │
│ 現在: 記録なし                      │  ← 記録なしの場合
├─────────────────────────────────────┤
│ 直近:                               │
│   [ゲーム] HOI4        2h30m  2時間前 │
│   [開発]   フォント改造 1h15m  5時間前 │
├─────────────────────────────────────┤
│ 1) 開始                             │
│ 2) 停止 (記録中の場合のみ表示)      │
│ 3) 今日の一覧                       │
│ 4) 週集計                           │
│ 5) 月集計                           │
│ 6) カテゴリ管理                     │
│ q) 終了                             │
└─────────────────────────────────────┘
```

- 「1) 開始」を選ぶと、次画面でカテゴリ選択 (archivedでないもののみ)、description入力へ進む
- 「6) カテゴリ管理」を選ぶとサブメニューで list/add/remove/restore/rename が可能
- Ctrl+C で安全に抜けられること。記録中のセッションは保持される
- メニューから開始したセッションは、メニューを閉じた後も生きている (別ターミナルから `tsk stop` で終了可能)

## 出力イメージ

### tsk today
```
2026-04-14 (Tue)
14:00-15:30  [ゲーム] HOI4 日本プレイ        1h30m
15:45-17:00  [開発]   task-recorder-cui実装  1h15m
17:30-18:15  [学習]   ABC B問題              45m
19:00-       [開発]   ObatLog Firestore      (記録中 32m)
合計: 4h02m (記録中含む)
ゲーム: 1h30m (37%)
開発:   1h47m (44%)
学習:   45m   (19%)
```
### tsk week
```
直近7日 (2026-04-08 Tue 〜 2026-04-14 Mon)
日別:
04-08 Tue  ゲーム 1h00m  開発 3h00m  学習 30m    合計 4h30m
04-09 Wed  ゲーム 2h00m  開発 1h00m              合計 3h00m
04-10 Thu                開発 4h30m  学習 1h00m  合計 5h30m
04-11 Fri  ゲーム 3h00m  開発 30m                合計 3h30m
04-12 Sat  ゲーム 2h30m              学習 2h00m  合計 4h30m
04-13 Sun  ゲーム 1h30m  開発 2h00m  学習 45m    合計 4h15m
04-14 Mon  ゲーム 1h30m  開発 1h47m  学習 45m    合計 4h02m
週合計: 29h17m
ゲーム: 11h30m (39%) / 日平均 1h38m
開発:   12h47m (44%) / 日平均 1h49m
学習:   5h00m  (17%) / 日平均 43m
```
## 開発コマンド

```bash
# セットアップ
pip install -e ".[dev]"

# 実行
tsk                              # インタラクティブメニュー
python -m task_recorder_cui      # 同上 (コンソールスクリプト未インストール時)

# テスト
pytest                           # 全テスト
pytest --cov                     # カバレッジ付き (Codecov 用)
pytest tests/test_menu_pure.py -v  # 単体ファイル

# Lint / Format (ruff 一本)
ruff check .                     # 静的解析
ruff check . --fix               # 自動修正
ruff format .                    # フォーマット
```

## コーディング規約
- 型ヒント必須 (Python 3.11+ syntax、`list[str]`などのbuiltin generic使用)
- docstringの方針:
  - **公開関数・公開メソッド**: Google style または NumPy style で
    目的・Args・Returns・Raises を明記する
  - **private関数** (`_` プレフィックス) や自明な関数: 1行サマリーで可
  - **公開クラス**: 役割と主要な責務を明記
- 時刻処理は全て datetime(timezone-aware)、DBにはISO8601文字列で保存、表示時にローカルタイムへ
- SQLは生SQL (ORM不要)
- 出力はprint()直書きせず、`io.py` 等にまとめた出力関数経由にする (将来のカラー化/i18nのため)
- エラーは早期returnで処理、握りつぶさない
- サブコマンドごとにモジュール分割 (`cli/start.py`, `cli/stop.py`, `cli/week.py` 等)

### docstringフォーマット例 (Google style採用)
```python
def calculate_week_summary(start_date: date, end_date: date) -> WeekSummary:
    """指定期間の日別・カテゴリ別の時間集計を返す。

    Args:
        start_date: 集計開始日 (その日を含む)
        end_date: 集計終了日 (その日を含む)

    Returns:
        WeekSummary: 日別内訳とカテゴリ別合計・平均を含む集計結果

    Raises:
        ValueError: start_date が end_date より後の場合
    """
    ...


def _format_duration(minutes: int) -> str:
    """分を '2h30m' 形式に整形する。"""
    ...
```

## プロジェクト構成 (想定)
```
task-recorder-cui/
├── CLAUDE.md
├── README.md
├── LICENSE
├── pyproject.toml
├── src/
│   └── task_recorder_cui/
│       ├── __init__.py
│       ├── __main__.py         # python -m 用エントリ
│       ├── main.py
│       ├── cli.py              # argparse エントリポイント
│       ├── menu.py             # インタラクティブメニュー
│       ├── db.py               # SQLite初期化、マイグレーション
│       ├── models.py           # dataclass定義
│       ├── io.py               # 出力用関数
│       ├── repo.py             # Repository層 (commands から呼ぶ CRUD/集計)
│       ├── commands/
│       │   ├── _summary.py     # today/week/month/range/all 共通ロジック
│       │   ├── start.py
│       │   ├── stop.py
│       │   ├── add.py
│       │   ├── now.py
│       │   ├── today.py
│       │   ├── week.py
│       │   ├── month.py
│       │   ├── range.py        # 任意期間集計
│       │   ├── all.py          # 全累計
│       │   └── cat.py
│       └── utils/
│           ├── time.py         # 時刻フォーマット、duration計算
│           └── validate.py     # keyの検証等
└── tests/
    └── (pytest + pytest-cov、全コマンド & 純粋関数を網羅)
```
## やらないこと (スコープ外)

- タスク管理機能 (これは時間記録ツール、ToDoではない)
- カテゴリの物理削除 (archiveで十分)
- クラウド同期
- 通知機能
- タグ機能 (カテゴリ1つで十分)
- 優先度機能 (時間記録に優先度は不要)
- ポモドーロタイマー機能 (別ツール)

## Phase 2 計画 (MVP 後の拡張ロードマップ)

MVP (Phase 1-7) は v1.0.0 で完成。以降は以下の優先順で検討:

- **データ可視化** (本命): jupyterlab + pandas + plotly で interactive グラフ
  - `tsk export --csv` → notebook で `px.bar(df, x='date', y='minutes', color='category_key')` など
  - dev deps に `jupyterlab` / `pandas` は投入済、`plotly` の追加のみでいける
  - WSL2 運用は Jupyter Lab 中心 (Windows ブラウザが localhost に繋がる)
- **CSV エクスポート**: `tsk export --from YYYY-MM-DD --to YYYY-MM-DD` (可視化の前段)
- **過去レコードの編集**: `tsk edit <id>`
- **Android 版**: 同じ SQLite スキーマを Room に移植
- **Web ダッシュボード**: Next.js + Firestore (ObatLog スタック踏襲)
- **ActivityWatch 連携**: 稼働時間比率を自動取得
- **英語対応 (国際化)**: v1.0.0 で pyproject.toml の `description` は英語化済。以降のステップとして `README.en.md` 追加 → ツール本体の i18n (UI メッセージ / エラー文 / カテゴリ display_name の英語切替、`LANG=en` 対応) を検討

## Phase 2.1 実装済み機能 (v1.1.0)

- **任意時間タイマー**: `tsk start --timer 2h30m` または `tsk timer set 2h30m` で
  記録中セッションに単発タイマーを設定できる。経過時に Windows 側スピーカーから
  音を鳴らし、tsk メニュー閉時はデスクトップ通知 (MessageBox) で知らせる。
  **ポモドーロ (繰り返しサイクル) は引き続きスコープ外** (上記「やらないこと」参照)。
- **設定ファイル**: `~/.config/tsk/config.toml` で音ファイル、バーの色・スタイル、
  言語を設定可能。`tsk config get/set/list/reset` で CLI 経由の編集も可能。
- **プログレスバー**: メニューの「現在」行下と `tsk now` 出力末尾に、タイマー
  設定時のみ `[=====>   ] 1h20m / 2h30m (53%)` 形式で表示される。

## 設定ファイル

- パス: `~/.config/tsk/config.toml` (`TSK_CONFIG_PATH` で上書き可)
- 書式: TOML。未作成時はコード内デフォルトが使われる
- スキーマ:
  ```toml
  [timer]
  enabled = true                                   # false で機能無効化
  sound_path = "/mnt/c/Windows/Media/Alarm01.wav"  # 発火時の WAV
  notify_when_closed = true                        # メニュー閉時の MessageBox
  [ui]
  lang = "ja"           # ja / en
  bar_color = "cyan"    # rich カラー名
  bar_style = "solid"   # solid / rainbow / gradient
  ```
- ユーザが `C:\...` 形式のパスを設定すると自動的に `/mnt/c/...` に正規化される。

## ライセンス
MIT (予定、pyproject.tomlに記載)

## 開発ノート
- 機能追加前に `docs/superpowers/specs/YYYY-MM-DD-<feature>-design.md` で設計書、`docs/superpowers/plans/YYYY-MM-DD-<feature>.md` で実装計画を書く (superpowers:writing-plans)
- 最初のコミットはCLAUDE.mdとpyproject.tomlのみ、それから実装に入る
- コミットは機能単位で小さく切る (DB初期化 → start実装 → stop実装 → ...)
- テストは pytest ベース、`tests/test_*.py` にコマンド単位で配置
- 純粋関数 (menu の `_active_session_line` 等、`utils/time` 等) はユニットテスト必須
- CI (`.github/workflows/ci.yml`) で pytest + ruff + Codecov アップロード

## リリース・タグ打ち手順
バージョン情報は 2 箇所に存在する。タグ打ち前に **両方** を揃えること:

1. `pyproject.toml` の `[project].version`
2. `src/task_recorder_cui/__init__.py` の `__version__`

`tsk --version` は `__init__.py` を参照するため、ここを忘れると「pyproject は 1.0.0 なのに `tsk --version` が 0.1.0」のような乖離が起きる。

タグ打ち時のチェックリスト:
- [ ] 上記 2 箇所を新バージョンに更新
- [ ] `pip install -e .` で再インストール後、`tsk --version` が新バージョンを返すことを確認
- [ ] `chore(release): version を X.Y.Z に bump` でコミット
- [ ] dev → main の release PR をマージ
- [ ] `git tag vX.Y.Z` / `git push origin vX.Y.Z`