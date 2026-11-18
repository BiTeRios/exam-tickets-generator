import random

import pytest

from lab2 import results
from lab2.controller import Controller
from lab2.results import ResultsLockedError, read_rows

from .conftest import ticket_lines, write_docx


def ready_controller(data_dir, seed=0):
    controller = Controller(data_dir, rng=random.Random(seed))
    assert controller.load() == []
    return controller


def choose(controller, group, index):
    controller.select_group(group)
    controller.select_student(index)


def test_button_rule_needs_group_and_student(data_dir):
    controller = ready_controller(data_dir)
    assert not controller.can_generate
    controller.select_group("ИТ-41")
    assert not controller.can_generate
    controller.select_student(0)
    assert controller.can_generate
    controller.select_group("ИТ-42")  # смена группы сбрасывает студента
    assert not controller.can_generate


def test_select_group_returns_its_students(data_dir):
    controller = ready_controller(data_dir)
    assert [s.display_name for s in controller.select_group("ИТ-41")] == ["Иванов Иван", "Петрова Анна"]
    assert [s.display_name for s in controller.select_group("ИТ-42")] == ["Морарь Ион"]


def test_empty_group_keeps_button_disabled(data_dir):
    controller = ready_controller(data_dir)
    assert controller.select_group("ИТ-43") == []
    controller.select_student(0)
    assert not controller.can_generate


def test_first_generation_is_random_ticket_from_file(data_dir):
    controller = ready_controller(data_dir)
    choose(controller, "ИТ-41", 0)
    assignment = controller.generate()
    assert assignment.ticket_number in {1, 2, 3}
    assert assignment.repeat is False
    assert len(assignment.questions) == 3
    assert read_rows(controller.results_path)[1][3:] == (
        assignment.ticket_number,
        read_rows(controller.results_path)[1][4],
        "нет",
    )


def test_idempotency_same_student_gets_same_ticket(data_dir):
    numbers = []
    for seed in range(5):  # разные «случайности» не должны влиять на повтор
        controller = ready_controller(data_dir, seed)
        choose(controller, "ИТ-41", 0)
        numbers.append(controller.generate().ticket_number)
    assert len(set(numbers)) == 1

    rows = read_rows(Controller(data_dir).results_path)
    assert len(rows) == 1 + 5  # каждая выдача — новая строка, старые не меняются
    assert [r[5] for r in rows[1:]] == ["нет", "да", "да", "да", "да"]
    assert {r[3] for r in rows[1:]} == {numbers[0]}


def test_repeat_marks_assignment(data_dir):
    controller = ready_controller(data_dir)
    choose(controller, "ИТ-41", 0)
    first = controller.generate()
    second = controller.generate()
    assert second.repeat and second.ticket_number == first.ticket_number


def test_same_name_in_other_group_is_a_different_student(data_dir):
    from .conftest import write_students

    write_students(data_dir / "students.xlsx", {"А": [("Иванов", "Иван")], "Б": [("Иванов", "Иван")]})
    controller = ready_controller(data_dir)
    choose(controller, "А", 0)
    controller.generate()
    choose(controller, "Б", 0)
    assert controller.generate().repeat is False


def test_repeat_of_ticket_removed_from_docx(data_dir):
    controller = ready_controller(data_dir, seed=1)
    choose(controller, "ИТ-41", 0)
    number = controller.generate().ticket_number

    others = [n for n in (1, 2, 3) if n != number]
    write_docx(data_dir / "tickets.docx", sum((ticket_lines(n) for n in others), []))
    controller = ready_controller(data_dir)
    choose(controller, "ИТ-41", 0)
    assignment = controller.generate()
    assert assignment.ticket_number == number
    assert assignment.questions is None


def test_missing_input_files_are_reported(tmp_path):
    errors = Controller(tmp_path).load()
    assert len(errors) == 2
    assert any("students.xlsx" in e for e in errors)
    assert any("tickets.docx" in e for e in errors)


def test_docx_without_valid_tickets_is_reported(data_dir):
    write_docx(data_dir / "tickets.docx", ticket_lines(1, count=2))
    controller = Controller(data_dir)
    assert any("нет ни одного корректного билета" in e for e in controller.load())
    choose(controller, "ИТ-41", 0)
    assert not controller.can_generate


def test_locked_results_writes_nothing(data_dir, monkeypatch):
    controller = ready_controller(data_dir)
    choose(controller, "ИТ-41", 0)
    controller.generate()

    def locked(*args):
        raise PermissionError(13, "used by another process")

    monkeypatch.setattr(results.os, "replace", locked)
    with pytest.raises(ResultsLockedError):
        controller.generate()
    monkeypatch.undo()
    assert len(read_rows(controller.results_path)) == 2
