"""Консольный генератор экзаменационных билетов (лабораторная работа №1).

Цикл работы: фамилия -> имя -> случайный билет 1..20 -> вывод номера ->
дозапись в journal.xlsx -> снова фамилия. ESC во время ввода завершает работу.
"""

from __future__ import annotations

import random
from pathlib import Path

from .console_input import GetCh, Write, EscapePressed, ask_non_empty, wait_enter_or_esc
from .journal import JournalError, JournalLockedError, append_record

TICKET_MIN = 1
TICKET_MAX = 20
DEFAULT_JOURNAL = Path(__file__).resolve().parent / "journal.xlsx"


def generate_ticket(rng: random.Random) -> int:
    return rng.randint(TICKET_MIN, TICKET_MAX)


def save_with_retry(
    journal_path: Path,
    last_name: str,
    first_name: str,
    ticket: int,
    getch: GetCh,
    write: Write,
) -> bool:
    """Сохраняет запись. Если не вышло, объясняет причину и предлагает повторить.

    Возвращает True, если запись сохранена, False, если пользователь отказался.
    """
    while True:
        try:
            append_record(journal_path, last_name, first_name, ticket)
            return True
        except JournalError as error:
            action = "Закройте файл" if isinstance(error, JournalLockedError) else "Исправьте проблему"
            write(
                f"Запись не сохранена. {error}\n"
                f"{action} и нажмите Enter для повтора или ESC, чтобы не сохранять эту запись.\n"
            )
            if not wait_enter_or_esc(getch):
                write("Запись НЕ сохранена в журнал.\n")
                return False


def run(journal_path: Path, getch: GetCh, write: Write, rng: random.Random) -> None:
    write("Для выхода нажмите ESC.\n")
    while True:
        try:
            last_name = ask_non_empty("Last name: ", getch, write)
            first_name = ask_non_empty("First name: ", getch, write)
        except EscapePressed:
            write("Работа завершена.\n")
            return

        ticket = generate_ticket(rng)
        write(f"Билет № {ticket}\n")
        if save_with_retry(journal_path, last_name, first_name, ticket, getch, write):
            write(f"Запись сохранена в {journal_path.name}.\n")
        write("\n")
