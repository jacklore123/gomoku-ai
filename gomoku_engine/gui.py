"""Tkinter graphical interface for the Gomoku AI."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .ai import AIPlayer, LEVEL_PRESETS, State
from .board import (
    BLACK,
    DEFAULT_BOARD_SIZE,
    EMPTY,
    WHITE,
    check_win_flat,
    other,
    star_points,
    winning_line,
)


ROLE_HUMAN = "human"
ROLE_AI = "ai"

MODE_PVP = "双人对战"
MODE_HUMAN_BLACK = "人机对战（我执黑先手）"
MODE_AI_BLACK = "人机对战（电脑执黑先手）"
MODE_AI_AI = "AI 对战 AI"

ROLE_NAME = {
    ROLE_HUMAN: "玩家",
    ROLE_AI: "电脑",
}

PIECE_NAME = {
    BLACK: "黑棋",
    WHITE: "白棋",
}

DIFFICULTIES = {
    "低": LEVEL_PRESETS["low"],
    "中": LEVEL_PRESETS["medium"],
    "高": LEVEL_PRESETS["high"],
}


class GomokuApp:
    def __init__(self, root: tk.Tk, size: int = DEFAULT_BOARD_SIZE):
        self.root = root
        self.root.title("五子棋 AI")
        self.root.resizable(False, False)

        self.size = size
        self.ai = AIPlayer(
            size=size,
            max_depth=DIFFICULTIES["中"]["max_depth"],
            time_limit=DIFFICULTIES["中"]["time_limit"],
            max_branch=DIFFICULTIES["中"]["max_branch"],
        )

        self.search_id = 0
        self.thinking = False
        self.winner: int | None = None
        self.winning_cells: list[int] = []
        self.last_move: int | None = None

        self._build_controls()
        self._build_canvas_container()
        self._create_canvas()
        self.start_game()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_controls(self) -> None:
        control = ttk.Frame(self.root, padding=(12, 10))
        control.pack(fill="x")

        ttk.Label(control, text="游戏模式：").pack(side="left")
        self.mode_var = tk.StringVar(value=MODE_HUMAN_BLACK)
        mode_menu = ttk.OptionMenu(
            control,
            self.mode_var,
            MODE_HUMAN_BLACK,
            MODE_HUMAN_BLACK,
            MODE_AI_BLACK,
            MODE_AI_AI,
            MODE_PVP,
        )
        mode_menu.pack(side="left", padx=(0, 10))

        ttk.Label(control, text="棋盘：").pack(side="left")
        self.size_var = tk.StringVar(value=str(self.size))
        size_menu = ttk.OptionMenu(
            control,
            self.size_var,
            str(self.size),
            "15",
            "17",
            "19",
            command=self._on_size_change,
        )
        size_menu.pack(side="left", padx=(0, 10))

        ttk.Label(control, text="AI 强度：").pack(side="left")
        self.difficulty_var = tk.StringVar(value="中")
        difficulty_menu = ttk.OptionMenu(
            control,
            self.difficulty_var,
            "中",
            "低",
            "中",
            "高",
            command=self._on_difficulty_change,
        )
        difficulty_menu.pack(side="left", padx=(0, 10))

        ttk.Button(control, text="开始新对局", command=self.start_game).pack(side="left")
        ttk.Button(control, text="悔棋", command=self.undo_move).pack(side="left", padx=(8, 0))

    def _build_canvas_container(self) -> None:
        self.canvas_container = ttk.Frame(self.root)
        self.canvas_container.pack(padx=10, pady=4)

        self.status_var = tk.StringVar()
        status = ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="center",
            padding=(10, 8),
        )
        status.pack(fill="x", side="bottom")

    def _create_canvas(self) -> None:
        self.cell = 32 if self.size >= 19 else 36
        self.margin = 48
        board_length = self.cell * (self.size - 1)
        canvas_size = board_length + self.margin * 2

        self.canvas = tk.Canvas(
            self.canvas_container,
            width=canvas_size,
            height=canvas_size,
            bg="#8b5a2b",
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def _rebuild_canvas(self) -> None:
        self.canvas.destroy()
        self._create_canvas()

    def _on_size_change(self, _value: str) -> None:
        new_size = int(self.size_var.get())
        if new_size == self.size:
            return
        self.size = new_size
        self.ai.size = new_size
        self._rebuild_canvas()
        self.start_game()

    def _on_difficulty_change(self, _value: str) -> None:
        config = DIFFICULTIES[self.difficulty_var.get()]
        self.ai.max_depth = config["max_depth"]
        self.ai.time_limit = config["time_limit"]
        self.ai.max_branch = config["max_branch"]

    # ------------------------------------------------------------------
    # Game management
    # ------------------------------------------------------------------
    def current_role(self) -> str:
        mode = self.mode_var.get()
        piece = self.state.turn
        if mode == MODE_PVP:
            return ROLE_HUMAN
        if mode == MODE_AI_AI:
            return ROLE_AI
        if mode == MODE_HUMAN_BLACK:
            return ROLE_HUMAN if piece == BLACK else ROLE_AI
        return ROLE_AI if piece == BLACK else ROLE_HUMAN

    def game_over(self) -> bool:
        return self.winner is not None

    def start_game(self) -> None:
        self.search_id += 1
        self.state = State(self.size)
        self.winner = None
        self.winning_cells = []
        self.last_move = None
        self.thinking = False
        self.draw_board()
        self.update_status()

        if self.current_role() == ROLE_AI:
            self.root.after(350, self.ai_play)

    def update_status(self, extra: str | None = None) -> None:
        if extra is not None:
            self.status_var.set(extra)
            return
        if self.winner == 0:
            self.status_var.set("棋盘已满，双方平局！点击“开始新对局”再来一局。")
            return
        if self.winner in (BLACK, WHITE):
            role = self._role_for_piece(self.winner)
            self.status_var.set(
                f"恭喜 {PIECE_NAME[self.winner]}（{ROLE_NAME[role]}）获胜！"
                "点击“开始新对局”再来一局。"
            )
            return

        piece = self.state.turn
        role = ROLE_NAME[self.current_role()]
        self.status_var.set(
            f"轮到 {PIECE_NAME[piece]}（{role}），请点击棋盘落子。"
        )

    def _role_for_piece(self, piece: int) -> str:
        mode = self.mode_var.get()
        if mode == MODE_PVP:
            return ROLE_HUMAN
        if mode == MODE_AI_AI:
            return ROLE_AI
        if mode == MODE_HUMAN_BLACK:
            return ROLE_HUMAN if piece == BLACK else ROLE_AI
        return ROLE_AI if piece == BLACK else ROLE_HUMAN

    # ------------------------------------------------------------------
    # Input and AI
    # ------------------------------------------------------------------
    def on_canvas_click(self, event) -> None:
        if self.game_over() or self.thinking:
            return
        if self.current_role() != ROLE_HUMAN:
            return

        index = self.pixel_to_cell(event.x, event.y)
        if index is None or self.state.board[index] != EMPTY:
            return
        self.make_move(index)

    def ai_play(self) -> None:
        if self.game_over() or self.thinking or self.current_role() != ROLE_AI:
            return

        self.thinking = True
        search_id = self.search_id
        state_copy = self.state.copy()
        difficulty = self.difficulty_var.get()
        self.update_status(f"电脑思考中（{difficulty}）……")
        self.root.update_idletasks()

        def worker() -> None:
            try:
                stats = self.ai.choose_move(state_copy)
            except Exception as exc:  # pragma: no cover - defensive UI guard
                self.root.after(0, lambda: self._ai_error(exc, search_id))
                return
            self.root.after(0, lambda: self._apply_ai_move(stats, search_id))

        threading.Thread(target=worker, daemon=True).start()

    def _ai_error(self, exc: Exception, search_id: int) -> None:
        if search_id != self.search_id:
            return
        self.thinking = False
        self.update_status(f"AI 计算出错：{exc}")

    def _apply_ai_move(self, stats, search_id: int) -> None:
        if search_id != self.search_id:
            return
        if self.game_over() or self.current_role() != ROLE_AI:
            self.thinking = False
            return
        self.make_move(stats.move, stats)

    def make_move(self, index: int, stats=None) -> None:
        piece = self.state.make_move(index)
        self.last_move = index

        if check_win_flat(self.state.board, index, piece, self.size):
            self.winner = piece
            self.winning_cells = winning_line(self.state.board, index, piece, self.size)
            self.thinking = False
            self.draw_board()
            self.update_status()
            self.show_result_popup()
            return

        if self.state.is_full:
            self.winner = 0
            self.thinking = False
            self.draw_board()
            self.update_status()
            self.show_result_popup()
            return

        self.thinking = False
        self.draw_board()
        if stats is not None:
            self.update_status(
                f"电脑落子 {stats.move_text}，深度 {stats.depth}，"
                f"节点 {stats.nodes}，用时 {stats.elapsed:.2f}s。"
            )
        else:
            self.update_status()

        if self.current_role() == ROLE_AI:
            self.root.after(250, self.ai_play)

    def undo_move(self) -> None:
        if self.thinking:
            return
        if not self.state.stones:
            return
        self.search_id += 1
        self.state.unmake_move()
        if self.state.stones:
            self.last_move = self.state.stones[-1]
        else:
            self.last_move = None
        self.winner = None
        self.winning_cells = []
        self.draw_board()
        self.update_status()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def pixel_to_cell(self, x: int, y: int) -> int | None:
        origin = self.margin
        end = origin + self.cell * (self.size - 1)
        if not (origin - 12 <= x <= end + 12 and origin - 12 <= y <= end + 12):
            return None

        col = round((x - origin) / self.cell)
        row = round((y - origin) / self.cell)
        col = min(max(col, 0), self.size - 1)
        row = min(max(row, 0), self.size - 1)
        return row * self.size + col

    def draw_board(self) -> None:
        canvas = self.canvas
        canvas.delete("all")

        origin = self.margin
        end = origin + self.cell * (self.size - 1)

        canvas.create_rectangle(
            origin - 12,
            origin - 12,
            end + 12,
            end + 12,
            fill="#dcb35c",
            outline="#5a3c1a",
            width=2,
        )
        canvas.create_rectangle(
            origin,
            origin,
            end,
            end,
            fill="#dcb35c",
            outline="",
        )

        line_color = "#5a3c1a"
        for i in range(self.size):
            position = self.cell_center(i)
            canvas.create_line(origin, position, end, position, fill=line_color)
            canvas.create_line(position, origin, position, end, fill=line_color)

        for i in range(self.size):
            position = self.cell_center(i)
            canvas.create_text(
                origin - 24,
                position,
                text=str(i + 1),
                fill="#3a240e",
                font=("Microsoft YaHei UI", 8),
            )
            canvas.create_text(
                position,
                origin - 24,
                text=str(i + 1),
                fill="#3a240e",
                font=("Microsoft YaHei UI", 8),
            )

        for row, col in star_points(self.size):
            x, y = self.cell_center(col), self.cell_center(row)
            canvas.create_oval(
                x - 4,
                y - 4,
                x + 4,
                y + 4,
                fill="#3a240e",
                outline="",
            )

        for index, piece in enumerate(self.state.board):
            if piece != EMPTY:
                self.draw_stone(index, piece)

        if self.last_move is not None and not self.game_over():
            x, y = self.index_center(self.last_move)
            canvas.create_oval(
                x - 5,
                y - 5,
                x + 5,
                y + 5,
                outline="#e74c3c",
                width=2,
            )

        for index in self.winning_cells:
            self.highlight_stone(index)

    def cell_center(self, value: int) -> int:
        return self.margin + value * self.cell

    def index_center(self, index: int) -> tuple[int, int]:
        row, col = divmod(index, self.size)
        return self.cell_center(col), self.cell_center(row)

    def stone_radius(self) -> int:
        return max(8, int(self.cell * 0.42))

    def stone_coords(self, index: int) -> tuple[int, int, int, int]:
        radius = self.stone_radius()
        x, y = self.index_center(index)
        return x - radius, y - radius, x + radius, y + radius

    def draw_stone(self, index: int, piece: int) -> None:
        x1, y1, x2, y2 = self.stone_coords(index)
        if piece == BLACK:
            fill, outline = "#111111", "#000000"
        else:
            fill, outline = "#fdfdfd", "#666666"
        self.canvas.create_oval(
            x1,
            y1,
            x2,
            y2,
            fill=fill,
            outline=outline,
            width=1,
        )

    def highlight_stone(self, index: int) -> None:
        x1, y1, x2, y2 = self.stone_coords(index)
        self.canvas.create_oval(
            x1,
            y1,
            x2,
            y2,
            outline="#e74c3c",
            width=3,
        )

    def show_result_popup(self) -> None:
        if self.winner == 0:
            messagebox.showinfo("游戏结束", "棋盘已满，双方平局！")
        elif self.winner in (BLACK, WHITE):
            role = ROLE_NAME[self._role_for_piece(self.winner)]
            messagebox.showinfo(
                "游戏结束",
                f"恭喜 {PIECE_NAME[self.winner]}（{role}）获胜！",
            )


def main() -> None:
    root = tk.Tk()
    GomokuApp(root, size=DEFAULT_BOARD_SIZE)
    root.mainloop()


if __name__ == "__main__":
    main()
