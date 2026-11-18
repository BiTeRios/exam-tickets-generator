import pytest
from openpyxl import Workbook

from lab2 import SourceFileError
from lab2.students import Student, load_groups

from .conftest import write_students


def test_groups_are_sheet_names_in_order(tmp_path):
    path = tmp_path / "students.xlsx"
    write_students(path)
    assert list(load_groups(path)) == ["ИТ-41", "ИТ-42", "ИТ-43"]


def test_students_of_group(tmp_path):
    path = tmp_path / "students.xlsx"
    write_students(path)
    groups = load_groups(path)
    assert groups["ИТ-41"] == [Student("Иванов", "Иван"), Student("Петрова", "Анна")]
    assert [s.display_name for s in groups["ИТ-41"]] == ["Иванов Иван", "Петрова Анна"]


def test_empty_group_has_no_students(tmp_path):
    path = tmp_path / "students.xlsx"
    write_students(path)
    assert load_groups(path)["ИТ-43"] == []


def test_spaces_trimmed_and_blank_or_incomplete_rows_skipped(tmp_path):
    path = tmp_path / "students.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Г1"
    sheet.append(["Фамилия", "Имя"])
    sheet.append(["  Лунгу ", " Виктор  "])
    sheet.append([None, None])
    sheet.append(["Безымянный", None])
    sheet.append(["Русу", "Елена"])
    workbook.save(path)

    assert load_groups(path)["Г1"] == [Student("Лунгу", "Виктор"), Student("Русу", "Елена")]


def test_missing_file_raises_source_error(tmp_path):
    with pytest.raises(SourceFileError):
        load_groups(tmp_path / "students.xlsx")


def test_corrupted_file_raises_source_error(tmp_path):
    path = tmp_path / "students.xlsx"
    path.write_text("not excel", encoding="utf-8")
    with pytest.raises(SourceFileError):
        load_groups(path)
