"""Backwards-compatible module facade.

The original project exposed most of its rules from a single ``gomoku.py``
file.  This module keeps the common names available while delegating to the
new package.  Running it directly starts the terminal game.
"""

from __future__ import annotations

from gomoku_engine.ai import AIPlayer, State, ai_move
from gomoku_engine.board import (
    BLACK,
    DEFAULT_BOARD_SIZE,
    EMPTY,
    WHITE,
    check_win,
    new_board,
    other,
    print_board,
    star_points,
)

BOARD_SIZE = DEFAULT_BOARD_SIZE
MODE_PVP = 1
MODE_PVC = 2

STONE_NAME = {
    BLACK: "黑棋 (X)",
    WHITE: "白棋 (O)",
}

__all__ = [
    "AIPlayer",
    "BLACK",
    "BOARD_SIZE",
    "DEFAULT_BOARD_SIZE",
    "EMPTY",
    "MODE_PVC",
    "MODE_PVP",
    "STONE_NAME",
    "State",
    "WHITE",
    "ai_move",
    "check_win",
    "new_board",
    "other",
    "print_board",
    "star_points",
]


if __name__ == "__main__":
    from gomoku_engine.cli import main

    raise SystemExit(main())
