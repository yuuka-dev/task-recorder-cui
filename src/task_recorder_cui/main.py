"""`python -m task_recorder_cui.main` および `python -m task_recorder_cui` 用のエントリ。

実体の CLI ロジックは `cli.main` にある。本モジュールは薄いラッパ。
"""

from task_recorder_cui.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
