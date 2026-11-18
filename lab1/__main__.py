"""Точка входа: python -m lab1 [--journal ПУТЬ]."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from .app import DEFAULT_JOURNAL, run
from .console_input import system_getch


def _write(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="Генератор экзаменационных билетов")
    parser.add_argument(
        "--journal",
        type=Path,
        default=DEFAULT_JOURNAL,
        help=f"путь к журналу Excel (по умолчанию {DEFAULT_JOURNAL})",
    )
    args = parser.parse_args()
    try:
        run(args.journal, system_getch(), _write, random.SystemRandom())
    except KeyboardInterrupt:
        _write("\nРабота прервана (Ctrl+C).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
