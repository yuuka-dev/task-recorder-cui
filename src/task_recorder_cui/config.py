"""設定ファイル (TOML) の読み書き。

ファイル配置は `~/.config/tsk/config.toml` (XDG 準拠)。環境変数
`TSK_CONFIG_PATH` で上書き可能 (主にテスト用)。外部依存を増やさないため
読み込みは標準ライブラリ `tomllib`、書き込みは簡易シリアライザで行う。
"""

import os
import tomllib
from dataclasses import asdict, dataclass, field, replace
from dataclasses import fields as dc_fields
from pathlib import Path


@dataclass(frozen=True)
class TimerConfig:
    """タイマー機能の設定。

    Attributes:
        enabled: False ならタイマー機能全体を無効化する。
        sound_path: 発火時に鳴らす WAV ファイルのパス (POSIX または Windows 形式)。
        notify_when_closed: tsk メニュー閉時に Windows デスクトップ通知を出すか。

    """

    enabled: bool = True
    sound_path: str = "/mnt/c/Windows/Media/Alarm01.wav"
    notify_when_closed: bool = True


@dataclass(frozen=True)
class UIConfig:
    """UI 見た目の設定。

    Attributes:
        lang: 'ja' / 'en' / '' のいずれか。空文字列は「未設定」を意味し、
            i18n 側で OS の LC_ALL / LANG にフォールバックする。
        bar_color: rich のカラー名 (red/green/cyan 等)。
        bar_style: 'solid' / 'rainbow' / 'gradient'。

    """

    lang: str = ""
    bar_color: str = "cyan"
    bar_style: str = "solid"


@dataclass(frozen=True)
class Config:
    """tsk 全体の設定。

    Attributes:
        timer: タイマー関連。
        ui: UI 関連。

    """

    timer: TimerConfig = field(default_factory=TimerConfig)
    ui: UIConfig = field(default_factory=UIConfig)


def default_config() -> Config:
    """組み込みデフォルト値で Config を生成する。"""
    return Config()


def get_config_path() -> Path:
    """設定ファイルのパスを返す。

    環境変数 `TSK_CONFIG_PATH` が設定されていればそれを優先する。

    Returns:
        config.toml のパス (実在しなくてもよい)。

    """
    env = os.environ.get("TSK_CONFIG_PATH")
    if env:
        return Path(env)
    return Path.home() / ".config" / "tsk" / "config.toml"


def load_config() -> Config:
    """設定ファイルを読み込む。存在しなければデフォルトを返す。

    部分的にしかキーが書かれていない場合はデフォルト値で埋める。

    Returns:
        読み込み済み Config。

    """
    path = get_config_path()
    if not path.exists():
        return default_config()
    with path.open("rb") as fp:
        raw = tomllib.load(fp)
    return _from_raw(raw)


def save_config(cfg: Config) -> None:
    """設定ファイルを書き出す。親ディレクトリは自動作成。

    Args:
        cfg: 保存する Config。

    """
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    text = dump_toml(cfg)
    path.write_text(text, encoding="utf-8")


def dump_toml(cfg: Config) -> str:
    """Config を TOML 文字列にシリアライズする (簡易実装)。

    値の型は bool / str のみを想定。外部依存を避けるため手書き。

    Args:
        cfg: 対象 Config。

    Returns:
        TOML 形式の文字列。

    """
    lines: list[str] = []
    for section_name, section_obj in (("timer", cfg.timer), ("ui", cfg.ui)):
        lines.append(f"[{section_name}]")
        for key, value in asdict(section_obj).items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _toml_value(value: object) -> str:
    """TOML のスカラー値を文字列化する。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise TypeError(f"未対応の型: {type(value).__name__}")


def _from_raw(raw: dict[str, object]) -> Config:
    """tomllib が返す dict から Config を構築する (欠けたキーはデフォルト)。"""
    timer_raw_obj = raw.get("timer")
    ui_raw_obj = raw.get("ui")
    timer_raw = timer_raw_obj if isinstance(timer_raw_obj, dict) else {}
    ui_raw = ui_raw_obj if isinstance(ui_raw_obj, dict) else {}
    timer = TimerConfig(
        enabled=bool(timer_raw.get("enabled", True)),
        sound_path=str(timer_raw.get("sound_path", TimerConfig.sound_path)),
        notify_when_closed=bool(timer_raw.get("notify_when_closed", True)),
    )
    ui = UIConfig(
        lang=str(ui_raw.get("lang", "")),
        bar_color=str(ui_raw.get("bar_color", "cyan")),
        bar_style=str(ui_raw.get("bar_style", "solid")),
    )
    return Config(timer=timer, ui=ui)


_SECTIONS: dict[str, type] = {"timer": TimerConfig, "ui": UIConfig}


def all_keys() -> list[str]:
    """サポートするすべての設定キー ('section.name' 形式) を返す。"""
    result: list[str] = []
    for section_name, section_cls in _SECTIONS.items():
        for f in dc_fields(section_cls):
            result.append(f"{section_name}.{f.name}")
    return result


def _split_key(key: str) -> tuple[str, str]:
    """'timer.sound_path' を ('timer', 'sound_path') に分解する。"""
    if "." not in key:
        raise KeyError(f"設定キーは 'section.name' 形式で指定してください: {key}")
    section, name = key.split(".", 1)
    if section not in _SECTIONS:
        raise KeyError(f"未知のセクション: {section}")
    valid_names = {f.name for f in dc_fields(_SECTIONS[section])}
    if name not in valid_names:
        raise KeyError(f"{key}: 未知のキー")
    return section, name


def get_value(cfg: Config, key: str) -> object:
    """'timer.sound_path' 形式のキーで値を取得する。

    Args:
        cfg: 対象 Config。
        key: 'section.name' 形式。

    Returns:
        該当フィールドの値。

    Raises:
        KeyError: 未知のキー。

    """
    section, name = _split_key(key)
    section_obj = getattr(cfg, section)
    return getattr(section_obj, name)


def set_value(cfg: Config, key: str, value: str) -> Config:
    """Config の指定キーを更新した新しい Config を返す (frozen なので copy)。

    str 入力を dataclass の型に合わせてコアースする。bool は 'true'/'false'、
    int は素直に int()。それ以外は str のまま。

    Args:
        cfg: 元 Config。
        key: 'section.name' 形式。
        value: 文字列で渡される新しい値。

    Returns:
        更新後の新しい Config。

    Raises:
        KeyError: 未知のキー。
        ValueError: bool を要求する場合に 'true'/'false' 以外が渡された。

    """
    section, name = _split_key(key)
    section_cls = _SECTIONS[section]
    field_type = {f.name: f.type for f in dc_fields(section_cls)}[name]

    coerced: object
    if field_type is bool or field_type == "bool":
        lower = value.strip().lower()
        if lower not in {"true", "false"}:
            raise ValueError(f"bool には true/false を指定してください: {value!r}")
        coerced = lower == "true"
    elif field_type is int or field_type == "int":
        coerced = int(value)
    else:
        coerced = value

    section_obj = getattr(cfg, section)
    new_section = replace(section_obj, **{name: coerced})
    return replace(cfg, **{section: new_section})


def reset_value(cfg: Config, key: str) -> Config:
    """指定キーをデフォルト値に戻した Config を返す。"""
    section, name = _split_key(key)
    section_cls = _SECTIONS[section]
    default_section = section_cls()
    default_val = getattr(default_section, name)
    section_obj = getattr(cfg, section)
    new_section = replace(section_obj, **{name: default_val})
    return replace(cfg, **{section: new_section})
