import logging

import pytest

from lab2 import SourceFileError
from lab2.tickets import Ticket, parse_paragraphs, parse_tickets

from .conftest import ticket_lines, write_docx


def plain(lines):
    return [(line, False) for line in lines]


def test_parses_ticket_from_word_file(tmp_path):
    path = tmp_path / "tickets.docx"
    write_docx(path, ["Билет 1", "1. Что такое Git?", "2. Что такое ветка?", "3. Что такое PR?"])

    assert parse_tickets(path) == [
        Ticket(1, ("Что такое Git?", "Что такое ветка?", "Что такое PR?")),
    ]


def test_parses_several_tickets_and_ignores_empty_paragraphs(tmp_path):
    path = tmp_path / "tickets.docx"
    write_docx(path, ticket_lines(1) + ["", "   "] + ticket_lines(2))
    assert [t.number for t in parse_tickets(path)] == [1, 2]


def test_word_auto_numbered_questions(tmp_path):
    path = tmp_path / "tickets.docx"
    write_docx(path, ["Билет 4", ("Первый", "List Number"), ("Второй", "List Number"), ("Третий", "List Number")])
    assert parse_tickets(path) == [Ticket(4, ("Первый", "Второй", "Третий"))]


@pytest.mark.parametrize("header", ["Билет 5", "билет 5", "БИЛЕТ №5", "Билет № 5.", "Билет 5:"])
def test_header_variants(header):
    lines = [header, "1. a", "2. b", "3. c"]
    assert parse_paragraphs(plain(lines))[0].number == 5


def test_question_with_parenthesis_numbering():
    lines = ["Билет 1", "1) a", "2) b", "3) c"]
    assert parse_paragraphs(plain(lines))[0].questions == ("a", "b", "c")


def test_ticket_with_less_than_three_questions_is_skipped_and_logged(caplog):
    lines = ticket_lines(1, count=2) + ticket_lines(2)
    with caplog.at_level(logging.ERROR):
        tickets = parse_paragraphs(plain(lines))
    assert [t.number for t in tickets] == [2]
    assert "Билет 1" in caplog.text and "пропущен" in caplog.text


def test_unrecognised_header_skips_ticket_and_does_not_glue_questions(caplog):
    lines = ticket_lines(1) + ["Билт 2", "1. x", "2. y", "3. z"] + ticket_lines(3)
    with caplog.at_level(logging.ERROR):
        tickets = parse_paragraphs(plain(lines))
    assert [t.number for t in tickets] == [1, 3]
    assert tickets[0].questions == ("Вопрос 1 билета 1", "Вопрос 2 билета 1", "Вопрос 3 билета 1")
    assert "не распознан заголовок" in caplog.text


def test_more_than_three_questions_keeps_first_three(caplog):
    with caplog.at_level(logging.WARNING):
        tickets = parse_paragraphs(plain(ticket_lines(1, count=4)))
    assert len(tickets[0].questions) == 3
    assert "первые 3" in caplog.text


def test_duplicate_ticket_number_is_skipped():
    tickets = parse_paragraphs(plain(ticket_lines(1) + ticket_lines(1)))
    assert len(tickets) == 1


def test_question_before_first_header_is_ignored():
    tickets = parse_paragraphs(plain(["1. сирота"] + ticket_lines(1)))
    assert [t.number for t in tickets] == [1]


def test_ticket_number_zero_is_skipped():
    assert parse_paragraphs(plain(ticket_lines(0) + ticket_lines(1)))[0].number == 1


def test_missing_file_raises_source_error(tmp_path):
    with pytest.raises(SourceFileError):
        parse_tickets(tmp_path / "tickets.docx")


def test_corrupted_file_raises_source_error(tmp_path):
    path = tmp_path / "tickets.docx"
    path.write_bytes(b"not a docx")
    with pytest.raises(SourceFileError):
        parse_tickets(path)
