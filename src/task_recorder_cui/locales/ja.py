"""日本語メッセージカタログ。

キーは UPPER_SNAKE_CASE で統一。値は str.format() 互換のプレースホルダ
({name}) を含んでよい。UI からは `i18n.t(key, **fmt)` 経由で参照する。
"""

# === Session ===
SESSION_NONE = "現在: 記録なし"

# === Errors ===
ERROR_INVALID_KEY = "カテゴリ key が不正です: {key}"
