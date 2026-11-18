"""Лабораторная работа №2: генератор билетов с графическим интерфейсом."""


class SourceFileError(Exception):
    """Входной файл (students.xlsx или tickets.docx) отсутствует или не читается."""
