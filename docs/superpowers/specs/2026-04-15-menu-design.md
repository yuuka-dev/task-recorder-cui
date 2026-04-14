# インタラクティブメニュー (Phase 6) 設計書

- 作成日: 2026-04-15
- 対象ブランチ: `feature/menu`
- 関連ドキュメント: ルートの `CLAUDE.md` (Phase 6 / メニュー構造モックアップ)

## 目的

`tsk` をサブコマンドなしで起動した際に、`questionary` ベースの階層メニューで記録系・参照系・カテゴリ管理・コマンドヘルプに到達できるようにする。CLI サブコマンドのラッパーとして機能し、独自のビジネスロジックは持たない。

## 非対象 (スコープ外)

- メニューからの過去レコード編集 (将来拡張候補)
- キーボードショートカットの独自割当 (questionary 既定の矢印/Enter/Ctrl+C に乗る)
- カラーテーマのカスタマイズ
- メニュー状態の永続化 (セッション中のみ)
- i18n (日本語固定)

## アーキテクチャ

- **新規ファイル**: `src/task_recorder_cui/menu.py`
- `cli.py` の `args.command is None` 分岐のスタブ (`_not_implemented("インタラクティブメニュー", _MENU_PHASE)`) を `menu.run()` 呼び出しに差し替える
- `menu.py` は以下の 2 層構造:
  - **pure 関数**: ステータス行生成・直近レコード整形・ヘルプテキスト保持。DB 読み取りに依存する関数も含むが、副作用はプリントしない
  - **UI 層**: `questionary.select` / `questionary.text` / `questionary.confirm` と `print_line` を呼ぶ薄い層。ループは UI 層に集約
- 既存コマンド (`commands.start.run` 等) を import して再利用。menu.py は DB を直接触らず、必要なら `repo` 経由 (ステータス行と直近取得のみ)

## メインループ

```
def run() -> int:
    while True:
        _render_header()             # 現在のセッション + 直近 5 件
        choice = _show_main_menu()   # questionary.select の戻り値
        if choice is None or choice == "quit":
            return 0
        try:
            _dispatch(choice)
        except KeyboardInterrupt:
            print_line("(中断しました)")
            continue
        _pause()                     # Enter 待ち。ユーザが内容を読む時間を確保
```

- `_show_main_menu()` は選択時の Ctrl+C / ESC に対して `None` を返すのでそれを終了扱い
- ループ中の Ctrl+C は continue してメニューを再描画
- 非インタラクティブ環境 (パイプ経由等) で `questionary` が失敗する場合は `KeyboardInterrupt` ではなく例外で落ちてよい (MVP)

## ヘッダ描画

```
tsk - task recorder

現在: [開発] ObatLog実装 (32m経過)      # 記録中
または
現在: 記録なし

直近:
  [ゲーム] HOI4            2h30m  2時間前
  [開発]   フォント改造    1h15m  5時間前
  [学習]   ABC B問題       45m    昨日
```

pure 関数:

- `_active_session_line(now: datetime) -> str`
  - アクティブセッションがあれば `現在: [<display>] <desc> (<経過>経過)` 形式
  - なければ `現在: 記録なし`
- `_recent_records_lines(limit: int = 5) -> list[str]`
  - 直近 `limit` 件を新しい順で取得し、`[<display>]<padding><desc><padding><duration>  <relative>` 形式で整形
  - description が NULL のときは空文字扱い
  - display_name の幅揃えは最大長を基準に space padding
- `_humanize_relative(when: datetime, now: datetime) -> str` (`utils/time.py`)
  - `NmNs` → 「N分前」、`NhNm` → 「N時間前」、昨日 → 「昨日」、2 日以上前 → 「N日前」
  - 未来は MVP では発生しない前提 (必要なら "まもなく" でも可)

## メインメニュー項目

順番と value:

| 表示 | value | 条件 |
|---|---|---|
| 開始 | `start` | 常時 |
| 停止 | `stop` | 記録中のみ有効 (非記録時は `Choice(disabled="(記録中のセッションがありません)")`) |
| 今日の一覧 | `today` | 常時 |
| 週集計 | `week` | 常時 |
| 月集計 | `month` | 常時 |
| カテゴリ管理 | `cat` | 常時 |
| ヘルプ (CLI コマンド一覧) | `help` | 常時 |
| 終了 | `quit` | 常時 |

## アクションディスパッチ

| value | 処理 |
|---|---|
| `start` | (1) active カテゴリを `questionary.select` で選ばせる (2) `questionary.text` で description 入力 (空文字 → None) (3) `commands.start.run(key, desc)` |
| `stop` | `commands.stop.run()` を直接呼ぶ |
| `today` | `commands.today.run()` |
| `week` | `commands.week.run(calendar=False)` (直近 7 日) |
| `month` | `commands.month.run(calendar=False)` (直近 30 日) |
| `cat` | カテゴリサブメニュー (後述) |
| `help` | 静的ヘルプテキストを `print_line` で表示 |
| `quit` | return 0 |

アクション完了後: `_pause()` で Enter 待ち → ループ先頭に戻る。`quit` は pause しない。

## 開始フローの詳細

1. `repo.list_categories(active_only=True)` で active カテゴリを取得
2. 0 件ならば `print_line("有効なカテゴリがありません。先に『カテゴリ管理 → 追加』してください。")` して戻る
3. `questionary.select("カテゴリを選んでください", choices=[...])` で Choice ごとに `title = f"{display_name} ({key})"`, `value = key` を渡す
4. 選択キャンセル (`None`) ならば戻る
5. `questionary.text("何をしましたか (任意、空欄可)", default="")` で description。空文字 → None
6. `commands.start.run(key, desc)` の終了コードをそのまま返す (画面にはコマンドが出すメッセージが出る)

## カテゴリ管理サブメニュー

メインと同じく `questionary.select`、戻るオプションあり:

```
一覧表示 (list)
追加 (add)
アーカイブ (remove)
アーカイブから復帰 (restore)
表示名を変更 (rename)
← 戻る (back)
```

各アクション:

- **list**: `commands.cat.list_categories(active_only=False, archived_only=False)` を呼ぶ (フラグ無しで全件)
- **add**:
  1. `questionary.text("新しいカテゴリキー (ASCII 英小文字・数字・_)")` で key
  2. `questionary.text("表示名")` で display_name
  3. `commands.cat.add_category(key, display_name)`
- **remove**:
  1. active カテゴリを `questionary.select` で選択 (0 件なら警告して戻る)
  2. `questionary.confirm(f"{display_name} ({key}) をアーカイブしますか？", default=False)` で確認
  3. `commands.cat.remove_category(key)`
- **restore**:
  1. archived カテゴリを `questionary.select` で選択 (0 件なら警告して戻る)
  2. `commands.cat.restore_category(key)`
- **rename**:
  1. active カテゴリを選択
  2. `questionary.text("新しい表示名", default=現在の display_name)` で入力
  3. `commands.cat.rename_category(key, new_display_name)`

サブメニューも **ループ**。`back` 選択でメインメニューへ戻る。

## ヘルプテキスト (静的)

menu.py に定数 `_HELP_TEXT` として保持:

```
tsk コマンド一覧

記録:
  tsk start <cat> ["<desc>"]             新しいセッションを開始
  tsk stop                                記録中のセッションを終了
  tsk add   <cat> <分> ["<desc>"]        事後に手動で追加
  tsk now                                 記録中セッションを表示

集計:
  tsk today                               今日の一覧
  tsk week  [--calendar]                  直近7日 / 今週
  tsk month [--calendar]                  直近30日 / 今月
  tsk range --from YYYY-MM-DD --to YYYY-MM-DD   任意期間
  tsk all                                 全累計

カテゴリ:
  tsk cat list [--active|--archived]
  tsk cat add     <key> "<表示名>"
  tsk cat remove  <key>
  tsk cat restore <key>
  tsk cat rename  <key> "<新表示名>"

その他:
  tsk --version / --help
  tsk (引数なし)                          このメニューを起動
```

- 手書きテキストで保持 (argparse の format_help は日本語・階層表示で見づらい)
- 表示は `print_line(_HELP_TEXT)` → `_pause()` でメニューへ戻る

## エラー処理・中断

- メニュー・プロンプト中の Ctrl+C / ESC は `questionary` が `None` を返す → ループで吸収して続行
- アクション実行中の Ctrl+C は `KeyboardInterrupt` としてキャッチし、「(中断しました)」を出してループ続行
- 記録中のセッションはメニュー終了時も保持される (DB に書き込み済みなので menu.py は何もしない)
- 別ターミナルから `tsk stop` で終了可能な挙動は既存コマンドにより担保される

## テスト方針

questionary の UI 部分は端末入出力のセットアップが重いので、以下の 2 層:

### 1. pure 関数の単体テスト (主)

`tests/test_menu_pure.py` に追加:

- `_active_session_line(now)`:
  - 記録中で description あり / なし
  - 記録なし
  - 経過時間の整形 (`32m` / `1h 05m`)
- `_recent_records_lines(limit)`:
  - limit 件数で切られる
  - 0 件の場合は空リスト
  - description が NULL
  - display_name 幅揃え
- `_humanize_relative(when, now)`:
  - N 分前 / N 時間前 / 昨日 / N 日前
  - 閾値境界ケース

### 2. スモークテスト (最小 1 本)

`tests/test_menu_smoke.py`:

- `monkeypatch.setattr("task_recorder_cui.menu._show_main_menu", lambda: "quit")` で差し替え、`menu.run()` の戻り値が `0` であること
- `questionary.select` を直接モックする必要がないように `_show_main_menu()` を薄い関数として分離

UI フロー全体の E2E は手動確認 (ローカルでの動作確認) で代替する。MVP はここまで。

## 変更ファイル一覧

| パス | 種別 | 概要 |
|---|---|---|
| `src/task_recorder_cui/menu.py` | 新規 | メニュー本体 (pure + UI 層) |
| `src/task_recorder_cui/cli.py` | 更新 | `args.command is None` 分岐を `menu.run()` 呼び出しに差し替え、`_not_implemented` / `_MENU_PHASE` 定数を削除 |
| `src/task_recorder_cui/utils/time.py` | 更新 | `humanize_relative(when, now) -> str` を追加 |
| `src/task_recorder_cui/repo.py` | 更新 (必要最小) | `list_recent_records(conn, limit)` を新規追加 (`ORDER BY started_at DESC LIMIT N`、ended_at が NULL の記録中セッションは除外) |
| `tests/test_menu_pure.py` | 新規 | pure 関数のテスト |
| `tests/test_menu_smoke.py` | 新規 | menu.run() スモーク |
| `tests/test_cli.py` | 更新 | 引数なし起動の挙動に関する既存テストがあれば menu が呼ばれる想定に調整 |
| `README.md` | 更新 (軽め) | 「サブコマンドなしでメニュー」の節を最新挙動に揃える (既に大枠は書かれているので表現調整のみ) |

## 成功基準

- [ ] `tsk` (引数なし) でヘッダ + メニューが表示される
- [ ] 矢印キー + Enter で「開始」が走り、カテゴリと description を経て `tsk start` と同じ DB 書き込みが行われる
- [ ] 「停止」は記録中でなければグレーアウト
- [ ] 「ヘルプ」で CLI コマンド一覧が表示されメニューに戻れる
- [ ] カテゴリ管理サブメニューで list/add/remove/restore/rename が全て動く (remove は confirm 要求)
- [ ] Ctrl+C でメニュー・プロンプト中にクラッシュしない
- [ ] `pytest --cov` でカバレッジが既存水準 (90%+) を維持

## リスク / 留意点

1. **questionary の端末依存**: 非インタラクティブ環境 (パイプ・CI) で `tsk` を引数なしで叩かれると異常終了する可能性。CI では不要なので問題無いが、テスト実行時に `pytest` 経由で menu を呼び出さないよう pure 関数経由に倒す
2. **カテゴリ 0 件の開始フロー**: active カテゴリが 1 件も無い状態で「開始」を選ばれたら、エラーではなく案内メッセージで戻す。`commands.start.run` に到達させない
3. **Ctrl+C の挙動差異**: questionary のバージョンによっては `None` ではなく `KeyboardInterrupt` を送出することがある。両方受けるようラップする
4. **テスト用 DB のセッション汚染**: スモークテストは `TSK_DB_PATH` を tmp_path に切り替える既存のフィクスチャを踏襲する
5. **rename のデフォルト値**: `questionary.text(default=現在名)` で初期値を入れると、現在値を消さずに編集しにくいので空文字 default + placeholder 案内の方が親切かもしれないが、MVP は default= 現在名 で確定

## 実装順 (ざっくり)

1. `utils/time.py` に `humanize_relative` 追加 + 単体テスト
2. `repo` に `list_recent_records(limit)` 追加 (無ければ) + 単体テスト
3. `menu.py` の pure 関数 (`_active_session_line`, `_recent_records_lines`) 追加 + 単体テスト
4. `_HELP_TEXT` 定数とヘルプアクション追加
5. UI 層 (メインループ、カテゴリサブメニュー、開始フロー、停止、各集計、ヘルプ、終了) を実装
6. `cli.py` のスタブを `menu.run()` 呼び出しに差し替え
7. スモークテスト追加、ローカルで `tsk` を手動起動し一通り動くこと確認
8. push → PR → Actions 完走 → マージはユーザが実施
