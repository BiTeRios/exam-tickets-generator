"""Журнал results.xlsx: поиск первой выдачи билета студенту и дозапись строк."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

HEADER = ["Группа", "Фамилия", "Имя", "Номер билета", "Дата и время", "Повтор (да/нет)"]
SHEET_TITLE = "Results"
DATETIME_FORMAT = "DD.MM.YYYY HH:MM:SS"
COLUMN_WIDTHS = {"A": 14, "B": 18, "C": 16, "D": 15, "E": 22, "F": 17}
TEXT_COLUMNS = (1, 2, 3, 6)  # группа, фамилия, имя, повтор — всегда текст, не формула
REPEAT_YES = "да"
REPEAT_NO = "нет"


class ResultsError(Exception):
    """Журнал не прочитан или не записан; файл остался прежним."""


class ResultsLockedError(ResultsError):
    """results.xlsx занят другой программой (обычно открыт в Excel)."""


class ResultsFileError(ResultsError):
    """results.xlsx повреждён или недоступен для записи — перезаписывать его нельзя."""


def find_first_ticket(path: str | os.PathLike, group: str, last_name: str, first_name: str) -> int | None:
    """Номер билета из самой первой записи по студенту или None, если записей нет."""
    path = Path(path)
    if not path.exists():
        return None
    key = _key(group, last_name, first_name)
    workbook = _load(path, read_only=True)
    try:
        for row in _results_sheet(workbook).iter_rows(min_row=2, max_col=4, values_only=True):
            if len(row) < 4 or _key(*row[:3]) != key:
                continue
            try:
                return int(row[3])
            except (TypeError, ValueError):
                continue  # строка с испорченным номером — ищем дальше
        return None
    finally:
        workbook.close()


def append_result(
    path: str | os.PathLike,
    group: str,
    last_name: str,
    first_name: str,
    ticket: int,
    repeat: bool,
    when: datetime | None = None,
) -> None:
    """Дописывает строку в конец журнала и сразу сохраняет файл."""
    path = Path(path)
    when = when or datetime.now().replace(microsecond=0)
    workbook = _load(path, read_only=False) if path.exists() else _create()
    sheet = _results_sheet(workbook)
    sheet.append([group, last_name, first_name, ticket, when, REPEAT_YES if repeat else REPEAT_NO])
    row = sheet.max_row
    for column in TEXT_COLUMNS:
        sheet.cell(row=row, column=column).data_type = "s"
    sheet.cell(row=row, column=5).number_format = DATETIME_FORMAT
    _save_atomically(workbook, path)


def read_rows(path: str | os.PathLike) -> list[tuple]:
    workbook = _load(Path(path), read_only=True)
    try:
        return [tuple(row) for row in _results_sheet(workbook).iter_rows(values_only=True)]
    finally:
        workbook.close()


def _key(group: object, last_name: object, first_name: object) -> tuple[str, str, str]:
    return tuple("" if v is None else str(v).strip().casefold() for v in (group, last_name, first_name))


def _results_sheet(workbook: Workbook) -> Worksheet:
    if SHEET_TITLE in workbook.sheetnames:
        return workbook[SHEET_TITLE]
    return workbook.worksheets[0]


def _load(path: Path, read_only: bool) -> Workbook:
    try:
        return load_workbook(path, read_only=read_only)
    except PermissionError as error:
        raise ResultsLockedError(f"Файл {path.name} открыт в другой программе (например, в Excel) или защищён от записи.") from error
    except Exception as error:
        raise ResultsFileError(
            f"Файл {path} повреждён и не читается ({error}). "
            "Переименуйте или удалите его — журнал будет создан заново."
        ) from error


def _create() -> Workbook:
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
        fd, tmp_name = tempfile.mkstemp(prefix="~results_tmp_", suffix=".xlsx", dir=path.parent)
        os.close(fd)
        workbook.save(tmp_name)
        with open(tmp_name, "rb+") as tmp_file:
            os.fsync(tmp_file.fileno())
        try:
            os.replace(tmp_name, path)
        except PermissionError as error:
            raise ResultsLockedError(
                f"Файл {path.name} открыт в другой программе (например, в Excel) или защищён от записи."
            ) from error
    except ResultsError:
        raise
    except OSError as error:
        raise ResultsFileError(f"Не удалось записать {path.name}: {error}") from error
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.remove(tmp_name)
