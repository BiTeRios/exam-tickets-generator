"""Журнал journal.xlsx: создание файла с шапкой и дозапись строк.

Каждая запись сохраняется на диск сразу. Файл сначала пишется во временный
файл рядом с журналом, затем атомарно подменяет журнал (os.replace). Поэтому
аварийное завершение программы или выключение компьютера в момент записи
не портит уже сохранённые строки.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook

HEADER = ["Last name", "First name", "Номер билета", "Дата и время"]
SHEET_TITLE = "Journal"
DATETIME_FORMAT = "DD.MM.YYYY HH:MM:SS"
COLUMN_WIDTHS = {"A": 20, "B": 20, "C": 15, "D": 22}


class JournalLockedError(Exception):
    """Файл журнала занят другой программой (обычно открыт в Excel)."""

    def __init__(self, path: Path):
        super().__init__(f"Файл {path} занят другой программой")
        self.path = path


def append_record(
    path: str | os.PathLike,
    last_name: str,
    first_name: str,
    ticket: int,
    when: datetime | None = None,
) -> None:
    """Дописывает строку в конец журнала. Создаёт журнал с шапкой, если его нет.

    Существующие строки не изменяются. При занятом файле поднимает
    JournalLockedError, журнал при этом остаётся прежним.
    """
    path = Path(path)
    when = when or datetime.now().replace(microsecond=0)

    workbook = _open_or_create(path)
    sheet = workbook.active
    sheet.append([last_name, first_name, ticket, when])
    sheet.cell(row=sheet.max_row, column=4).number_format = DATETIME_FORMAT
    _save_atomically(workbook, path)


def read_rows(path: str | os.PathLike) -> list[tuple]:
    """Возвращает все строки журнала, включая шапку (удобно для проверок)."""
    workbook = load_workbook(Path(path), read_only=True)
    try:
        return [tuple(row) for row in workbook.active.iter_rows(values_only=True)]
    finally:
        workbook.close()


def _open_or_create(path: Path) -> Workbook:
    if path.exists():
        try:
            return load_workbook(path)
        except PermissionError as error:
            raise JournalLockedError(path) from error

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = SHEET_TITLE
    sheet.append(HEADER)
    for column, width in COLUMN_WIDTHS.items():
        sheet.column_dimensions[column].width = width
    return workbook


def _save_atomically(workbook: Workbook, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="~journal_tmp_", suffix=".xlsx", dir=path.parent)
    os.close(fd)
    try:
        workbook.save(tmp_name)
        # Сбрасываем данные на диск до подмены, чтобы пережить выключение питания.
        with open(tmp_name, "rb+") as tmp_file:
            os.fsync(tmp_file.fileno())
        try:
            os.replace(tmp_name, path)
        except PermissionError as error:
            raise JournalLockedError(path) from error
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
