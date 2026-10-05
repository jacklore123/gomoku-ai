"""Gomoku AI engine package.

This package contains the board model, the alpha-beta search AI, the
terminal interface and the Tkinter GUI.
"""

from .board import (
    BLACK,
    DEFAULT_BOARD_SIZE,
    EMPTY,
    WHITE,
    check_win,
    index_to_move,
    move_to_index,
    new_board,
    other,
    print_board,
    star_points,
)
from .ai import AIPlayer, State, candidate_moves, point_score

__all__ = [
    "AIPlayer",
    "BLACK",
    "DEFAULT_BOARD_SIZE",
    "EMPTY",
    "State",
    "WHITE",
    "candidate_moves",
    "check_win",
    "index_to_move",
    "move_to_index",
    "new_board",
    "other",
    "point_score",
    "print_board",
    "star_points",
]

__version__ = "2.0.0"
