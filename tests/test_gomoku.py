"""Core rule and tactical tests for the Gomoku AI."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gomoku_engine.ai import AIPlayer, LEVEL_PRESETS, State, ai_move
from gomoku_engine.board import (
    BLACK,
    EMPTY,
    WHITE,
    check_win,
    index_to_move,
    move_to_index,
    new_board,
)


class BoardRulesTest(unittest.TestCase):
    def test_flat_index_conversion(self) -> None:
        self.assertEqual(move_to_index(7, 8, 19), 7 * 19 + 8)
        self.assertEqual(index_to_move(7 * 19 + 8, 19), (7, 8))

    def test_check_win_horizontal(self) -> None:
        board = new_board(15)
        for col in range(5):
            board[7][col] = BLACK
        self.assertTrue(check_win(board, 7, 4, BLACK))
        self.assertFalse(check_win(board, 7, 3, WHITE))

    def test_check_win_diagonal(self) -> None:
        board = new_board(15)
        for i in range(5):
            board[3 + i][3 + i] = WHITE
        self.assertTrue(check_win(board, 7, 7, WHITE))


class TacticsTest(unittest.TestCase):
    def _state_from_rows(self, rows: list[list[int]], turn: int) -> State:
        return State.from_board(rows, turn=turn)

    def test_ai_takes_immediate_win(self) -> None:
        rows = new_board(19)
        for col in range(8, 12):
            rows[9][col] = BLACK
        state = self._state_from_rows(rows, turn=BLACK)
        stats = AIPlayer(size=19, max_depth=2, time_limit=0.1, max_branch=12).choose_move(state)
        self.assertIn(stats.move, (9 * 19 + 7, 9 * 19 + 12))

    def test_ai_blocks_immediate_four(self) -> None:
        rows = new_board(19)
        for col in range(8, 12):
            rows[9][col] = WHITE
        state = self._state_from_rows(rows, turn=BLACK)
        stats = AIPlayer(size=19, max_depth=2, time_limit=0.1, max_branch=12).choose_move(state)
        self.assertIn(stats.move, (9 * 19 + 7, 9 * 19 + 12))

    def test_search_timeout_restores_state(self) -> None:
        rows = new_board(19)
        for row, col in ((8, 8), (8, 9), (9, 8), (10, 10)):
            rows[row][col] = BLACK if (row + col) % 2 == 0 else WHITE
        state = self._state_from_rows(rows, turn=BLACK)
        original = state.copy()
        AIPlayer(
            size=19,
            max_depth=8,
            time_limit=0.001,
            max_branch=24,
        ).choose_move(state)
        self.assertEqual(state.board, original.board)
        self.assertEqual(state.turn, original.turn)
        self.assertEqual(state.stones, original.stones)
        self.assertEqual(state.black_mask, original.black_mask)
        self.assertEqual(state.white_mask, original.white_mask)
        self.assertEqual(state.zobrist, original.zobrist)


class CompatibilityTest(unittest.TestCase):
    def test_ai_move_compatibility(self) -> None:
        board = new_board(15)
        board[7][7] = BLACK
        row, col = ai_move(board, ai_piece=WHITE, human_piece=BLACK, size=15, max_depth=1)
        self.assertTrue(0 <= row < 15)
        self.assertTrue(0 <= col < 15)

    def test_level_presets(self) -> None:
        self.assertSetEqual(set(LEVEL_PRESETS), {"low", "medium", "high"})
        self.assertTrue(LEVEL_PRESETS["low"]["max_depth"] < LEVEL_PRESETS["medium"]["max_depth"])
        self.assertTrue(LEVEL_PRESETS["medium"]["max_depth"] < LEVEL_PRESETS["high"]["max_depth"])


if __name__ == "__main__":
    unittest.main()
