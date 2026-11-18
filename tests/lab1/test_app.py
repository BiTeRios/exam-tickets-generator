import random

import pytest

from lab1 import app
from lab1.app import TICKET_MAX, TICKET_MIN, generate_ticket, run
from lab1.journal import JournalLockedError, read_rows


def keys(*sequence):
    stream = iter("".join(sequence))
    return lambda: next(stream)


class Screen:
    def __init__(self):
        self.text = ""

    def __call__(self, chunk):
        self.text += chunk


def student(last, first):
    return f"{last}\r{first}\r"


def test_ticket_is_always_in_range():
    rng = random.Random(0)
    tickets = {generate_ticket(rng) for _ in range(2000)}
    assert tickets == set(range(TICKET_MIN, TICKET_MAX + 1))


def test_three_students_then_escape(tmp_path):
    path = tmp_path / "journal.xlsx"
    screen = Screen()
    run(path, keys(student("A", "a"), student("B", "b"), student("C", "c"), "\x1b"), screen, random.Random(1))

    rows = read_rows(path)
    assert len(rows) == 4
    assert [r[:2] for r in rows[1:]] == [("A", "a"), ("B", "b"), ("C", "c")]
    assert screen.text.startswith("Для выхода нажмите ESC.")
    assert screen.text.count("Билет № ") == 3


def test_second_run_appends_after_previous(tmp_path):
    path = tmp_path / "journal.xlsx"
    run(path, keys(student("A", "a"), student("B", "b"), student("C", "c"), "\x1b"), Screen(), random.Random(1))
    first_run = read_rows(path)

    run(path, keys(student("D", "d"), student("E", "e"), "\x1b"), Screen(), random.Random(2))
    rows = read_rows(path)
    assert len(rows) == 6
    assert rows[:4] == first_run


def test_printed_ticket_matches_journal(tmp_path):
    path = tmp_path / "journal.xlsx"
    screen = Screen()
    run(path, keys(student("A", "a"), "\x1b"), screen, random.Random(5))
    ticket = read_rows(path)[1][2]
    assert f"Билет № {ticket}\n" in screen.text


def test_record_is_saved_before_next_student(tmp_path):
    """Имитация аварии: после первого студента ввод «обрывается»."""
    path = tmp_path / "journal.xlsx"
    stream = iter(student("A", "a") + "Bo")

    def crashing_getch():
        try:
            return next(stream)
        except StopIteration:
            raise RuntimeError("процесс убит")

    with pytest.raises(RuntimeError):
        run(path, crashing_getch, Screen(), random.Random(1))
    assert len(read_rows(path)) == 2


def test_escape_on_first_name_exits(tmp_path):
    path = tmp_path / "journal.xlsx"
    run(path, keys("Ivanov\r\x1b"), Screen(), random.Random(1))
    assert not path.exists()


def test_locked_journal_asks_to_close_and_retries(tmp_path, monkeypatch):
    path = tmp_path / "journal.xlsx"
    real_append = app.append_record
    calls = {"n": 0}

    def flaky_append(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise JournalLockedError(path)
        return real_append(*args, **kwargs)

    monkeypatch.setattr(app, "append_record", flaky_append)
    screen = Screen()
    # студент, затем Enter = «повторить», затем ESC = выход
    run(path, keys(student("A", "a"), "\r", "\x1b"), screen, random.Random(1))

    assert "Закройте файл" in screen.text
    assert len(read_rows(path)) == 2


def test_locked_journal_can_be_skipped_with_escape(tmp_path, monkeypatch):
    path = tmp_path / "journal.xlsx"

    def always_locked(*args, **kwargs):
        raise JournalLockedError(path)

    monkeypatch.setattr(app, "append_record", always_locked)
    screen = Screen()
    run(path, keys(student("A", "a"), "\x1b", "\x1b"), screen, random.Random(1))

    assert "Запись НЕ сохранена" in screen.text
    assert "Работа завершена." in screen.text


def test_corrupted_journal_is_reported_and_app_keeps_running(tmp_path):
    path = tmp_path / "journal.xlsx"
    path.write_bytes(b"garbage")
    screen = Screen()
    # студент, ESC = не сохранять, затем ещё ESC = выход
    run(path, keys(student("A", "a"), "\x1b", "\x1b"), screen, random.Random(1))

    assert "повреждён" in screen.text
    assert "Запись НЕ сохранена" in screen.text
    assert path.read_bytes() == b"garbage"
