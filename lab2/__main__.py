"""Точка входа: python -m lab2 [--data-dir ПАПКА]."""

from __future__ import annotations

import argparse
import logging
import sys
import tkinter as tk
from pathlib import Path

from .controller import Controller
from .ui import TicketApp

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
LOG_FILE = "lab2.log"


def _setup_logging(data_dir: Path) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(data_dir / LOG_FILE, encoding="utf-8"))
    except OSError:
        pass  # без файла лога приложение всё равно работает
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def _enable_high_dpi() -> None:
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Генератор экзаменационных билетов с UI")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"папка с students.xlsx, tickets.docx и results.xlsx (по умолчанию {DEFAULT_DATA_DIR})",
    )
    args = parser.parse_args()
    _setup_logging(args.data_dir)
    _enable_high_dpi()

    root = tk.Tk()
    TicketApp(root, Controller(args.data_dir))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
