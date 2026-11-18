"""Чтение students.xlsx: один лист на группу, A — фамилия, B — имя, данные со 2-й строки."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook

from . import SourceFileError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Student:
    last_name: str
    first_name: str

    @property
    def display_name(self) -> str:
        return f"{self.last_name} {self.first_name}"


def load_groups(path: str | os.PathLike) -> dict[str, list[Student]]:
    """Возвращает {имя группы: [студенты]} в порядке листов книги."""
    path = Path(path)
    if not path.exists():
        raise SourceFileError(f"Не найден файл со списком студентов: {path}")
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except Exception as error:  # битый файл, не xlsx, нет доступа
        raise SourceFileError(f"Не удалось прочитать {path.name}: {error}") from error

    try:
        groups: dict[str, list[Student]] = {}
        for sheet in workbook.worksheets:
            students = []
            for row_number, row in enumerate(
                sheet.iter_rows(min_row=2, max_col=2, values_only=True), start=2
            ):
                last_name = _clean(row[0] if len(row) > 0 else None)
                first_name = _clean(row[1] if len(row) > 1 else None)
                if not last_name and not first_name:
                    continue
                if not last_name or not first_name:
                    log.warning(
                        "%s, лист «%s», строка %d: нет фамилии или имени — строка пропущена",
                        path.name, sheet.title, row_number,
                    )
                    continue
                students.append(Student(last_name, first_name))
            groups[sheet.title] = students
        return groups
    finally:
        workbook.close()


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()
