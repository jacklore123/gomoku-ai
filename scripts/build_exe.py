"""Build the CLI and GUI executables with PyInstaller."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run_pyinstaller(name: str, entry: str, *, console: bool) -> None:
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--name",
        name,
    ]
    args.append("--console" if console else "--noconsole")
    args.append(entry)
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    print("Building GomokuAI_CLI.exe ...")
    run_pyinstaller("GomokuAI_CLI", "gomoku_cli.py", console=True)
    print("Building GomokuAI_GUI.exe ...")
    run_pyinstaller("GomokuAI_GUI", "gomoku_gui.py", console=False)
    print("Build complete. See the dist/ directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
