"""A fast, reasonably strong Gomoku AI.

The search is a time-limited negamax alpha-beta with:

* Zobrist transposition tables
* iterative deepening
* candidate-move generation limited to the neighbourhood of existing stones
* move ordering driven by a pattern/threat evaluation
* immediate win and forced-block shortcuts
* a small opening-book centre bias

The evaluation understands five, open four, four, open three, broken three,
and double-threat combinations.  It is deliberately compact enough to remain
interactive on a 19x19 board while still punishing one-move blunders.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import random
import time
from typing import Callable, Optional

from .board import (
    BLACK,
    DEFAULT_BOARD_SIZE,
    EMPTY,
    WHITE,
    check_win_flat,
    format_indices,
    index_to_move,
    other,
)


INF = 1 << 30
WIN_SCORE = 10_000_000
MATE_SCORE = WIN_SCORE - 100

EXACT = 0
LOWER_BOUND = 1
UPPER_BOUND = 2

LEVEL_PRESETS = {
    "low": {"max_depth": 2, "time_limit": 0.25, "max_branch": 12},
    "medium": {"max_depth": 4, "time_limit": 0.8, "max_branch": 20},
    "high": {"max_depth": 6, "time_limit": 2.0, "max_branch": 28},
}


class SearchTimeout(Exception):
    """Raised internally when the allocated search time has elapsed."""


@dataclass(slots=True)
class SearchStats:
    """Result and diagnostics for one AI move."""

    move: int
    score: int
    depth: int
    nodes: int
    elapsed: float
    pv: list[int]
    cutoffs: int = 0
    size: int = DEFAULT_BOARD_SIZE

    @property
    def move_text(self) -> str:
        row, col = index_to_move(self.move, self.size)
        return f"{row + 1},{col + 1}"

    @property
    def pv_text(self) -> str:
        return format_indices(self.pv, self.size)


@dataclass(slots=True)
class _TTEntry:
    depth: int
    score: int
    flag: int
    best_move: Optional[int]


@dataclass(slots=True)
class _Tables:
    size: int
    side_key: int
    zobrist: list[list[int]]
    neighbour_masks: list[int]
    lines: list[list[tuple[int, tuple[int, ...]]]]
    windows6: list[tuple[int, int, int]]


class State:
    """Mutable board state used by the search.

    The board is stored both as a flat ``list[int]`` (for fast pattern
    evaluation) and as two bitboards (for fast candidate generation).
    """

    __slots__ = (
        "size",
        "board",
        "stones",
        "turn",
        "black_mask",
        "white_mask",
        "zobrist",
        "ply",
    )

    def __init__(self, size: int = DEFAULT_BOARD_SIZE):
        self.size = size
        self.board = [EMPTY] * (size * size)
        self.stones: list[int] = []
        self.turn = BLACK
        self.black_mask = 0
        self.white_mask = 0
        self.ply = 0
        self.zobrist = _tables(size).side_key

    @property
    def occupied(self) -> int:
        return self.black_mask | self.white_mask

    @property
    def is_full(self) -> bool:
        return len(self.stones) == self.size * self.size

    def copy(self) -> "State":
        clone = State.__new__(State)
        clone.size = self.size
        clone.board = self.board.copy()
        clone.stones = self.stones.copy()
        clone.turn = self.turn
        clone.black_mask = self.black_mask
        clone.white_mask = self.white_mask
        clone.zobrist = self.zobrist
        clone.ply = self.ply
        return clone

    @classmethod
    def from_board(cls, board: list[list[int]], turn: int = BLACK) -> "State":
        """Build a state from a two dimensional board without side effects."""

        size = len(board)
        state = cls(size)
        tables = _tables(size)
        zobrist = 0
        for row in range(size):
            for col in range(size):
                piece = board[row][col]
                if piece == EMPTY:
                    continue
                index = row * size + col
                bit = 1 << index
                state.board[index] = piece
                state.stones.append(index)
                if piece == BLACK:
                    state.black_mask |= bit
                else:
                    state.white_mask |= bit
                zobrist ^= tables.zobrist[piece][index]
        state.turn = turn
        state.ply = len(state.stones)
        state.zobrist = zobrist ^ (tables.side_key if turn == BLACK else 0)
        return state

    def make_move(self, index: int) -> int:
        """Place the current player's stone at *index* and toggle the turn."""

        player = self.turn
        self.board[index] = player
        self.stones.append(index)
        bit = 1 << index
        if player == BLACK:
            self.black_mask |= bit
        else:
            self.white_mask |= bit

        tables = _tables(self.size)
        self.zobrist ^= tables.side_key
        self.zobrist ^= tables.zobrist[player][index]
        self.turn = other(player)
        self.zobrist ^= tables.side_key
        self.ply += 1
        return player

    def unmake_move(self) -> int:
        """Undo the most recent :meth:`make_move` and return its index."""

        index = self.stones.pop()
        player = other(self.turn)
        bit = 1 << index
        if player == BLACK:
            self.black_mask &= ~bit
        else:
            self.white_mask &= ~bit

        tables = _tables(self.size)
        self.zobrist ^= tables.side_key
        self.zobrist ^= tables.zobrist[player][index]
        self.board[index] = EMPTY
        self.turn = player
        self.zobrist ^= tables.side_key
        self.ply -= 1
        return index


@lru_cache(maxsize=None)
def _tables(size: int) -> _Tables:
    """Precompute zobrist keys, neighbour masks, and evaluation lines."""

    n = size * size
    rng = random.Random(0x5EED_60A0 ^ size)

    zobrist = [[0] * n for _ in range(3)]
    for player in (BLACK, WHITE):
        for index in range(n):
            zobrist[player][index] = rng.getrandbits(64) or 1
    side_key = rng.getrandbits(64) or 1

    neighbour_masks: list[int] = []
    for index in range(n):
        row, col = divmod(index, size)
        mask = 0
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                if dr == 0 and dc == 0:
                    continue
                r = row + dr
                c = col + dc
                if 0 <= r < size and 0 <= c < size:
                    mask |= 1 << (r * size + c)
        neighbour_masks.append(mask)

    lines: list[list[tuple[int, tuple[int, ...]]]] = []
    for index in range(n):
        row, col = divmod(index, size)
        cell_lines: list[tuple[int, tuple[int, ...]]] = []
        for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
            points: list[int] = []
            for step in range(-4, 5):
                r = row + dr * step
                c = col + dc * step
                if 0 <= r < size and 0 <= c < size:
                    points.append(r * size + c)
            if points:
                cell_lines.append((points.index(index), tuple(points)))
        lines.append(cell_lines)

    windows6: list[tuple[int, int, int]] = []
    for row in range(size):
        for col in range(size):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                end_row = row + 5 * dr
                end_col = col + 5 * dc
                if not (0 <= end_row < size and 0 <= end_col < size):
                    continue

                mask = 0
                for step in range(6):
                    r = row + dr * step
                    c = col + dc * step
                    mask |= 1 << (r * size + c)

                before_row = row - dr
                before_col = col - dc
                after_row = end_row + dr
                after_col = end_col + dc
                before = (
                    1 << (before_row * size + before_col)
                    if 0 <= before_row < size and 0 <= before_col < size
                    else 0
                )
                after = (
                    1 << (after_row * size + after_col)
                    if 0 <= after_row < size and 0 <= after_col < size
                    else 0
                )
                windows6.append((mask, before, after))

    return _Tables(
        size=size,
        side_key=side_key,
        zobrist=zobrist,
        neighbour_masks=neighbour_masks,
        lines=lines,
        windows6=windows6,
    )


def candidate_moves(state: State) -> list[int]:
    """Generate legal candidate moves near existing stones."""

    if not state.stones:
        return [state.size * state.size // 2]

    tables = _tables(state.size)
    mask = 0
    for index in state.stones:
        mask |= tables.neighbour_masks[index]
    mask &= ~state.occupied

    moves: list[int] = []
    while mask:
        low_bit = mask & -mask
        moves.append(low_bit.bit_length() - 1)
        mask ^= low_bit
    return moves


def _pattern_level(window: str, length: int) -> int:
    """Classify one 5/6 cell window.

    Levels:
    6 = five, 5 = open/broken four, 4 = four, 3 = open/broken three,
    2 = closed three, 1 = weak two, 0 = nothing.
    """

    if "PPPPP" in window:
        return 6

    p = window.count("P")
    e = window.count(".")
    b = length - p - e

    if b == 0:
        if p == 4:
            return 5 if length >= 6 else 4
        if p == 3 and e >= 2:
            return 3
        if p == 2 and e >= 3:
            return 1
        return 0

    if p == 4 and e == 1 and b == 1:
        return 4
    if p == 3 and e == 2 and b == 1:
        return 2
    if p == 2 and e >= 2:
        return 1
    return 0


def _line_level(
    state: State,
    index: int,
    player: int,
    center: int,
    line: tuple[int, ...],
) -> int:
    """Return the strongest threat level on one board line for *player*."""

    chars: list[str] = []
    for offset, cell in enumerate(line):
        if offset == center:
            chars.append("P")
            continue
        value = state.board[cell]
        if value == player:
            chars.append("P")
        elif value == EMPTY:
            chars.append(".")
        else:
            chars.append("B")
    text = "".join(chars)

    best = 0
    n = len(text)
    for length in (6, 5):
        if n < length:
            continue
        start_min = max(0, center - length + 1)
        start_max = min(center, n - length)
        for start in range(start_min, start_max + 1):
            level = _pattern_level(text[start : start + length], length)
            if level > best:
                best = level
                if best == 6:
                    return best
    return best


def _combine_levels(levels: list[int]) -> int:
    """Combine four directional threat levels into one point score."""

    max_level = max(levels) if levels else 0
    if max_level >= 6:
        return 10_000_000
    if max_level >= 5:
        return 1_000_000

    fours = levels.count(4)
    threes = levels.count(3)
    twos = levels.count(2)

    if fours >= 2:
        return 900_000
    if fours == 1 and threes >= 1:
        return 500_000
    if fours == 1:
        return 120_000
    if threes >= 2:
        return 200_000
    if threes == 1:
        return 12_000
    if twos >= 2:
        return 1_000
    if twos == 1:
        return 500
    if 1 in levels:
        return 80
    return 10


def point_score(state: State, index: int, player: int) -> int:
    """Estimate the value of playing *index* for *player*."""

    tables = _tables(state.size)
    levels: list[int] = []
    for center, line in tables.lines[index]:
        levels.append(_line_level(state, index, player, center, line))
    return _combine_levels(levels)


def _centre_bonus(index: int, size: int) -> int:
    centre = (size - 1) / 2
    row, col = divmod(index, size)
    distance = abs(row - centre) + abs(col - centre)
    return max(0, 20 - int(distance))


def analyse_candidates(state: State) -> tuple[list[tuple[int, int, int, int]], int]:
    """Return ordered candidate moves and a static evaluation.

    Each candidate entry is ``(priority, index, attack, defence)``.  The
    static evaluation is the sum of attack minus defence over all candidates,
    which is a reasonably robust board-level heuristic for alpha-beta leaves.
    """

    moves = candidate_moves(state)
    if not moves:
        return [], 0

    me = state.turn
    opponent = other(me)
    entries: list[tuple[int, int, int, int]] = []
    total = 0

    for index in moves:
        attack = point_score(state, index, me)
        defence = point_score(state, index, opponent)
        total += attack - defence
        priority = attack * 2 + defence + _centre_bonus(index, state.size)
        entries.append((priority, index, attack, defence))

    entries.sort(key=lambda item: item[0], reverse=True)
    total = max(-MATE_SCORE, min(MATE_SCORE, total))
    return entries, total


def _window_value(p: int, e: int, blockers: int, open_ends: int) -> int:
    """Score one six-cell window for a single colour."""

    if p >= 5:
        return 1_000_000

    if p == 4:
        if blockers == 0:
            if open_ends == 2:
                return 1_000_000
            if open_ends == 1:
                return 100_000
            return 0
        if blockers == 1 and e == 1:
            return 80_000 if open_ends >= 1 else 0
        return 0

    if p == 3:
        if blockers == 0:
            if open_ends == 2:
                return 18_000
            if open_ends == 1:
                return 3_000
            return 0
        if blockers == 1 and e >= 2:
            return 1_500 if open_ends >= 1 else 200
        return 0

    if p == 2:
        if blockers == 0:
            if open_ends == 2:
                return 400
            if open_ends == 1:
                return 80
            return 0
        if blockers <= 1 and e >= 2:
            return 20
        return 0

    if p == 1:
        return 5
    return 0


def evaluate_state(state: State) -> int:
    """Fast full-board evaluation based on bitboard six-cell windows."""

    tables = _tables(state.size)
    black = state.black_mask
    white = state.white_mask
    occupied = black | white
    black_score = 0
    white_score = 0

    for mask, before, after in tables.windows6:
        p = (black & mask).bit_count()
        if p:
            w = (white & mask).bit_count()
            if w:
                continue
            e = 6 - p
            open_ends = int(bool(before and not (occupied & before))) + int(
                bool(after and not (occupied & after))
            )
            black_score += _window_value(p, e, 0, open_ends)
            continue

        w = (white & mask).bit_count()
        if not w:
            continue
        e = 6 - w
        open_ends = int(bool(before and not (occupied & before))) + int(
            bool(after and not (occupied & after))
        )
        white_score += _window_value(w, e, 0, open_ends)

    score = black_score - white_score
    score = max(-MATE_SCORE, min(MATE_SCORE, score))
    return score if state.turn == BLACK else -score


def _fast_shape_score(count: int, open_ends: int) -> int:
    if count >= 5:
        return 1_000_000
    if count == 4:
        return 100_000 if open_ends == 2 else 10_000 if open_ends == 1 else 0
    if count == 3:
        return 5_000 if open_ends == 2 else 500 if open_ends == 1 else 0
    if count == 2:
        return 300 if open_ends == 2 else 50 if open_ends == 1 else 0
    if count == 1:
        return 10 if open_ends == 2 else 1
    return 0


def fast_point_score(state: State, index: int, player: int) -> int:
    """Cheap continuous-line heuristic used for internal move ordering."""

    size = state.size
    row, col = divmod(index, size)
    board = state.board
    best = 0
    for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
        count = 1
        open_ends = 0
        for sign in (1, -1):
            r = row + dr * sign
            c = col + dc * sign
            while 0 <= r < size and 0 <= c < size and board[r * size + c] == player:
                count += 1
                r += dr * sign
                c += dc * sign
            if 0 <= r < size and 0 <= c < size and board[r * size + c] == EMPTY:
                open_ends += 1
        best = max(best, _fast_shape_score(count, open_ends))
    return best


def ordered_moves_fast(state: State) -> list[tuple[int, int, int, int]]:
    """Return cheaply ordered candidate moves for internal search nodes."""

    moves = candidate_moves(state)
    if not moves:
        return []

    me = state.turn
    opponent = other(me)
    entries: list[tuple[int, int, int, int]] = []
    for index in moves:
        attack = fast_point_score(state, index, me)
        defence = fast_point_score(state, index, opponent)
        priority = attack * 2 + defence + _centre_bonus(index, state.size)
        entries.append((priority, index, attack, defence))
    entries.sort(key=lambda item: item[0], reverse=True)
    return entries


class AIPlayer:
    """Configurable alpha-beta Gomoku player."""

    def __init__(
        self,
        size: int = DEFAULT_BOARD_SIZE,
        max_depth: int = 6,
        time_limit: float = 1.8,
        max_branch: int = 24,
        seed: Optional[int] = None,
        on_iteration: Optional[Callable[[int, int, float, int, int], None]] = None,
    ):
        self.size = size
        self.max_depth = max_depth
        self.time_limit = time_limit
        self.max_branch = max_branch
        self.on_iteration = on_iteration
        self._random = random.Random(seed)
        self._tt: dict[int, _TTEntry] = {}
        self.nodes = 0
        self.cutoffs = 0

    def choose_move(self, state: State) -> SearchStats:
        """Choose a move for the side to move in *state*."""

        started = time.perf_counter()
        self._tt = {}
        self.nodes = 0
        self.cutoffs = 0

        ordered, static = analyse_candidates(state)
        if not ordered:
            return SearchStats(-1, 0, 0, self.nodes, time.perf_counter() - started, [], size=state.size)

        # Short-circuit one-move tactics.  This both speeds up play and
        # avoids the horizon effect around forced wins.
        win_moves = [item[1] for item in ordered if item[2] >= WIN_SCORE]
        block_moves = [item[1] for item in ordered if item[3] >= WIN_SCORE]
        if win_moves:
            move = win_moves[0]
            return SearchStats(move, WIN_SCORE, 1, self.nodes, time.perf_counter() - started, [move], size=state.size)
        if block_moves:
            move = block_moves[0]
            return SearchStats(move, -WIN_SCORE + state.ply, 1, self.nodes, time.perf_counter() - started, [move], size=state.size)

        deadline = started + self.time_limit
        best_move = ordered[0][1]
        best_score = static
        best_depth = 0
        pv: list[int] = [best_move]

        for depth in range(1, self.max_depth + 1):
            try:
                score, move = self._search_root(state, depth, deadline)
            except SearchTimeout:
                break

            best_score = score
            best_move = move
            best_depth = depth
            pv = self._collect_pv(state, depth, move)

            elapsed = time.perf_counter() - started
            if self.on_iteration is not None:
                self.on_iteration(depth, score, elapsed, self.nodes, move)

            # A proven forced win needs no deeper search.
            if score >= WIN_SCORE - state.ply - 2:
                break
            if time.perf_counter() >= deadline:
                break

        return SearchStats(
            move=best_move,
            score=best_score,
            depth=best_depth,
            nodes=self.nodes,
            elapsed=time.perf_counter() - started,
            pv=pv,
            cutoffs=self.cutoffs,
            size=state.size,
        )

    def _search_root(
        self, state: State, depth: int, deadline: float
    ) -> tuple[int, int]:
        ordered = ordered_moves_fast(state)
        if not ordered:
            return 0, -1

        best = -INF
        best_move = ordered[0][1]
        alpha = -INF
        beta = INF

        for item in ordered:
            if time.perf_counter() >= deadline:
                raise SearchTimeout
            _, index, _, _ = item
            player = state.make_move(index)
            try:
                if check_win_flat(state.board, index, player, state.size):
                    score = WIN_SCORE - state.ply
                elif state.is_full:
                    score = 0
                else:
                    score = -self._negamax(state, depth - 1, -beta, -alpha, deadline)
            finally:
                state.unmake_move()

            if score > best:
                best = score
                best_move = index
            if best > alpha:
                alpha = best

        return best, best_move

    def _negamax(
        self,
        state: State,
        depth: int,
        alpha: int,
        beta: int,
        deadline: float,
    ) -> int:
        self.nodes += 1
        if (self.nodes & 63) == 0 and time.perf_counter() >= deadline:
            raise SearchTimeout

        key = state.zobrist
        entry = self._tt.get(key)
        if entry is not None and entry.depth >= depth:
            if entry.flag == EXACT:
                return entry.score
            if entry.flag == LOWER_BOUND:
                if entry.score > alpha:
                    alpha = entry.score
            elif entry.flag == UPPER_BOUND:
                if entry.score < beta:
                    beta = entry.score
            if alpha >= beta:
                self.cutoffs += 1
                return entry.score

        ordered = ordered_moves_fast(state)
        if not ordered:
            return 0
        if depth <= 0:
            return evaluate_state(state)

        original_alpha = alpha
        best = -INF
        best_move: Optional[int] = None
        limit = min(len(ordered), self.max_branch)

        for item in ordered[:limit]:
            _, index, _, _ = item
            player = state.make_move(index)
            try:
                if check_win_flat(state.board, index, player, state.size):
                    score = WIN_SCORE - state.ply
                elif state.is_full:
                    score = 0
                else:
                    score = -self._negamax(state, depth - 1, -beta, -alpha, deadline)
            finally:
                state.unmake_move()

            if score > best:
                best = score
                best_move = index
            if best > alpha:
                alpha = best
            if alpha >= beta:
                self.cutoffs += 1
                break

        if best <= original_alpha:
            flag = UPPER_BOUND
        elif best >= beta:
            flag = LOWER_BOUND
        else:
            flag = EXACT
        self._tt[key] = _TTEntry(depth, best, flag, best_move)
        return best

    def _collect_pv(self, state: State, depth: int, first_move: int) -> list[int]:
        """Reconstruct a principal variation from the transposition table."""

        pv = [first_move]
        tmp = state.copy()
        tmp.make_move(first_move)
        for _ in range(depth - 1):
            entry = self._tt.get(tmp.zobrist)
            if entry is None or entry.best_move is None:
                break
            move = entry.best_move
            pv.append(move)
            tmp.make_move(move)
        return pv


def ai_move(
    board: list[list[int]],
    ai_piece: int,
    human_piece: int,
    size: Optional[int] = None,
    **kwargs,
) -> tuple[int, int]:
    """Compatibility helper that mirrors the old ``ai_move`` API.

    It accepts a two dimensional board and returns a zero based ``(row, col)``.
    """

    if size is None:
        size = len(board)
    state = State.from_board(board, turn=ai_piece)
    player = AIPlayer(size=size, **kwargs)
    stats = player.choose_move(state)
    return index_to_move(stats.move, size)
