"""Посимвольное чтение строки с перехватом ESC.

input() ждёт Enter и не видит ESC, поэтому строка собирается из отдельных
нажатий: Enter завершает ввод, Backspace стирает символ, ESC прерывает ввод.
"""

from __future__ import annotations

import sys
from typing import Callable

ESC = "\x1b"
ENTER_KEYS = ("\r", "\n")
BACKSPACE_KEYS = ("\b", "\x7f")
CTRL_C = "\x03"
# На Windows стрелки, F1..F12 и т.п. приходят парой: префикс + код клавиши.
SPECIAL_KEY_PREFIXES = ("\x00", "\xe0")

GetCh = Callable[[], str]
Write = Callable[[str], None]


class EscapePressed(Exception):
    """Пользователь нажал ESC во время ввода."""


def read_line(prompt: str, getch: GetCh, write: Write) -> str:
    """Выводит prompt и собирает строку по нажатиям клавиш."""
    write(prompt)
    chars: list[str] = []
    while True:
        key = getch()
        if key == "":  # конец ввода (EOF) — ведём себя как ESC
            raise EscapePressed
        if key == ESC:
            write("\n")
            raise EscapePressed
        if key == CTRL_C:
            raise KeyboardInterrupt
        if key in ENTER_KEYS:
            write("\n")
            return "".join(chars)
        if key in BACKSPACE_KEYS:
            if chars:
                chars.pop()
                write("\b \b")
            continue
        if key in SPECIAL_KEY_PREFIXES:
            getch()  # пропускаем код специальной клавиши
            continue
        if key.isprintable():
            chars.append(key)
            write(key)


def ask_non_empty(prompt: str, getch: GetCh, write: Write) -> str:
    """Запрашивает строку, пока пользователь не введёт непустое значение."""
    while True:
        value = read_line(prompt, getch, write).strip()
        if value:
            return value
        write("Значение не может быть пустым. Повторите ввод.\n")


def wait_enter_or_esc(getch: GetCh) -> bool:
    """Ждёт Enter (возвращает True) или ESC (возвращает False)."""
    while True:
        key = getch()
        if key in ENTER_KEYS:
            return True
        if key in (ESC, ""):
            return False
        if key == CTRL_C:
            raise KeyboardInterrupt
        if key in SPECIAL_KEY_PREFIXES:
            getch()


def system_getch() -> GetCh:
    """Возвращает функцию чтения одной клавиши для текущей ОС."""
    if sys.platform == "win32":
        import msvcrt

        return msvcrt.getwch
    return _posix_getch


def _posix_getch() -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
