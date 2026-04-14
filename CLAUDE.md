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
- SQLite (標準ライブラリのsqlite3、追加依存なし)
- CLI: argparse
- インタラクティブメニュー: input() で実装 (TUIライブラリは使わない)
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

### 設計メモ

- **key と display_name を分ける理由**: 集計出力時に日本語表示できる。将来i18n対応したくなっても崩れない。archive後にkeyが衝突しない。
- **category_key は TEXT で保持 (正規化しない)**: CUI段階ではJOINレスで扱える方が実装がシンプル。Android版移植時にRoomのリレーションで綺麗にすることは可能。
- **archived は物理削除しない**: 過去レコードが参照しているkeyを消すと履歴集計が壊れるため。アーカイブはメニュー表示から消えるだけで、`tsk week` 等の集計には含まれ続ける。
- **時刻は全てISO8601文字列で保存、コード内ではdatetime(timezone-aware)で扱う**。

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
│       ├── init.py
│       ├── main.py
│       ├── cli.py              # argparse エントリポイント
│       ├── menu.py             # インタラクティブメニュー
│       ├── db.py               # SQLite初期化、マイグレーション
│       ├── models.py           # dataclass定義
│       ├── io.py               # 出力用関数
│       ├── commands/
│       │   ├── start.py
│       │   ├── stop.py
│       │   ├── add.py
│       │   ├── now.py
│       │   ├── today.py
│       │   ├── week.py
│       │   ├── month.py
│       │   └── cat.py
│       └── utils/
│           ├── time.py         # 時刻フォーマット、duration計算
│           └── validate.py     # keyの検証等
└── tests/
└── (最小限のテストのみ)
```
## やらないこと (スコープ外)

- タスク管理機能 (これは時間記録ツール、ToDoではない)
- カテゴリの物理削除 (archiveで十分)
- クラウド同期
- 通知機能
- グラフ描画 (CLIの数字表示のみ)
- PC総稼働時間の自動取得 (ActivityWatch等の外部ツール連携は後回し)
- タグ機能 (カテゴリ1つで十分)
- 優先度機能 (時間記録に優先度は不要)
- ポモドーロタイマー機能 (別ツール)

## 将来の拡張候補 (MVP後、やるかは未定)

- CSVエクスポート (`tsk export --from 2026-04-01 --to 2026-04-30`)
- Android版 (同じスキーマをRoomで実装)
- Webダッシュボード (ObatLogと同じ技術スタックで、Next.js + Firestore)
- ActivityWatch連携による稼働時間比率表示
- 過去レコードの編集 (`tsk edit <id>`)

## ライセンス
MIT (予定、pyproject.tomlに記載)

## 開発ノート
- 最初のコミットはCLAUDE.mdとpyproject.tomlのみ、それから実装に入る
- コミットは機能単位で小さく切る (DB初期化 → start実装 → stop実装 → ...)
- テストは各コマンドの正常系1ケースずつで十分、MVPでは網羅性より動くことを優先