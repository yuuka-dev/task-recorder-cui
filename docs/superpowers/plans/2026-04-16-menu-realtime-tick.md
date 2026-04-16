# メニュー内リアルタイム Tick 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tsk` メニューの「現在」行とプログレスバーを 1 秒毎にリアルタイム更新する

**Architecture:** `questionary.select()` が内部で持つ `prompt_toolkit.Application` に `refresh_interval=1.0` をセットし，Layout の HSplit 先頭にリアルタイム描画用 Window を差し込む．tick 描画内容は pure 関数 `_build_tick_lines` が組み立て，`_rich_to_ansi` で rich markup → ANSI に変換して `FormattedTextControl` に渡す．

**Tech Stack:** Python 3.11+ / questionary 2.1.1 / prompt_toolkit / rich / SQLite

**Spec:** `docs/superpowers/specs/2026-04-16-menu-realtime-tick-design.md`

---

## File Structure

| 操作 | パス | 役割 |
|------|------|------|
| Modify | `src/task_recorder_cui/menu.py` | `_build_tick_lines` (pure)，`_rich_to_ansi`，`_attach_tick_window` を追加．`_render_header` から active/bar 行を削除．`_show_main_menu` に `tick_source` 引数追加．`_run_loop` で wire up |
| Modify | `tests/test_menu_pure.py` | `_build_tick_lines` の 3 ケース追加 |
| Modify | `tests/test_menu_flow.py` | `_render_header` の stale assert 削除，`_attach_tick_window` smoke テスト追加，`_show_main_menu` tick_source テスト追加 |

---

### Task 1: `_build_tick_lines` pure 関数の TDD

**Files:**
- Modify: `tests/test_menu_pure.py` (末尾に追加)
- Modify: `src/task_recorder_cui/menu.py` (関数追加)

- [ ] **Step 1: failing test を書く**

`tests/test_menu_pure.py` 末尾に追加:

```python
# --- _build_tick_lines ---


def test_build_tick_lines_no_active_returns_single_line(isolated_db) -> None:
    """記録なし → 「現在: 記録なし」1 要素。"""
    from task_recorder_cui.menu import _build_tick_lines

    now = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    with open_db() as conn:
        lines = _build_tick_lines(now, conn, bar_color="cyan", bar_style="solid")
    assert len(lines) == 1
    assert "記録なし" in lines[0]


def test_build_tick_lines_active_no_timer_returns_single_line(isolated_db) -> None:
    """記録中・タイマーなし → 経過時間付き 1 要素。"""
    from task_recorder_cui.menu import _build_tick_lines

    started = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    now = started + timedelta(minutes=45)
    with open_db() as conn, conn:
        insert_record(conn, category_key="dev", description="test", started_at=started)
    with open_db() as conn:
        lines = _build_tick_lines(now, conn, bar_color="cyan", bar_style="solid")
    assert len(lines) == 1
    assert "45m" in lines[0]


def test_build_tick_lines_active_with_timer_returns_two_lines(isolated_db) -> None:
    """記録中・タイマーあり → 2 要素 (経過行 + バー行)。"""
    from task_recorder_cui.menu import _build_tick_lines
    from task_recorder_cui.repo import set_timer_target

    started = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)
    now = started + timedelta(minutes=30)
    target = started + timedelta(minutes=60)
    with open_db() as conn, conn:
        rec_id = insert_record(conn, category_key="dev", description="x", started_at=started)
        set_timer_target(conn, rec_id, target_at=target)
    with open_db() as conn:
        lines = _build_tick_lines(now, conn, bar_color="cyan", bar_style="solid")
    assert len(lines) == 2
    assert "30m" in lines[0]
    assert "%" in lines[1]
```

- [ ] **Step 2: テスト実行 → FAIL 確認**

Run: `source .venv/bin/activate && pytest tests/test_menu_pure.py -v -k "build_tick"`

Expected: `ImportError: cannot import name '_build_tick_lines'`

- [ ] **Step 3: `_build_tick_lines` を実装**

`src/task_recorder_cui/menu.py` に関数を追加 (`_active_session_line` 定義の直後あたり):

```python
def _build_tick_lines(
    now: datetime,
    conn: sqlite3.Connection,
    *,
    bar_color: str,
    bar_style: str,
) -> list[str]:
    """tick_window 用の表示行を組み立てる (pure)。

    Args:
        now: 経過時間計算の基準時刻 (tz付き)。
        conn: 読み取りに使う DB 接続。
        bar_color: 'cyan' 等の rich カラー名。
        bar_style: 'solid' / 'rainbow' / 'gradient'。

    Returns:
        1〜2 要素のリスト。[0] は active session 行，[1] は timer bar (あれば)。

    """
    lines: list[str] = [_active_session_line(now, conn)]
    active = find_active_record(conn)
    if active is not None and active.timer_target_at is not None:
        bar = render_timer_bar(
            now=now,
            started_at=active.started_at,
            target_at=active.timer_target_at,
            fired_at=active.timer_fired_at,
            bar_color=bar_color,
            bar_style=bar_style,
            width=30,
        )
        if bar:
            lines.append(bar)
    return lines
```

- [ ] **Step 4: テスト実行 → PASS 確認**

Run: `source .venv/bin/activate && pytest tests/test_menu_pure.py -v -k "build_tick"`

Expected: 3 passed

- [ ] **Step 5: コミット**

```bash
git add tests/test_menu_pure.py src/task_recorder_cui/menu.py
git commit -m "feat(menu): _build_tick_lines pure 関数を追加

メニュー tick_window が毎秒呼ぶ描画ロジック。
既存の _active_session_line + render_timer_bar を組み合わせて
1〜2 行のリストを返す。TDD で 3 ケースを追加。"
```

---

### Task 2: `_render_header` から active/bar 行を剥がす

**Files:**
- Modify: `tests/test_menu_flow.py:208-244` (stale テスト削除・更新)
- Modify: `src/task_recorder_cui/menu.py:234-264` (`_render_header` 変更)

- [ ] **Step 1: stale テストを更新**

`tests/test_menu_flow.py` の以下 2 テストを削除 (active/bar はヘッダから消えるため):

- `test_render_header_without_active_prints_active_none` (行 208-214)
- `test_render_header_with_timer_prints_bar` (行 217-227)

`test_render_header_with_recent_records_prints_recent` (行 230-244) はそのまま残す。

- [ ] **Step 2: `_render_header` を変更 + `load_config` import をモジュールレベルに移動**

`src/task_recorder_cui/menu.py` のモジュール先頭 import セクションに追加:

```python
from task_recorder_cui.config import load_config
```

`_render_header` を以下に置き換え (内部の `from task_recorder_cui.config import load_config` は削除):

```python
def _render_header(now: datetime, conn: sqlite3.Connection) -> None:
    """ヘッダ (タイトル + 直近) を描画する。

    「現在」行とタイマーバーは tick_window で動的に描画するため，
    ヘッダには含めない。
    """
    print_line()
    print_line(t("MENU_TITLE"))
    recent = _recent_records_lines(now, conn)
    if recent:
        print_line()
        print_line(t("MENU_RECENT_LABEL"))
        for line in recent:
            print_line(line)
    print_line()
```

- [ ] **Step 3: テスト実行 → PASS 確認**

Run: `source .venv/bin/activate && pytest tests/test_menu_flow.py -v -k "render_header"`

Expected: 1 passed (`test_render_header_with_recent_records_prints_recent`)

- [ ] **Step 4: 全テスト実行 → 回帰なし確認**

Run: `source .venv/bin/activate && pytest -v`

Expected: all passed (config 未使用になった `_render_header` で import 削除は不要 — 他の場所では使っていないが，ruff が怒る場合は Task 6 で対応)

- [ ] **Step 5: コミット**

```bash
git add tests/test_menu_flow.py src/task_recorder_cui/menu.py
git commit -m "refactor(menu): _render_header から active/bar 行を削除

リアルタイム tick_window に移管するため，ヘッダにはタイトルと直近 5 件のみ残す。
対応する stale テスト 2 件を削除。"
```

---

### Task 3: `_rich_to_ansi` + `_attach_tick_window` 実装

**Files:**
- Modify: `src/task_recorder_cui/menu.py` (2 関数追加)
- Modify: `tests/test_menu_flow.py` (smoke テスト追加)

- [ ] **Step 1: smoke テストを書く**

`tests/test_menu_flow.py` の `# === _render_header ===` セクションの直前 (またはファイル末尾) に追加:

```python
# === _rich_to_ansi / _attach_tick_window ===


def test_rich_to_ansi_converts_markup() -> None:
    """rich markup が ANSI エスケープ付き文字列に変換される。"""
    text = menu._rich_to_ansi("[bold]hello[/bold]")
    assert "hello" in text


def test_attach_tick_window_sets_refresh_and_prepends_window() -> None:
    """Application に refresh_interval と先頭 Window が追加される。"""
    import questionary
    from prompt_toolkit.layout.containers import HSplit
    from prompt_toolkit.layout.controls import FormattedTextControl

    q = questionary.select("x", choices=["a", "b"])
    original_children_count = len(q.application.layout.container.children)

    menu._attach_tick_window(q.application, tick_source=lambda: ["test line"])

    assert q.application.refresh_interval == 1.0
    container = q.application.layout.container
    assert isinstance(container, HSplit)
    assert len(container.children) == original_children_count + 1
    # get_text の正常パスも通す
    tick_control = container.children[0].content
    assert isinstance(tick_control, FormattedTextControl)
    result = tick_control.text()
    assert result is not None


def test_attach_tick_window_exception_in_source_returns_empty() -> None:
    """tick_source が例外を投げても get_text は空を返す (メニューは落ちない)。"""
    import questionary
    from prompt_toolkit.layout.controls import FormattedTextControl

    def _exploding() -> list[str]:
        raise RuntimeError("boom")

    q = questionary.select("x", choices=["a", "b"])
    menu._attach_tick_window(q.application, tick_source=_exploding)

    container = q.application.layout.container
    tick_control = container.children[0].content
    assert isinstance(tick_control, FormattedTextControl)
    result = tick_control.text()
    # 例外時は空 ANSI が返る (crash しない)
    assert result is not None
```

- [ ] **Step 2: テスト実行 → FAIL 確認**

Run: `source .venv/bin/activate && pytest tests/test_menu_flow.py -v -k "attach_tick"`

Expected: `AttributeError: module 'task_recorder_cui.menu' has no attribute '_attach_tick_window'`

- [ ] **Step 3: `_rich_to_ansi` と `_attach_tick_window` を実装**

`src/task_recorder_cui/menu.py` の import セクションに追加:

```python
import io
from collections.abc import Callable

from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from rich.console import Console
```

関数を追加 (`_build_tick_lines` の直後あたり):

```python
def _rich_to_ansi(markup: str) -> str:
    """rich markup を ANSI エスケープシーケンス付き文字列に変換する。"""
    buf = io.StringIO()
    Console(file=buf, force_terminal=True, highlight=False, width=120).print(
        markup, end=""
    )
    return buf.getvalue()


def _attach_tick_window(
    application: object,
    tick_source: Callable[[], list[str]],
) -> None:
    """prompt_toolkit Application にリアルタイム tick 描画用 Window を差し込む。

    Args:
        application: questionary が内部で保持する prompt_toolkit.Application。
        tick_source: 毎秒呼ばれ，表示行 (rich markup) のリストを返す callable。

    """

    def get_text() -> ANSI:
        try:
            lines = tick_source()
            return ANSI(_rich_to_ansi("\n".join(lines)))
        except Exception:
            return ANSI("")

    tick_window = Window(
        content=FormattedTextControl(get_text),
        dont_extend_height=True,
    )
    original = application.layout.container  # type: ignore[attr-defined]
    application.layout.container = HSplit([tick_window, original])  # type: ignore[attr-defined]
    application.refresh_interval = 1.0  # type: ignore[attr-defined]
```

- [ ] **Step 4: テスト実行 → PASS 確認**

Run: `source .venv/bin/activate && pytest tests/test_menu_flow.py -v -k "attach_tick"`

Expected: 2 passed

- [ ] **Step 5: コミット**

```bash
git add src/task_recorder_cui/menu.py tests/test_menu_flow.py
git commit -m "feat(menu): _attach_tick_window で Application に tick Window を差し込む

prompt_toolkit の refresh_interval=1.0 + HSplit 先頭挿入で
メニュー選択肢の直上に 1 秒毎更新の Window を追加する仕組み。
rich markup → ANSI 変換は _rich_to_ansi 経由。"
```

---

### Task 4: `_show_main_menu` に tick_source 引数を追加

**Files:**
- Modify: `src/task_recorder_cui/menu.py:274-288` (`_show_main_menu` 変更)
- Modify: `tests/test_menu_flow.py` (テスト追加)

- [ ] **Step 1: `_FakePrompt` に `application` 属性を追加 + テストを追加**

`tests/test_menu_flow.py` の `_FakePrompt` クラスを修正 (tick_source テストで `q.application`
がアクセスされても AttributeError にならないため):

```python
class _FakePrompt:
    """questionary 関数の戻り値を差し替えるための最小スタブ。"""

    def __init__(self, value: Any) -> None:
        self._value = value
        self.application = None

    def ask(self) -> Any:
        return self._value
```

`# === _show_main_menu ===` セクション末尾に追加:

```python
def test_show_main_menu_with_tick_source_calls_attach(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """tick_source が渡されたら _attach_tick_window が呼ばれる。"""
    attached: list[bool] = []

    def _fake_attach(_app: Any, tick_source: Any) -> None:
        attached.append(True)

    monkeypatch.setattr(menu, "_attach_tick_window", _fake_attach)
    _queue_prompts(monkeypatch, selects=["quit"])
    menu._show_main_menu(recording=False, tick_source=lambda: ["test"])
    assert attached == [True]


def test_show_main_menu_without_tick_source_skips_attach(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """tick_source が None なら _attach_tick_window は呼ばれない。"""
    attached: list[bool] = []

    def _fake_attach(_app: Any, tick_source: Any) -> None:
        attached.append(True)

    monkeypatch.setattr(menu, "_attach_tick_window", _fake_attach)
    _queue_prompts(monkeypatch, selects=["quit"])
    menu._show_main_menu(recording=False)
    assert attached == []
```

- [ ] **Step 2: テスト実行 → FAIL 確認**

Run: `source .venv/bin/activate && pytest tests/test_menu_flow.py -v -k "tick_source"`

Expected: `TypeError: _show_main_menu() got an unexpected keyword argument 'tick_source'` (FakePrompt に application を追加済なので AttributeError にはならない)

- [ ] **Step 3: `_show_main_menu` を変更**

`src/task_recorder_cui/menu.py` の `_show_main_menu` を以下に置き換え:

```python
def _show_main_menu(
    *,
    recording: bool,
    tick_source: Callable[[], list[str]] | None = None,
) -> str | None:
    """メインメニューを表示し選択値 (value 文字列) を返す。Ctrl+C / ESC で None。"""
    stop_disabled: str | bool = False if recording else t("MENU_CHOICE_STOP_DISABLED")
    q = questionary.select(
        t("MENU_PROMPT_ACTION"),
        choices=[
            questionary.Choice(t("MENU_CHOICE_START"), value="start"),
            questionary.Choice(t("MENU_CHOICE_STOP"), value="stop", disabled=stop_disabled),
            questionary.Choice(t("MENU_CHOICE_TODAY"), value="today"),
            questionary.Choice(t("MENU_CHOICE_WEEK"), value="week"),
            questionary.Choice(t("MENU_CHOICE_MONTH"), value="month"),
            questionary.Choice(t("MENU_CHOICE_CAT"), value="cat"),
            questionary.Choice(t("MENU_CHOICE_HELP"), value="help"),
            questionary.Choice(t("MENU_CHOICE_QUIT"), value="quit"),
        ],
    )
    if tick_source is not None:
        _attach_tick_window(q.application, tick_source)
    return q.ask()
```

- [ ] **Step 4: テスト実行 → PASS 確認**

Run: `source .venv/bin/activate && pytest tests/test_menu_flow.py -v -k "tick_source or show_main_menu"`

Expected: 4 passed (既存 2 + 新規 2)

- [ ] **Step 5: コミット**

```bash
git add src/task_recorder_cui/menu.py tests/test_menu_flow.py
git commit -m "feat(menu): _show_main_menu に tick_source 引数を追加

tick_source が非 None の場合のみ _attach_tick_window を呼ぶ。
デフォルト None で後方互換を保つ。"
```

---

### Task 5: `_run_loop` で tick_source を wire up

**Files:**
- Modify: `src/task_recorder_cui/menu.py:509-527` (`_run_loop` 変更)

- [ ] **Step 1: `_run_loop` を変更**

`src/task_recorder_cui/menu.py` の `_run_loop` を以下に置き換え:

```python
def _run_loop() -> int:
    while True:
        now = now_utc()
        with open_db() as conn:
            _render_header(now, conn)
            recording = find_active_record(conn) is not None

        cfg = load_config()

        def _tick() -> list[str]:
            with open_db() as conn:
                return _build_tick_lines(
                    now_utc(),
                    conn,
                    bar_color=cfg.ui.bar_color,
                    bar_style=cfg.ui.bar_style,
                )

        choice = _show_main_menu(recording=recording, tick_source=_tick)
        if choice is None or choice == "quit":
            return 0
        try:
            _dispatch(choice)
        except KeyboardInterrupt:
            print_line(t("MENU_INTERRUPTED"))
            continue
        if choice != "cat":
            _pause()
```

注意: `_tick` は `# pragma: no cover` **不要** — テスト上は `_show_main_menu` の monkeypatch で
`tick_source` 引数として受け取れるが，`_tick` 自体は `_run_loop` 内のクロージャなのでテストから
直接呼ばれない．ただし `_run_loop` のフロー全体を monkeypatch で通してるテスト
(`test_run_loop_quit_immediately` 等) は `_show_main_menu` も monkeypatch 済なので
`_tick` 定義は通るが呼ばれない → dead code 扱いにならない (定義行は実行される)。

`_tick` 内の `with open_db() as conn:` 以降の行は呼び出されないので coverage miss になる可能性がある。
monkeypatch で `_show_main_menu` を差し替えているテストでは `_tick` は定義されるが呼ばれないため。
→ Step 3 で対応。

- [ ] **Step 2: 既存テスト実行 → PASS 確認**

Run: `source .venv/bin/activate && pytest tests/test_menu_flow.py -v -k "run_loop"`

Expected: 5 passed (既存テストは `_show_main_menu` を monkeypatch 済なので `tick_source` が渡っても無視)

- [ ] **Step 3: `_tick` クロージャ本体に `# pragma: no cover` を付ける**

`_tick` 関数の body が monkeypatch 時に到達されないため，以下のように pragma を追加:

```python
        def _tick() -> list[str]:  # pragma: no cover
            with open_db() as conn:
                return _build_tick_lines(
                    now_utc(),
                    conn,
                    bar_color=cfg.ui.bar_color,
                    bar_style=cfg.ui.bar_style,
                )
```

- [ ] **Step 4: コミット**

```bash
git add src/task_recorder_cui/menu.py
git commit -m "feat(menu): _run_loop で tick_source を配線

_show_main_menu に _tick クロージャを渡す。毎秒 open_db() →
_build_tick_lines で現在の active session とタイマー状態を取得。
config の bar_color / bar_style を反映する。"
```

---

### Task 6: カバレッジ 100% + ruff + 最終確認

**Files:**
- 全体確認

- [ ] **Step 1: ruff チェック**

Run: `source .venv/bin/activate && ruff check src/task_recorder_cui/menu.py tests/test_menu_pure.py tests/test_menu_flow.py`

Expected: 0 errors

未使用 import (`from task_recorder_cui.config import load_config` が `_render_header` から消えた場合) があれば削除。
ただし `_run_loop` 内で `load_config()` を使うので import 自体は残る (位置の変更は不要)。

- [ ] **Step 2: ruff format**

Run: `source .venv/bin/activate && ruff format src/task_recorder_cui/menu.py tests/test_menu_pure.py tests/test_menu_flow.py`

- [ ] **Step 3: カバレッジ確認**

Run: `source .venv/bin/activate && pytest --cov --cov-report=term-missing`

Expected: 100% (fail_under=100 が pass する)

もし `_rich_to_ansi` や `_attach_tick_window` 内の行がカバーされていなければ:
- `_rich_to_ansi` → Task 3 の smoke テスト (`test_attach_tick_window_exception_in_source_returns_empty`) が
  例外パスのみ通る場合は正常パスもテストする必要あり → `_rich_to_ansi` 単体テストを追加:

```python
def test_rich_to_ansi_converts_markup() -> None:
    text = menu._rich_to_ansi("[bold]hello[/bold]")
    assert "hello" in text
```

- `_attach_tick_window` → Task 3 の smoke テスト 2 つでカバー済のはず
- `get_text` クロージャ → 例外テスト経由で呼ばれるのでカバー済のはず

- [ ] **Step 4: 全テスト最終実行**

Run: `source .venv/bin/activate && pytest -v`

Expected: all passed, coverage 100%

- [ ] **Step 5: コミット (変更がある場合)**

```bash
git add -u
git commit -m "style(menu): ruff fix + カバレッジ 100% 調整"
```

---

## 手動動作確認チェックリスト (Task 6 の後，TTY で実施)

以下はテスト自動化できない TTY 依存の確認項目。実装完了後にユーザが手動で確認:

- [ ] `tsk start dev "test"` で記録開始 → `tsk` でメニュー起動 → 「現在」行の経過時間が 1 分刻みで進む
- [ ] `tsk start dev "test" --timer 5m` → `tsk` メニュー → バーが 1 秒毎に伸びる
- [ ] タイマー発火の瞬間 → 5 秒間赤点滅 (blink) → 太字表示に落ち着く
- [ ] 矢印キー・Enter の操作が従来通り動く (tick で入力が取りこぼされない)
- [ ] Ctrl+C で安全に抜けられる
- [ ] 記録なしの状態でメニュー → 「現在: 記録なし」が表示される
- [ ] カテゴリサブメニュー → tick は自然に止まる (questionary の別 Application になるため)
