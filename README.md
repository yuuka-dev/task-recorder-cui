# task-recorder-cui

[![CI](https://github.com/yuuka-dev/task-recorder-cui/actions/workflows/ci.yml/badge.svg)](https://github.com/yuuka-dev/task-recorder-cui/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yuuka-dev/task-recorder-cui/branch/main/graph/badge.svg)](https://codecov.io/gh/yuuka-dev/task-recorder-cui)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)

> **一言で説明**: 日々の時間の使い方を記録し、週平均・月平均で可視化するCUIツール。タスク管理ではなく「時間記録」に特化しています。

## 概要

### なぜ作ったのか

Toggl などのタイムトラッキングツールは多機能ですが、項目が多すぎて続かないことがあります。本ツールは「何を・何時間・いつやったか」を **極限まで削ぎ落としたコマンド** で記録し、週平均・月平均を数字だけで見ることに特化しています。

毎日使うのが苦にならない軽さを最優先に設計しました。

## 主な機能

- `tsk start` / `tsk stop` で時間を記録（ストップウォッチ形式）
- `tsk add` で事後に手動追加
- `tsk today` / `tsk week` / `tsk month` で集計を表示
- カテゴリは自由に追加・アーカイブ可能（初期は `game` / `study` / `dev` の3つ）
- サブコマンドなしで起動すると階層型インタラクティブメニュー
- **タイマー機能**: `tsk start --timer 2h30m` で作業開始と同時にタイマー設定。
  指定時間後に Windows 側スピーカーで音を鳴らす。メニュー起動中はプログレスバーで
  可視化、閉じている時はデスクトップ通知で知らせる。

## 技術スタック

| カテゴリ | 技術 |
|---|---|
| 言語 | Python 3.11+ |
| データストア | SQLite（標準ライブラリ `sqlite3`） |
| CLI | `argparse` |
| 出力整形 | `rich` |
| インタラクティブ選択 | `questionary` |
| パッケージ管理 | `pyproject.toml` + `pip install -e .` |

## はじめ方

### 前提条件

- Python 3.11 以上
- 動作確認環境: WSL2 Ubuntu（他のLinux/macOSでも動作するはず）

### セットアップ

```bash
git clone https://github.com/yuuka-dev/task-recorder-cui.git
cd task-recorder-cui
pip install -e ".[dev]"
```

インストール後、`tsk` コマンドが使えるようになります。データは `~/.local/share/tsk/records.db` に保存されます。

### テスト / カバレッジ

```bash
pytest                                                  # 全テスト実行
pytest --cov=task_recorder_cui --cov-report=term        # カバレッジ付きで実行
```

dev 依存関係を更新した場合は `pip install -e ".[dev]"` を再実行してください。

## 基本的な使い方

### 記録を開始する

```bash
tsk start dev "ObatLog Firestore 実装"
```

### 記録を停止する

```bash
tsk stop
```

### 今日の記録を確認する

```bash
tsk today
```

出力例:

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

### 事後に手動で追加する

```bash
tsk add study 45 "ABC B問題"
```

### 週次・月次サマリを見る

```bash
tsk week   # 直近7日
tsk month  # 直近30日
```

### インタラクティブメニュー

サブコマンドなしで起動すると、階層メニューから操作できます。

```bash
tsk
```

```
┌─────────────────────────────────────┐
│ tsk - task recorder                 │
├─────────────────────────────────────┤
│ 現在: [開発] ObatLog実装 (32m経過)  │
├─────────────────────────────────────┤
│ ? 操作を選んでください              │
│   開始                              │
│   停止                              │
│   今日の一覧                        │
│   週集計                            │
│   月集計                            │
│   カテゴリ管理                      │
│   ヘルプ (CLI コマンド一覧)         │
│   終了                              │
└─────────────────────────────────────┘
```

矢印キー + Enter で選択します。Ctrl+C / ESC でいつでも安全に中断できます (記録中のセッションは保持されます)。

## CLIサブコマンド一覧

### 記録系

| コマンド | 説明 |
|---|---|
| `tsk start <category_key> ["<description>"]` | 新しいセッションを開始 |
| `tsk stop` | 記録中のセッションを終了 |
| `tsk add <category_key> <minutes> ["<description>"]` | 事後に手動で追加 |
| `tsk now` | 現在記録中のセッションと経過時間を表示 |

### 参照系

| コマンド | 説明 |
|---|---|
| `tsk today` | 今日の記録一覧＋カテゴリ別合計 |
| `tsk week` | 直近7日の日別内訳＋週合計＋平均 |
| `tsk month` | 直近30日の同様の集計 |

### カテゴリ管理

| コマンド | 説明 |
|---|---|
| `tsk cat list` | カテゴリ一覧 |
| `tsk cat add <key> "<display_name>"` | カテゴリを追加 |
| `tsk cat remove <key>` | カテゴリをアーカイブ（物理削除はしない） |
| `tsk cat restore <key>` | アーカイブから復帰 |
| `tsk cat rename <key> "<new_display_name>"` | 表示名を変更 |

> `key` は ASCII 英小文字・数字・アンダースコアのみ。過去レコードの履歴を壊さないため、削除ではなく **アーカイブ** で運用します。

### タイマー (Phase 2.1)

| コマンド | 説明 |
|---|---|
| `tsk start <cat> "<desc>" --timer 2h30m` | 開始と同時にタイマー設定 |
| `tsk timer set 30m` | 記録中セッションにタイマーを後付け |
| `tsk timer cancel` | タイマーをキャンセル |

### 設定 (Phase 2.1)

| コマンド | 説明 |
|---|---|
| `tsk config list` | 全設定を表示 |
| `tsk config get timer.sound_path` | 単一キーを表示 |
| `tsk config set ui.bar_style rainbow` | 値を更新 |
| `tsk config reset ui.bar_color` | デフォルトに戻す |

設定ファイルは `~/.config/tsk/config.toml` (`TSK_CONFIG_PATH` で上書き可)。Windows
パス (`C:\Windows\Media\Alarm01.wav`) を設定すると自動的に `/mnt/c/...` に変換されます。

## スコープ外（やらないこと）

タスク管理、クラウド同期、ポモドーロ (固定サイクル繰り返し)、タグ、優先度機能は意図的に実装しません。時間を記録することだけに集中します。

## 制約事項

- **WSL2 専用**: タイマー機能は Windows 側スピーカーから音を鳴らすため
  `powershell.exe` と `wslpath` が使える環境 (WSL2 Ubuntu 等) を前提とします。
- **WSL シャットダウンでタイマー失効**: タイマー daemon は detach された子プロセス
  として動くので `tsk` 終了後も生きますが、WSL を完全に落とすと消えます。
  永続化 (Windows タスクスケジューラ連携) は Phase 2.2 以降で検討。

## ライセンス

[MIT License](./LICENSE)
