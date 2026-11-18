from datetime import datetime

import pytest

from lab1 import journal
from lab1.journal import (
    HEADER,
    JournalCorruptedError,
    JournalLockedError,
    JournalWriteError,
    append_record,
    read_rows,
)

WHEN = datetime(2026, 11, 18, 10, 30, 0)


def test_creates_file_with_header(tmp_path):
    path = tmp_path / "journal.xlsx"
    append_record(path, "Ivanov", "Ivan", 7, WHEN)

    rows = read_rows(path)
    assert rows[0] == tuple(HEADER)
    assert rows[1] == ("Ivanov", "Ivan", 7, WHEN)


def test_appends_without_touching_existing_rows(tmp_path):
    path = tmp_path / "journal.xlsx"
    for i, name in enumerate(["A", "B", "C"], start=1):
        append_record(path, name, "X", i, WHEN)
    before = read_rows(path)

    append_record(path, "D", "Y", 4, WHEN)
    append_record(path, "E", "Z", 5, WHEN)

    after = read_rows(path)
    assert len(after) == 6  # шапка + 5 строк
    assert after[:4] == before
    assert [row[0] for row in after[1:]] == ["A", "B", "C", "D", "E"]


def test_locked_file_on_replace_raises_and_keeps_journal(tmp_path, monkeypatch):
    path = tmp_path / "journal.xlsx"
    append_record(path, "Ivanov", "Ivan", 7, WHEN)

    def locked_replace(src, dst):
        raise PermissionError(13, "file is used by another process")

    monkeypatch.setattr(journal.os, "replace", locked_replace)
    with pytest.raises(JournalLockedError):
        append_record(path, "Petrov", "Petr", 3, WHEN)

    monkeypatch.undo()
    assert len(read_rows(path)) == 2
    # временный файл за собой не оставляем
    assert [p.name for p in tmp_path.iterdir()] == ["journal.xlsx"]


def test_locked_file_on_read_raises(tmp_path, monkeypatch):
    path = tmp_path / "journal.xlsx"
    append_record(path, "Ivanov", "Ivan", 7, WHEN)

    def locked_load(*args, **kwargs):
        raise PermissionError(13, "file is used by another process")

    monkeypatch.setattr(journal, "load_workbook", locked_load)
    with pytest.raises(JournalLockedError):
        append_record(path, "Petrov", "Petr", 3, WHEN)


@pytest.mark.parametrize("content", [b"", b"this is not an xlsx file"])
def test_corrupted_journal_raises_and_is_not_overwritten(tmp_path, content):
    path = tmp_path / "journal.xlsx"
    path.write_bytes(content)
    with pytest.raises(JournalCorruptedError):
        append_record(path, "Ivanov", "Ivan", 7, WHEN)
    assert path.read_bytes() == content


def test_formula_like_names_are_stored_as_text(tmp_path):
    from openpyxl import load_workbook

    path = tmp_path / "journal.xlsx"
    append_record(path, "=1+1", '=HYPERLINK("http://x")', 7, WHEN)
    cells = load_workbook(path).active[2]
    assert (cells[0].value, cells[0].data_type) == ("=1+1", "s")
    assert cells[1].data_type == "s"


def test_write_error_in_folder_is_reported(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError(13, "access denied")

    monkeypatch.setattr(journal.tempfile, "mkstemp", denied)
    with pytest.raises(JournalWriteError):
        append_record(tmp_path / "journal.xlsx", "Ivanov", "Ivan", 7, WHEN)


def test_rows_go_to_journal_sheet_even_if_other_sheet_is_active(tmp_path):
    from openpyxl import load_workbook

    path = tmp_path / "journal.xlsx"
    append_record(path, "A", "a", 1, WHEN)
    workbook = load_workbook(path)
    workbook.create_sheet("Notes")
    workbook.active = 1
    workbook.save(path)

    append_record(path, "B", "b", 2, WHEN)
    rows = read_rows(path)
    assert [r[0] for r in rows] == ["Last name", "A", "B"]
