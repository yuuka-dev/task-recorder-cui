# メニュー内リアルタイム Tick 設計書 (hotfix)

- 作成日: 2026-04-16
- 対象バージョン: v1.1.2 (hotfix)
- 対象プロジェクト: task-recorder-cui
- 親 Phase: Phase 2.2 (ただし本件は同 Phase のうち **最小 hotfix** スコープ．Textual への本格移行は別 spec で扱う)
- 関連 spec: [2026-04-15-timer-design.md](2026-04-15-timer-design.md), [2026-04-15-menu-design.md](2026-04-15-menu-design.md)

## 1. 背景と問題

`tsk` インタラクティブメニュー起動中，経過時間 (「現在: [カテゴリ] desc (32m経過)」) と
タイマーのプログレスバー (`[====>    ] 1h20m / 2h30m (53%)`) が **リアルタイムで更新されない**．
現状は `_run_loop` の先頭で `_render_header` を 1 回描画したあと `questionary.select(...)` の
入力待ちに入り，ユーザが何か選択するまで画面が凍結する．タイマーセット中にメニューを開きっぱなしに
しても残り時間やバーの伸びが視認できず，Phase 2.1 で導入した timer UX の魅力を大きく損なっている．

`CLAUDE.md` Phase 2.2 の TODO 「メニュー内 1 秒 tick」「rich.Live × questionary の本格併用」で
想定していた改善をこの hotfix で先行着手する．

## 2. スコープ

### やること
- メニュー起動中，**1 秒毎** に「現在」行とプログレスバーが自動更新される
- 既存の `render_timer_bar` / `should_flash` (発火時 5 秒点滅) のロジックはそのまま活用
- `_render_header` から「現在」行とバー行を**削除**し，それらは選択肢メニューの **直上** (HSplit 先頭) に
  リアルタイム Window として出す．タイトル・直近 5 件・「記録なし」の表示は従来通り `print_line` で
  ヘッダ出力する (起動時スナップショットとして上部に残り，スクロールで追える)

### やらないこと (本 hotfix のスコープ外)
- `tsk now` 単発出力へのバー追加 (別課題)
- Textual への全面移行 / フルスクリーン TUI 化 (次 Phase で別 spec)
- `argparse --help` の i18n (既存 Phase 2.2 TODO の別項目)
- WSL シャットダウンを跨いだタイマー永続化 (別 spec)
- カテゴリサブメニュー等，`questionary.select` 以外の箇所のリアルタイム化
  (メインメニューのみ対象，入力プロンプトに入ったら tick は自然に止まる)

## 3. アーキテクチャ

### 3.1 採用アプローチ

`questionary.select(...)` が内部で保持する `prompt_toolkit.Application` を**生成後にカスタム**する．
以下の 2 点を加える:

1. `application.refresh_interval = 1.0` — 1 秒ごとに画面を invalidate して再描画
2. `application.layout.container` を `HSplit([tick_window, 元の container])` に差し替え —
   選択肢メニューの直上にリアルタイム描画用 Window を差し込む

`tick_window` は `Window(FormattedTextControl(get_text))` で，`get_text` は呼ばれる度に
現在時刻と DB 状態を参照して 1〜2 行の ANSI テキスト (経過時間行 + バー行) を返す callable．

### 3.2 モジュール構成

```
menu.py
├ _build_tick_lines(now, conn) -> list[str]        # 新規 pure 関数
│   └ 既存の _active_session_line() と render_timer_bar() を組み合わせて 1〜2 行返す
├ _attach_tick_window(application)                  # 新規: Application を in-place で改造
│   └ refresh_interval セット + layout.container 差し替え
├ _render_header()                                  # 変更: 「現在」行とバー行を削除
└ _run_loop()                                       # 変更: _show_main_menu() 経由で Question を受け取り
                                                      _attach_tick_window でカスタム → ask() 実行
```

`_show_main_menu` は現状「選択値の文字列」を返しているが，本 hotfix では `questionary.Question` を
返すように変更し，呼び出し元が Application をカスタムしてから `.ask()` を呼ぶ．

### 3.3 tick_window の描画内容

```
現在: [開発] ObatLog実装 (33m経過)                    ← _active_session_line 相当
[=====>    ] 1h21m / 2h30m (54%)                     ← render_timer_bar 相当
```

- 記録中でない場合は 1 行 (「現在: 記録なし」) のみ
- タイマー未設定の場合は経過行のみ (バーなし)
- 発火済かつ 5 秒以内 → `should_flash=True` で既存の赤点滅が自動で反映される．これまで
  「発火時 5 秒だけ rich.Live で点滅」は `CLAUDE.md` に記述はあるが**実装はされていなかった**
  (grep で確認済)．本 hotfix で常時 tick 化することで，点滅 UX を実体化する

### 3.4 DB アクセス戦略

tick 毎 (1 秒) に `open_db()` → `find_active_record()` → `find_category()` → close を実行する．
いずれも軽量な主キー検索なので実害なし．
「1 ループ 1 回 open_db()」の原則 (memory: `feedback_single_open_db_per_loop.md`) は
`_render_header` 等の**同一描画パス内で複数回開くな**という文脈の規約であり，独立した tick
コンテキストでの再 open は別ケースとして扱う．最適化で Application 生存中に接続を使い回すのも
可能だが，複雑度が増すため本 hotfix では採用しない．

## 4. データフロー

```
メニュー起動
 └→ _render_header(print_line でタイトル / 直近を出力)      ← 静的スナップショット
 └→ _show_main_menu() が questionary.Question を返す
     └→ _attach_tick_window(q.application) で Application を改造
         ├ refresh_interval = 1.0
         └ layout.container = HSplit([tick_window, 元の container])
     └→ q.ask()                                              ← ここで入力待ち
         └ 1 秒毎に tick_window の get_text が呼ばれ
            - now_utc() を取得
            - open_db() で active / category / timer 状態を読む
            - _build_tick_lines(now, conn) が文字列を返す
            - prompt_toolkit がその領域だけ再描画 (選択肢の上)
 └→ 選択肢が返る → _dispatch(choice) へ
```

## 5. エラー処理

- `_build_tick_lines` は **pure 関数として例外を投げる責務を持つ** (正常系のみ実装し握りつぶさない)．
- 例外を握りつぶすのは `_attach_tick_window` 内の `get_text` クロージャ側．
  tick 描画中の例外 (DB lock 等) で 1 秒毎にメニューがクラッシュするのは UX 上最悪なので，
  クロージャ内で `try/except Exception` し，例外時は `""` を返して描画継続．
  プロジェクトに既存ログ機構は無いため，デバッグ出力は本 hotfix では導入しない (必要になったら別課題)．
- `_attach_tick_window` 自体の失敗はメニュー起動不能に直結するため，例外はそのまま伝播させて
  従来のスタックトレースを出す (隠蔽しない)．

## 6. テスト方針

### 新規ユニットテスト
- `_build_tick_lines(now, conn)` を pure 関数として切り出し，既存の `test_menu_pure.py` に追加
  - 記録なし → 1 要素 (「現在: 記録なし」)
  - 記録中・タイマーなし → 1 要素 (経過時間付き)
  - 記録中・タイマーあり → 2 要素 (経過行 + バー)
  - 例外ケースは `_build_tick_lines` 側では扱わない (握りつぶしは `get_text` クロージャ側の責務)

### 既存テストへの影響
- `_render_header` から「現在」行とバーを剥がすので，ヘッダ関連テストを更新 (行数の assertion を調整)
- `render_timer_bar` / `should_flash` / `_active_session_line` の pure テストは変更なし

### 手動確認項目 (TTY 依存で自動化しない)
- [ ] タイマー設定中のセッションでメニューを開き，バーが 1 秒毎に伸びる
- [ ] 「現在: …」行の「Xm経過」が 1 分刻みで進む
- [ ] タイマー発火の瞬間，5 秒間赤点滅する
- [ ] 発火後 5 秒経過で点滅が止まり「タイマー経過」太字表示に落ち着く
- [ ] 選択肢 1)〜q) のキー操作が従来通り動く (tick で入力イベントが取りこぼされない)
- [ ] Ctrl+C で安全に抜けられる

### カバレッジ
`fail_under = 100` 維持．`_attach_tick_window` / `get_text` クロージャは TTY 依存のため
`# pragma: no cover` もしくは `[tool.coverage.run].omit` に追記して除外．pure 関数
(`_build_tick_lines`) は 100% カバーする．

## 7. リスクと却下案

### 技術リスク
- **prompt_toolkit の API 変更リスク**: `Application.refresh_interval` と
  `Application.layout.container` は公開 API だが，`questionary.Question.application` に触るのは
  やや内部依存．現行版 `questionary==2.1.1` では動作確認済 (ブレインストーミング時に確認)．
  バージョン pin で緩和する (`pyproject.toml` の `questionary` を `>=2.1,<2.2` に絞る是非は
  実装時に判断)．
- **入力応答性**: `refresh_interval=1.0` による再描画で矢印キーの応答が鈍る懸念 → prompt_toolkit の
  refresh はイベントループ上で非同期に走るため同期入力はブロックしない (公式ドキュメント記載)．
  手動確認でチェック．

### 却下した代替案
- **案 B (rich.progress.Progress 別スレッド)**: stdout を questionary と奪い合うため実装が
  ANSI カーソル制御の泥沼になる．却下．
- **案 C (Textual 全面移行)**: `CLAUDE.md` の「フルスクリーン TUI は使わない」方針と衝突．
  本 hotfix のスコープを超える．次 Phase で別途 spec 起こす予定．

## 8. ブランチ・リリース

- ブランチ: `fix/menu-realtime-tick` (親 `dev`，CLAUDE.md ブランチ戦略に準拠)
- バージョン: **v1.1.2 を想定** (リリース要否・番号はユーザと実装完了時に最終判断)．
  出す場合の bump 先は 2 箇所: `pyproject.toml` + `src/task_recorder_cui/__init__.py`
- リリースフロー (出す場合): `dev` merge → `release/v1.1.2` 切って bump → `main` PR → tag push で自動発行
- CHANGELOG は README / `__init__` の version で代替 (既存運用踏襲，別途 CHANGELOG.md は持たない)

## 9. ロールアウト後の観測点

- `docs/superpowers/plans/2026-04-16-menu-realtime-tick.md` に TODO として残す:
  - Phase 2.2 本体 (Textual 移行) 着手時に，本 hotfix で追加した `_build_tick_lines` /
    `_attach_tick_window` は丸ごと置き換え対象になる．Textual 移行 PR で削除する前提でコメントを
    残しておく
- 本 hotfix 後にカテゴリ管理メニュー (`_cat_submenu`) からも同等の tick を出す要望が出たら，
  `_attach_tick_window` を再利用できるよう最初から汎用化しておく
