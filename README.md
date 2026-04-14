# task-recorder-cui

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
│ 1) 開始                             │
│ 2) 停止                             │
│ 3) 今日の一覧                       │
│ 4) 週集計                           │
│ 5) 月集計                           │
│ 6) カテゴリ管理                     │
│ q) 終了                             │
└─────────────────────────────────────┘
```

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

## スコープ外（やらないこと）

タスク管理、クラウド同期、通知、グラフ描画、ポモドーロ、タグ、優先度機能は意図的に実装しません。時間を記録することだけに集中します。

## ライセンス

[MIT License](./LICENSE)
