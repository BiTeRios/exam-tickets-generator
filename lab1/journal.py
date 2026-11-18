"""Журнал journal.xlsx: создание файла с шапкой и дозапись строк.

Каждая запись сохраняется на диск сразу. Книга пишется во временный файл рядом
с журналом, сбрасывается на диск и атомарно подменяет журнал (os.replace).
Поэтому аварийное завершение программы в момент записи не портит
уже сохранённые строки.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

HEADER = ["Last name", "First name", "Номер билета", "Дата и время"]
SHEET_TITLE = "Journal"
DATETIME_FORMAT = "DD.MM.YYYY HH:MM:SS"
COLUMN_WIDTHS = {"A": 20, "B": 20, "C": 15, "D": 22}
TEXT_COLUMNS = (1, 2)  # фамилия и имя всегда пишутся как текст


class JournalError(Exception):
    """Запись в журнал не удалась; журнал остался прежним."""

    def __init__(self, path: Path, message: str):
        super().__init__(message)
        self.path = path


class JournalLockedError(JournalError):
    """Файл журнала занят другой программой (обычно открыт в Excel)."""

    def __init__(self, path: Path):
        super().__init__(
            path,
            f"Файл {path.name} открыт в другой программе (например, в Excel).",
        )


class JournalCorruptedError(JournalError):
    """Файл журнала существует, но это не книга Excel или она повреждена."""

    def __init__(self, path: Path, reason: object):
        super().__init__(
            path,
            f"Файл {path.name} повреждён и не читается ({reason}). "
            "Переименуйте или удалите его, и журнал будет создан заново.",
        )


class JournalWriteError(JournalError):
    """Нет доступа на запись в папку журнала или диск переполнен."""

    def __init__(self, path: Path, reason: object):
        super().__init__(path, f"Не удалось записать {path.name}: {reason}")


def append_record(
    path: str | os.PathLike,
    last_name: str,
    first_name: str,
    ticket: int,
    when: datetime | None = None,
) -> None:
    """Дописывает строку в конец журнала. Создаёт журнал с шапкой, если его нет.

    Существующие строки не изменяются. При ошибке поднимает JournalError
    (или её наследника), журнал при этом остаётся прежним.
    """
    path = Path(path)
    when = when or datetime.now().replace(microsecond=0)

    workbook = _open_or_create(path)
    sheet = _journal_sheet(workbook)
    sheet.append([last_name, first_name, ticket, when])
    row = sheet.max_row
    for column in TEXT_COLUMNS:
        # Иначе имя вида «=1+1» Excel посчитает формулой.
        sheet.cell(row=row, column=column).data_type = "s"
    sheet.cell(row=row, column=4).number_format = DATETIME_FORMAT
    _save_atomically(workbook, path)


def read_rows(path: str | os.PathLike) -> list[tuple]:
    """Возвращает все строки журнала, включая шапку (удобно для проверок)."""
    workbook = load_workbook(Path(path), read_only=True)
    try:
        return [tuple(row) for row in _journal_sheet(workbook).iter_rows(values_only=True)]
    finally:
        workbook.close()


def _journal_sheet(workbook: Workbook) -> Worksheet:
    # Не workbook.active: если журнал сохранили в Excel с другим активным листом,
    # строки не должны уйти не туда.
    if SHEET_TITLE in workbook.sheetnames:
        return workbook[SHEET_TITLE]
    return workbook.worksheets[0]


def _open_or_create(path: Path) -> Workbook:
    if path.exists():
        try:
            return load_workbook(path)
        except PermissionError as error:
            raise JournalLockedError(path) from error
        except Exception as error:  # пустой файл, не xlsx, битый архив
            raise JournalCorruptedError(path, error) from error

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = SHEET_TITLE
    sheet.append(HEADER)
    for column, width in COLUMN_WIDTHS.items():
        sheet.column_dimensions[column].width = width
    return workbook


def _save_atomically(workbook: Workbook, path: Path) -> None:
    tmp_name = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix="~journal_tmp_", suffix=".xlsx", dir=path.parent)
        os.close(fd)
        workbook.save(tmp_name)
        # Сбрасываем данные на диск до подмены, чтобы пережить выключение питания.
        with open(tmp_name, "rb+") as tmp_file:
            os.fsync(tmp_file.fileno())
        try:
            os.replace(tmp_name, path)
        except PermissionError as error:
            raise JournalLockedError(path) from error
    except JournalError:
        raise
    except OSError as error:  # нет прав на папку, диск полон, антивирус держит файл
        raise JournalWriteError(path, error) from error
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.remove(tmp_name)
