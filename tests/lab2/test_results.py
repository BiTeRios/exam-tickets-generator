from datetime import datetime

import pytest
from openpyxl import load_workbook

from lab2 import results
from lab2.results import (
    HEADER,
    ResultsFileError,
    ResultsLockedError,
    append_result,
    find_first_ticket,
    read_rows,
)

WHEN = datetime(2026, 11, 18, 9, 0, 0)


def test_created_with_header_and_row(tmp_path):
    path = tmp_path / "results.xlsx"
    append_result(path, "ИТ-41", "Иванов", "Иван", 3, False, WHEN)
    assert read_rows(path) == [tuple(HEADER), ("ИТ-41", "Иванов", "Иван", 3, WHEN, "нет")]


def test_append_keeps_existing_rows(tmp_path):
    path = tmp_path / "results.xlsx"
    append_result(path, "ИТ-41", "Иванов", "Иван", 3, False, WHEN)
    append_result(path, "ИТ-41", "Петрова", "Анна", 5, False, WHEN)
    before = read_rows(path)
    append_result(path, "ИТ-41", "Иванов", "Иван", 3, True, WHEN)
    after = read_rows(path)
    assert after[: len(before)] == before
    assert after[-1][-1] == "да"


def test_find_first_ticket_returns_topmost_record(tmp_path):
    path = tmp_path / "results.xlsx"
    append_result(path, "ИТ-41", "Иванов", "Иван", 3, False, WHEN)
    append_result(path, "ИТ-41", "Иванов", "Иван", 9, True, WHEN)  # искусственно другая строка
    assert find_first_ticket(path, "ИТ-41", "Иванов", "Иван") == 3


def test_find_first_ticket_matches_group_and_full_name(tmp_path):
    path = tmp_path / "results.xlsx"
    append_result(path, "ИТ-41", "Иванов", "Иван", 3, False, WHEN)
    assert find_first_ticket(path, "ИТ-42", "Иванов", "Иван") is None
    assert find_first_ticket(path, "ИТ-41", "Иванов", "Пётр") is None
    assert find_first_ticket(path, " ит-41 ", "ИВАНОВ", "иван ") == 3


def test_find_first_ticket_without_file(tmp_path):
    assert find_first_ticket(tmp_path / "results.xlsx", "Г", "Ф", "И") is None


def test_formula_like_values_stored_as_text(tmp_path):
    path = tmp_path / "results.xlsx"
    append_result(path, "=1+1", "=A1", "Иван", 1, False, WHEN)
    row = load_workbook(path).active[2]
    assert [c.data_type for c in row[:3]] == ["s", "s", "s"]


def test_locked_on_replace(tmp_path, monkeypatch):
    path = tmp_path / "results.xlsx"
    append_result(path, "Г", "Ф", "И", 1, False, WHEN)

    def locked(*args):
        raise PermissionError(13, "used by another process")

    monkeypatch.setattr(results.os, "replace", locked)
    with pytest.raises(ResultsLockedError):
        append_result(path, "Г", "Ф2", "И2", 2, False, WHEN)
    monkeypatch.undo()
    assert len(read_rows(path)) == 2
    assert sorted(p.name for p in tmp_path.iterdir()) == ["results.xlsx"]


def test_locked_on_read(tmp_path, monkeypatch):
    path = tmp_path / "results.xlsx"
    append_result(path, "Г", "Ф", "И", 1, False, WHEN)

    def locked(*args, **kwargs):
        raise PermissionError(13, "used by another process")

    monkeypatch.setattr(results, "load_workbook", locked)
    with pytest.raises(ResultsLockedError):
        find_first_ticket(path, "Г", "Ф", "И")


def test_corrupted_results_not_overwritten(tmp_path):
    path = tmp_path / "results.xlsx"
    path.write_bytes(b"garbage")
    with pytest.raises(ResultsFileError):
        append_result(path, "Г", "Ф", "И", 1, False, WHEN)
    assert path.read_bytes() == b"garbage"
