# タイマー機能 設計書 (Phase 2.1)

- 作成日: 2026-04-15
- 対象バージョン: v1.1.0 (予定)
- 対象プロジェクト: task-recorder-cui
- 関連 spec: [2026-04-15-i18n-design.md](2026-04-15-i18n-design.md) (並列実装)

## 1. スコープと位置づけ

### やること
- 記録セッションに **任意時間の単発タイマー** を設定できる
- タイマー経過時に Windows 側スピーカーから音を鳴らす
- `tsk` メニュー起動中は **プログレスバー** と **発火時 5 秒点滅** で視覚通知
- `tsk` 閉じている時は **Windows デスクトップ通知** (MessageBox) で発火を知らせる
- 音ファイル、バー色、言語、通知 ON/OFF を設定可能にする

### やらないこと (Phase 2.1 スコープ外)
- **ポモドーロタイマー** (固定 25min/5min 繰り返しサイクル) — `CLAUDE.md` の「やらないこと」に従い引き続き対象外
- 複数タイマーの同時設定 (1 セッション 1 タイマー)
- タイマー履歴の閲覧 UI (DB には残すが一覧コマンドは作らない)
- 音量調整 (`powershell.exe` 経由の `Media.SoundPlayer` は WAV 側音量に依存、複雑化するため見送り)
- Windows タスクスケジューラ連携 (WSL セッション跨ぎの永続化は Phase 2.2 以降で検討)

### CLAUDE.md の改定点
本 spec 確定と同じコミット (または直後のコミット) で、`CLAUDE.md` を以下のように更新する:

- 「やらないこと」節から「ポモドーロタイマー機能 (別ツール)」は **残す** (繰り返しサイクルは引き続き NG)
- 新設する「Phase 2.1 実装済み機能」節に **任意時間タイマー** を明記
- 「データモデル」節の `records` に `timer_target_at` / `timer_fired_at` カラムを追記
- 設定ファイル (`~/.config/tsk/config.toml`) の章を新設

## 2. アーキテクチャ

### 2.1 生存範囲の決定

タイマー発火プロセスは **WSL シェル / ターミナル開きっぱの運用を前提** に、`tsk` CLI 終了後も生き残る detach subprocess 方式 (A) を採用する。

- 採用: A (detach subprocess)
- 却下: systemd-run (B, WSL systemd 依存), Windows タスクスケジューラ (C, オーバースペック), at (D, atd 依存)

制約: WSL を完全に shutdown するとタイマーは失効する。この旨を `tsk --help` / README / `tsk config` に明記。

### 2.2 プロセス構成

```
ユーザ端末 (tsk CLI)
    │
    │ (1) tsk start --timer 2h30m
    │ (2) records に timer_target_at 書き込み
    │ (3) Popen で detach child
    ▼
daemon 子プロセス (tsk _timer-daemon)
    │
    │ (a) 1 秒 polling で DB 再読込
    │ (b) timer_target_at を過ぎたら sound 再生 + notify
    │ (c) timer_target_at が NULL / fired_at が set されたら自殺
    ▼
  sound + notification
```

- daemon は PID 管理せず、DB を信頼する **自殺方式 (γ)** を採用する
- daemon 起動時に `setsid` で新セッションリーダーにし、親の tsk CLI が終了しても生き続けるようにする
- 子プロセスの標準入出力は `/dev/null` にリダイレクト

### 2.3 レイヤ

```
cli.py / menu.py (UI 層)
    ↓ --timer, tsk timer set|cancel, プロンプト
commands/timer.py (timer set / cancel のハンドラ)
commands/start.py (--timer フラグ対応)
    ↓
services/timer.py (新設 — タイマー計算、daemon 起動、音・通知の抽象)
    ↓
repo.py (set_timer_target / clear_timer_target / mark_timer_fired)
    ↓
db.py (マイグレーション、sqlite3)
```

- 音と通知の実装は `services/timer.py` 内の 2 関数にまとめ、テスト時はモックする
- `commands/` から直接 subprocess や powershell を叩かない (サービス層経由)

## 3. データモデル

### 3.1 records テーブルの変更

| カラム (追加) | 型 | 用途 |
|---|---|---|
| `timer_target_at` | TEXT (ISO8601, nullable) | タイマー発火予定時刻 (UTC)。NULL = タイマー未設定 |
| `timer_fired_at` | TEXT (ISO8601, nullable) | 実際に発火した時刻。NULL = 未発火 |

- キャンセル: `timer_target_at` を NULL に戻す。`timer_fired_at` はそのまま。
- 完了済みセッションでもカラムは残る (集計には影響なし)
- DB 上のタイマー時刻は **常に UTC ISO8601 文字列**。表示時にローカル変換

### 3.2 マイグレーション

`PRAGMA user_version` ベースの逐次適用。`db.py` に `migrate()` 関数を新設し、`initialize()` から呼ぶ。

```python
# db.py (擬似コード)
def migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < 1:
        with conn:
            conn.execute("ALTER TABLE records ADD COLUMN timer_target_at TEXT")
            conn.execute("ALTER TABLE records ADD COLUMN timer_fired_at TEXT")
            conn.execute("PRAGMA user_version = 1")
```

- 既存ユーザ DB: ALTER が 1 回走る (数ミリ秒)、既存レコードの新カラムは NULL (タイマー未使用扱い)
- 冪等性: `user_version` チェックで再実行を防ぐ
- ロールバック: 明示的 down migration は作らない (SQLite で DROP COLUMN は重い)。代わりに v0 に戻す場合は新カラム値を無視するだけで実害なし

## 4. 設定ファイル

### 4.1 配置と書式

- パス: `~/.config/tsk/config.toml` (XDG Base Directory 準拠、`TSK_CONFIG_PATH` で上書き可能)
- 書式: TOML
- 読み込み: Python 3.11+ 標準の `tomllib`
- 書き込み: **手書きの簡易シリアライザ** (`config.py` 内 `dump_toml()` 関数)。設定項目数が少なく、値の型も str/bool/int のみのため外部依存 (`tomli-w` 等) を追加しない

### 4.2 スキーマ

```toml
[timer]
enabled = true                                      # false ならタイマー機能全体を無効化
sound_path = "/mnt/c/Windows/Media/Alarm01.wav"     # 発火時に鳴らす WAV ファイル
notify_when_closed = true                           # tsk 閉じてる時のデスクトップ通知

[ui]
lang = "ja"              # ja / en、未設定なら LANG 環境変数から推定
bar_color = "cyan"       # rich カラー名 (red/green/blue/magenta/yellow/cyan/white 等)
bar_style = "solid"      # solid / rainbow / gradient
```

- デフォルト値はコード側 `config.py` に定義。設定ファイルが無ければデフォルトで動く
- `tsk` 初回起動時に `~/.config/tsk/config.toml` が無ければ作成しない (デフォルト動作、明示的に `tsk config set` で初めて生成)

### 4.3 CLI

- `tsk config list` — 全設定を現在値で表示
- `tsk config get <key>` — 単一キー取得 (`timer.sound_path`)
- `tsk config set <key> <value>` — 書き込み
- `tsk config reset <key>` — デフォルトに戻す (= 該当キー削除)

### 4.4 パス自動変換 (WSL2 対応)

`tsk config set timer.sound_path <value>` で入力を解析:

| 入力パターン | 処理 |
|---|---|
| `C:\Windows\Media\...` (`[A-Za-z]:\\...`) | `wslpath -u` で `/mnt/c/...` に変換して保存 |
| `\\wsl$\...` (UNC パス) | `wslpath -u` で変換 |
| `/mnt/c/...`, `/home/...`, `~/...` (POSIX) | そのまま保存 (展開は読み込み時に `Path.expanduser`) |
| 存在しないパス | エラー表示して保存拒否 |

- `wslpath` が無い環境 (非 WSL) では Windows パスは拒否、POSIX のみ許可
- 読み込み時は `Path(config['timer']['sound_path']).expanduser()` で解決

## 5. タイマー入力 UX

### 5.1 入力チャンネル

- **インタラクティブメニュー**: description 入力後にプロンプト「タイマー (例: 2h30m、空欄でスキップ): 」
- **CLI フラグ**: `tsk start <category> "<desc>" --timer 2h30m`
- **後付け**: `tsk timer set 30m` (記録中セッションに付与)
- **キャンセル**:
  - `tsk timer cancel` サブコマンド
  - メニューの「タイマー取消」項目 (記録中 && タイマー設定済の時だけ表示)
  - `tsk stop` 時に自動キャンセル (ended_at と同時に target_at を NULL に)

### 5.2 時間書式

受理する入力:

| 入力 | 分換算 |
|---|---|
| `2h30m` | 150 |
| `30m` | 30 |
| `2h` | 120 |
| `150m` | 150 |
| `150` | 150 (m 省略) |

正規表現: `^(?:(\d+)h)?(?:(\d+)m?)?$` (全部一致、空はエラー)

### 5.3 バリデーション

- 最小 1 分以上 (`0m` や `-5m` はエラー)
- 最大は設けない (ユーザ自己責任)
- 既にタイマー設定済のセッションに `tsk timer set` で再設定する場合は確認プロンプト or `--force` 必須

## 6. プログレスバーとメニューリフレッシュ

### 6.1 表示場所

- `tsk` メニュー起動中の「現在」行の下
- `tsk now` コマンドの出力末尾

### 6.2 表示条件

| 状態 | 表示 |
|---|---|
| セッションなし | バー無し (現状通り) |
| セッションあり、タイマーなし | 経過時間のみ (現状通り) |
| セッションあり、タイマーあり、未発火 | バー + `<経過>m / <目標>m (<%>%)` |
| セッションあり、タイマーあり、発火済 | バー満タン + 5 秒点滅 + 「タイマー経過」表示 |

例:
```
現在: [開発] ObatLog Firestore (1h20m経過)
[=================>          ] 1h20m / 2h30m (53%)
```

### 6.3 リフレッシュ方式

採用: **α (1 秒 tick 自動更新)**。rich の `Live` を使い、キー入力は別スレッド or `questionary.ask_async`。

- メニュー起動中は 1 秒ごとに画面再描画
- 描画フレームは pure 関数 `render_menu_frame(now, conn, config) -> str` に切り出してテスト可能に
- CPU 負荷: 1 秒 tick + DB 1 クエリ = 無視できるレベル

### 6.4 発火時点滅

- rich の `blink` スタイル + バー色反転
- **5 秒点滅して自動的に通常表示に戻る**
- ユーザ操作なしで戻る (鬱陶しさ回避)
- 点滅中でもメニュー操作は可能 (1-9 キーは効く)

### 6.5 バースタイル

| `bar_style` 値 | 挙動 |
|---|---|
| `solid` (デフォルト) | `bar_color` で単色塗り |
| `rainbow` | tick ごとに色をシフト (赤→橙→黄→緑→青→紫→赤...、1 秒ずつローテート) |
| `gradient` | バーの左端と右端で色が違う静的グラデーション |

- 実装は rich の `Text` に色指定、`Live` 内で毎 tick 生成
- 不正値はエラーにして `solid` にフォールバック

## 7. 音と通知

### 7.1 音の再生

全発火パターンで共通:

```bash
powershell.exe -c "(New-Object Media.SoundPlayer '<sound_path>').PlaySync()"
```

- `sound_path` は WSL パス (`/mnt/c/...`) → PowerShell 呼び出し時に Windows パス (`C:\...`) に変換して渡す (`wslpath -w`)
- `PlaySync()` はブロッキングだが daemon 子プロセス内で実行するので UI は影響受けない
- 失敗時 (ファイルなし、powershell.exe 無し) はログファイル `~/.local/share/tsk/timer.log` に記録して継続

### 7.2 デスクトップ通知 (tsk 閉じている時)

`config.timer.notify_when_closed = true` かつ daemon が発火した瞬間、tsk のメニュープロセスが存在しない場合に:

```bash
powershell.exe -c "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('<msg>', 'task-recorder-cui')"
```

- 音と同時に MessageBox が画面に出る
- 非依存 (BurntToast 等の外部モジュール不要)
- Toast 通知との比較: MessageBox はウィンドウが出るので見逃しにくい、ユーザが「閉じる」を押すまで残る

### 7.3 tsk メニュー起動中の扱い

- メニュー起動中は MessageBox は **出さない** (代わりにバー点滅 + 音)
- メニュー起動判定: `~/.local/share/tsk/menu.lock` (tsk メニュー開始時に作成、終了時に削除、PID 記録)
- daemon は発火前にこの lock を読み、PID のプロセスが生きてるかチェック

## 8. エッジケース

| ケース | 挙動 |
|---|---|
| `tsk timer set 0m` | バリデーションエラー「1 分以上を指定してください」 |
| システムスリープ中にタイマー経過 | 起床後の次の tick で `target_at < now()` を検出、即発火 |
| 壁時計を手動変更 (NTP ズレ含む) | 許容。秒単位のズレは影響小、大幅変更時は発火タイミングが前後する |
| daemon が kill されて DB に残ったまま | 次回 tsk 起動時に初期化フックが `target_at < now && fired_at IS NULL` を検出 → `timer.log` に「ゾンビタイマー検出」記録 + その場で即発火 (音 + 通知) してから `fired_at` をセット |
| 2 端末で同時に tsk 起動 | 「記録中セッションは 1 個」制約は現状通り。メニューは 1 秒 tick で DB を再読込するので他端末の操作もすぐ反映される |
| タイマー設定済セッションを `tsk add` で新規追加 | `tsk add` は過去レコード追加なのでタイマー対象外、`--timer` フラグは受け付けない |

## 9. 依存ライブラリとテスト

### 9.1 追加依存

- なし (標準ライブラリ `subprocess`, `tomllib`, `sqlite3` と既存 `rich`, `questionary` のみで実装)
- dev deps: 既存の `pytest`, `pytest-cov` を継続使用

### 9.2 テスト戦略

| 対象 | テスト種別 | 備考 |
|---|---|---|
| 時間書式パーサ (`parse_timer_spec`) | ユニット | `2h30m` → 150、異常系 |
| マイグレーション (`migrate`) | ユニット | v0 DB → v1 に上がるか、冪等性、既存レコード影響なし |
| daemon の DB polling ロジック | ユニット | target_at NULL で自殺、過去時刻で発火、future 時刻で継続 |
| 音・通知関数 | ユニット | subprocess.run をモック、呼び出し引数を検証 |
| パス変換 | ユニット | Windows パス / WSL パス / 展開 / 存在チェック |
| メニューフレーム描画 (`render_menu_frame`) | ユニット | タイマー無し / 進行中 / 発火済の 3 パターン |
| E2E (tsk CLI) | 統合 | temp DB に対して `tsk start --timer` → sleep → 発火ログ確認 |

- 音・通知の実物起動は CI でスキップ (`@pytest.mark.skipif(not _is_wsl_with_powershell())`)
- 既存カバレッジ 80% 基準を維持

## 10. 実装順序 (writing-plans 向けガイド)

1. `db.py` に `migrate()` 関数を追加、`user_version` 導入、タイマー系カラム追加
2. `config.py` (新設) — TOML 読み書き、デフォルト値、`tsk config` ハンドラ
3. `services/timer.py` (新設) — 時間パーサ、daemon 起動、音・通知
4. `repo.py` — タイマー系 CRUD 追加
5. `commands/timer.py` (新設) — `set` / `cancel` サブコマンド
6. `commands/start.py` — `--timer` フラグ対応
7. `menu.py` — プロンプト追加、プログレスバー描画、`Live` 導入
8. `cli.py` — 新サブコマンドの登録
9. `CLAUDE.md` 更新 (Phase 2.1 明記、カラム追記、設定ファイル章追加)
10. README 更新 (新機能・設定例)

各ステップでテスト追加。

## 11. 実装時に検証が必要な技術前提

本 spec は以下を前提にしているが、実装ブランチの最初のコミットでプロトタイプ検証し、仕様にズレがあれば本 spec を修正する。

- **`wslpath` の引数**: `-u` (Windows → POSIX), `-w` (POSIX → Windows)、`-a` は絶対パス。man ページで最終確認
- **`powershell.exe` のクォート**: シングルクォート内のシングルクォートは `''` でエスケープ、パスに含まれる空白・日本語は動作検証
- **プロセス detach 方式**: `subprocess.Popen(..., start_new_session=True, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)` を第一候補とする。動かなければ `os.fork` + `os.setsid` に落とす
- **rich.Live × questionary**: 公式サポート外なので、実装初期にメニュー画面プロトタイプで `Live` context 内で select プロンプトが動くか確認。動かない場合は `prompt_toolkit` 直呼びに切り替える
