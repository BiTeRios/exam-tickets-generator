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


def test_soft_line_break_inside_question_keeps_ticket():
    lines = ["Билет 1", "1. Первая строка\nпродолжение", "2. b", "3. c"]
    assert parse_paragraphs(plain(lines))[0].questions[0] == "Первая строка продолжение"


def test_question_text_starting_with_decimal_number_is_not_cut():
    lines = ["Билет 1", "1. a", "2. b", "3. Почему 2.5 секунды?"]
    assert parse_paragraphs(plain(lines))[0].questions[2] == "Почему 2.5 секунды?"
    auto = [("Билет 2", False), ("1.5 ГГц — это много?", True), ("x", True), ("y", True)]
    assert parse_paragraphs(auto)[0].questions[0] == "1.5 ГГц — это много?"


def test_tickets_inside_word_table(tmp_path):
    from docx import Document

    document = Document()
    document.add_paragraph("Билет 1")
    for i in range(1, 4):
        document.add_paragraph(f"{i}. q{i}")
    table = document.add_table(rows=4, cols=1)
    for row, text in zip(table.rows, ["Билет 2", "1. x", "2. y", "3. z"]):
        row.cells[0].text = text
    path = tmp_path / "tickets.docx"
    document.save(path)

    assert [(t.number, t.questions) for t in parse_tickets(path)] == [
        (1, ("q1", "q2", "q3")),
        (2, ("x", "y", "z")),
    ]


def test_removed_numbering_numid_zero_is_not_a_question(tmp_path):
    from docx import Document
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    document = Document()
    document.add_paragraph("Билет 1")
    for i in range(1, 4):
        document.add_paragraph(f"{i}. q{i}")
    plain_paragraph = document.add_paragraph("просто текст")
    num_pr = OxmlElement("w:numPr")
    num_id = OxmlElement("w:numId")
    num_id.set(qn("w:val"), "0")
    num_pr.append(num_id)
    plain_paragraph._p.get_or_add_pPr().append(num_pr)
    path = tmp_path / "tickets.docx"
    document.save(path)

    # «просто текст» — не вопрос, а нераспознанный заголовок; билет 1 цел
    assert [t.number for t in parse_tickets(path)] == [1]
