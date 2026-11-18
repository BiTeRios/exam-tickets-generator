"""Общие помощники для тестов лаб 2: генерация входных файлов во временной папке."""

from __future__ import annotations

import pytest
from docx import Document
from openpyxl import Workbook

DEFAULT_GROUPS = {
    "ИТ-41": [("Иванов", "Иван"), ("Петрова", "Анна")],
    "ИТ-42": [("Морарь", "Ион")],
    "ИТ-43": [],
}


def write_students(path, groups=None):
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, students in (groups or DEFAULT_GROUPS).items():
        sheet = workbook.create_sheet(name)
        sheet.append(["Фамилия", "Имя"])
        for row in students:
            sheet.append(list(row))
    workbook.save(path)


def write_docx(path, lines):
    """lines: строки абзацев; кортеж ("текст", "List Number") — абзац со стилем."""
    document = Document()
    for line in lines:
        if isinstance(line, tuple):
            document.add_paragraph(line[0], style=line[1])
        else:
            document.add_paragraph(line)
    document.save(path)


def ticket_lines(number, count=3):
    return [f"Билет {number}"] + [f"{i}. Вопрос {i} билета {number}" for i in range(1, count + 1)]


@pytest.fixture
def data_dir(tmp_path):
    write_students(tmp_path / "students.xlsx")
    write_docx(tmp_path / "tickets.docx", ticket_lines(1) + ticket_lines(2) + ticket_lines(3))
    return tmp_path
