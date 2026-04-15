"""タイマー daemon のエントリポイント (外部非公開)。

`tsk _timer-daemon <record_id>` で呼ばれ、services.timer.run_daemon_loop を
実行する。ユーザが直接呼ぶことは想定しない。
"""

import sys

from task_recorder_cui.services.timer import run_daemon_loop


def main(argv: list[str] | None = None) -> int:
    """daemon を起動する。

    Args:
        argv: コマンドライン引数 (先頭に record_id を期待)。

    Returns:
        終了コード (常に 0 または 2)。

    """
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: tsk _timer-daemon <record_id>", file=sys.stderr)
        return 2
    try:
        record_id = int(args[0])
    except ValueError:
        print(f"record_id は整数: {args[0]!r}", file=sys.stderr)
        return 2
    return run_daemon_loop(record_id)


if __name__ == "__main__":
    sys.exit(main())
