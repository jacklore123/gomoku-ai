"""Core board rules and small helpers.

The engine uses integer pieces internally for speed:

* ``EMPTY`` = 0
* ``BLACK`` = 1
* ``WHITE`` = 2

Coordinates are zero based in all engine APIs.  The CLI and GUI translate
one based coordinates to and from these values when talking to a human.
"""

from __future__ import annotations

from typing import Iterable

EMPTY = 0
BLACK = 1
WHITE = 2

DEFAULT_BOARD_SIZE = 19
MIN_BOARD_SIZE = 9
MAX_BOARD_SIZE = 25

PIECE_NAMES = {
    BLACK: "黑棋",
    WHITE: "白棋",
}

PIECE_CHARS = {
    EMPTY: ".",
    BLACK: "X",
    WHITE: "O",
}

DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


def other(piece: int) -> int:
    """Return the opponent of *piece*."""

    return 3 - piece


def move_to_index(row: int, col: int, size: int = DEFAULT_BOARD_SIZE) -> int:
    """Convert a zero based ``(row, col)`` coordinate to a flat index."""

    return row * size + col


def index_to_move(index: int, size: int = DEFAULT_BOARD_SIZE) -> tuple[int, int]:
    """Convert a flat index to a zero based ``(row, col)`` coordinate."""

    return divmod(index, size)


def new_board(size: int = DEFAULT_BOARD_SIZE) -> list[list[int]]:
    """Create an empty two dimensional board."""

    return [[EMPTY] * size for _ in range(size)]


def star_points(size: int = DEFAULT_BOARD_SIZE) -> list[tuple[int, int]]:
    """Return conventional star point coordinates for a square board."""

    if size < 13:
        return []

    points = {3, size // 2, size - 4}
    return [(row, col) for row in sorted(points) for col in sorted(points)]


def check_win(board: list[list[int]], row: int, col: int, piece: int) -> bool:
    """Return ``True`` if *piece* forms five or more in a row at ``(row, col)``."""

    size = len(board)
    for dr, dc in DIRECTIONS:
        count = 1
        for sign in (1, -1):
            r = row + dr * sign
            c = col + dc * sign
            while (
                0 <= r < size
                and 0 <= c < size
                and board[r][c] == piece
            ):
                count += 1
                r += dr * sign
                c += dc * sign
        if count >= 5:
            return True
    return False


def check_win_flat(
    board: list[int], index: int, piece: int, size: int = DEFAULT_BOARD_SIZE
) -> bool:
    """Flat-board variant of :func:`check_win` used by the AI search."""

    row, col = divmod(index, size)
    for dr, dc in DIRECTIONS:
        count = 1
        for sign in (1, -1):
            r = row + dr * sign
            c = col + dc * sign
            while 0 <= r < size and 0 <= c < size:
                if board[r * size + c] != piece:
                    break
                count += 1
                r += dr * sign
                c += dc * sign
        if count >= 5:
            return True
    return False


def print_board(board: list[list[int]]) -> None:
    """Print a two dimensional board to the terminal."""

    size = len(board)
    print()
    header = "    " + " ".join(f"{c:>2}" for c in range(1, size + 1))
    print(header)
    for row in range(size):
        cells = " ".join(f"{PIECE_CHARS[board[row][col]]:>2}" for col in range(size))
        print(f"{row + 1:>3}  {cells}")
    print()


def winning_line(
    board: list[int],
    index: int,
    piece: int,
    size: int = DEFAULT_BOARD_SIZE,
) -> list[int]:
    """Return the five winning indices for a completed line, if any."""

    row, col = divmod(index, size)
    for dr, dc in DIRECTIONS:
        cells = [index]
        for sign in (1, -1):
            r = row + dr * sign
            c = col + dc * sign
            while 0 <= r < size and 0 <= c < size:
                idx = r * size + c
                if board[idx] != piece:
                    break
                cells.append(idx)
                r += dr * sign
                c += dc * sign
        if len(cells) >= 5:
            return cells
    return []


def format_indices(indices: Iterable[int], size: int = DEFAULT_BOARD_SIZE) -> str:
    """Format flat indices as a human readable move sequence."""

    parts = []
    for idx in indices:
        row, col = divmod(idx, size)
        parts.append(f"{row + 1},{col + 1}")
    return " ".join(parts)
