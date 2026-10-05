"""Command line interface for the Gomoku engine.

Run ``python gomoku_cli.py --help`` for all options.  The CLI is the main
way to watch the AI print its search process; it also supports AI-vs-AI
games and small benchmark runs.
"""

from __future__ import annotations

import argparse
import random
import sys
from typing import Optional

from .ai import AIPlayer, LEVEL_PRESETS, SearchStats, State
from .board import (
    BLACK,
    DEFAULT_BOARD_SIZE,
    EMPTY,
    MAX_BOARD_SIZE,
    MIN_BOARD_SIZE,
    PIECE_NAMES,
    WHITE,
    check_win_flat,
    index_to_move,
    print_board,
)


def _reconfigure_stdio() -> None:
    """Make Windows consoles resilient to non-ASCII output."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _piece_label(piece: int) -> str:
    symbol = "X" if piece == BLACK else "O"
    return f"{PIECE_NAMES[piece]} ({symbol})"


def _move_text(index: int, size: int) -> str:
    row, col = divmod(index, size)
    return f"{row + 1},{col + 1}"


def _verbose_callback(piece: int, size: int):
    label = _piece_label(piece)

    def callback(depth: int, score: int, elapsed: float, nodes: int, move: int) -> None:
        print(
            f"    [{label}] 迭代深度 {depth:>2} | "
            f"节点 {nodes:>8} | 用时 {elapsed:.3f}s | "
            f"评分 {score:+d} | 首选 {_move_text(move, size)}"
        )

    return callback


def _print_stats(label: str, stats: SearchStats) -> None:
    print(
        f"[{label} AI] 落子 {stats.move_text} | "
        f"深度 {stats.depth} | 节点 {stats.nodes} | "
        f"用时 {stats.elapsed:.3f}s | 评分 {stats.score:+d} | "
        f"PV {stats.pv_text}"
    )


def _get_human_move(state: State) -> Optional[int]:
    """Read one one-based ``row,col`` coordinate, or ``None`` to quit."""

    while True:
        try:
            raw = input("你的落子（行,列，例如 7,7；q 退出）：").strip()
        except (EOFError, KeyboardInterrupt):
            return None

        if raw.lower() in {"q", "quit", "exit"}:
            return None

        parts = raw.replace("，", ",").replace(" ", ",").split(",")
        if len(parts) != 2:
            print("格式不对，请用逗号隔开行和列，例如 7,7。")
            continue
        try:
            row = int(parts[0])
            col = int(parts[1])
        except ValueError:
            print("请输入两个整数，例如 7,7。")
            continue

        if not (1 <= row <= state.size and 1 <= col <= state.size):
            print(f"坐标超出范围，行和列都应在 1 到 {state.size} 之间。")
            continue

        index = (row - 1) * state.size + (col - 1)
        if state.board[index] != EMPTY:
            print("这个位置已经有棋子了，请换一个位置。")
            continue
        return index


def _print_board_2d(state: State) -> None:
    """Convert the flat AI state to a two dimensional board for printing."""

    size = state.size
    board = [
        state.board[row * size : (row + 1) * size]
        for row in range(size)
    ]
    print_board(board)


def _run_game(
    *,
    mode: str,
    size: int,
    ai_black: AIPlayer,
    ai_white: AIPlayer,
    quiet: bool,
    show_board: bool,
    verbose: bool,
) -> Optional[int]:
    """Run one game and return BLACK, WHITE, 0 (draw), or None (quit)."""

    state = State(size)
    move_number = 0

    if not quiet:
        print()
        print("===== 五子棋 AI =====")
        print(f"棋盘大小：{size} x {size}")
        if mode == "pvp":
            print("模式：双人对战（黑棋先手）")
        elif mode == "human-ai":
            print("模式：人机对战（你执黑先手，电脑执白后手）")
        elif mode == "ai-human":
            print("模式：人机对战（电脑执黑先手，你执白后手）")
        else:
            print("模式：AI 对战 AI")
        print("输入 q 可随时退出。")
        if show_board:
            _print_board_2d(state)

    while True:
        piece = state.turn
        is_ai = (
            (mode == "ai-ai")
            or (mode == "human-ai" and piece == WHITE)
            or (mode == "ai-human" and piece == BLACK)
        )

        if is_ai:
            ai = ai_black if piece == BLACK else ai_white
            if not quiet:
                print(f"{_piece_label(piece)} AI 思考中……")
            stats = ai.choose_move(state)
            index = stats.move
            if index < 0:
                return None
            if not quiet:
                _print_stats(_piece_label(piece), stats)
        else:
            index = _get_human_move(state)
            if index is None:
                return None

        player = state.make_move(index)
        move_number += 1
        if show_board and not quiet:
            _print_board_2d(state)

        if check_win_flat(state.board, index, player, size):
            return player
        if state.is_full:
            return 0


def _benchmark(
    *,
    games: int,
    size: int,
    depth: int,
    time_limit: float,
    branch: int,
    seed: int,
) -> None:
    """Run deterministic AI-vs-AI games and print a compact summary."""

    results = {BLACK: 0, WHITE: 0, 0: 0}
    for game in range(1, games + 1):
        game_seed = seed + game
        black = AIPlayer(
            size=size,
            max_depth=depth,
            time_limit=time_limit,
            max_branch=branch,
            seed=game_seed,
        )
        white = AIPlayer(
            size=size,
            max_depth=depth,
            time_limit=time_limit,
            max_branch=branch,
            seed=game_seed + 1_000_000,
        )
        result = _run_game(
            mode="ai-ai",
            size=size,
            ai_black=black,
            ai_white=white,
            quiet=True,
            show_board=False,
            verbose=False,
        )
        key = result if result in (BLACK, WHITE) else 0
        results[key] += 1
        winner = "黑棋" if key == BLACK else "白棋" if key == WHITE else "平局"
        print(f"第 {game:>2} 局：{winner}")

    print()
    print(
        "汇总："
        f"黑棋 {results[BLACK]} 胜，"
        f"白棋 {results[WHITE]} 胜，"
        f"平局 {results[0]}。"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gomoku_cli",
        description="19x19（可配置）五子棋 AI，支持打印运算过程和 AI 自对弈。",
    )
    parser.add_argument(
        "--mode",
        choices=("human-ai", "ai-human", "pvp", "ai-ai"),
        default="human-ai",
        help="对局模式，默认 human-ai（人执黑先手）。",
    )
    parser.add_argument(
        "--level",
        choices=("low", "medium", "high"),
        default="medium",
        help="AI 棋力档位：low=低，medium=中，high=高。",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=DEFAULT_BOARD_SIZE,
        help=f"棋盘大小（奇数，{MIN_BOARD_SIZE}-{MAX_BOARD_SIZE}），默认 {DEFAULT_BOARD_SIZE}。",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=None,
        help="最大搜索深度（默认按 --level 预设）。",
    )
    parser.add_argument(
        "--time",
        type=float,
        default=None,
        help="每步思考时间上限（秒），默认按 --level 预设。",
    )
    parser.add_argument(
        "--branch",
        type=int,
        default=None,
        help="每层候选分支上限，默认按 --level 预设。",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="AI 随机种子（同种子可复现）。",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=1,
        help="AI 对 AI 或基准测试局数。",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="静默运行多局 AI 对 AI，仅输出每局胜负与汇总。",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="关闭思考过程输出，只显示必要结果。",
    )
    parser.add_argument(
        "--no-board",
        action="store_true",
        help="不打印棋盘。",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="打印每次迭代深度的详细运算过程。",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="gomoku-ai 2.0.0",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    _reconfigure_stdio()
    args = build_parser().parse_args(argv)

    if args.size < MIN_BOARD_SIZE or args.size > MAX_BOARD_SIZE or args.size % 2 == 0:
        print(
            f"棋盘大小必须是 {MIN_BOARD_SIZE}-{MAX_BOARD_SIZE} 之间的奇数。",
            file=sys.stderr,
        )
        return 2

    preset = LEVEL_PRESETS[args.level]
    depth = args.depth if args.depth is not None else preset["max_depth"]
    time_limit = args.time if args.time is not None else preset["time_limit"]
    branch = args.branch if args.branch is not None else preset["max_branch"]

    if depth < 1:
        print("--depth 至少为 1。", file=sys.stderr)
        return 2
    if time_limit <= 0:
        print("--time 必须大于 0。", file=sys.stderr)
        return 2
    if branch < 1:
        print("--branch 至少为 1。", file=sys.stderr)
        return 2

    if args.benchmark:
        _benchmark(
            games=max(1, args.games),
            size=args.size,
            depth=depth,
            time_limit=time_limit,
            branch=branch,
            seed=args.seed if args.seed is not None else random.randrange(1 << 30),
        )
        return 0

    if args.mode == "ai-ai" and args.games > 1:
        _benchmark(
            games=args.games,
            size=args.size,
            depth=depth,
            time_limit=time_limit,
            branch=branch,
            seed=args.seed if args.seed is not None else random.randrange(1 << 30),
        )
        return 0

    callback_black = _verbose_callback(BLACK, args.size) if args.verbose else None
    callback_white = _verbose_callback(WHITE, args.size) if args.verbose else None
    ai_black = AIPlayer(
        size=args.size,
        max_depth=depth,
        time_limit=time_limit,
        max_branch=branch,
        seed=args.seed,
        on_iteration=callback_black,
    )
    ai_white = AIPlayer(
        size=args.size,
        max_depth=depth,
        time_limit=time_limit,
        max_branch=branch,
        seed=None if args.seed is None else args.seed + 1_000_000,
        on_iteration=callback_white,
    )

    result = _run_game(
        mode=args.mode,
        size=args.size,
        ai_black=ai_black,
        ai_white=ai_white,
        quiet=args.quiet,
        show_board=not args.no_board,
        verbose=args.verbose,
    )

    if result is None:
        print("\n游戏结束，下次再战！")
        return 0

    if not args.quiet:
        if result == 0:
            print("\n棋盘已满，双方平局！")
        else:
            print(f"\n恭喜 {_piece_label(result)} 获胜！五子连珠达成！")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
