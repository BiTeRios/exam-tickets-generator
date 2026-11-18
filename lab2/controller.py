"""Состояние и правила приложения без Tkinter: всё, что можно проверить тестами."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from pathlib import Path

from . import SourceFileError
from .results import append_result, find_first_ticket
from .students import Student, load_groups
from .tickets import Ticket, parse_tickets

log = logging.getLogger(__name__)

STUDENTS_FILE = "students.xlsx"
TICKETS_FILE = "tickets.docx"
RESULTS_FILE = "results.xlsx"


@dataclass(frozen=True)
class Assignment:
    group: str
    student: Student
    ticket_number: int
    questions: tuple[str, ...] | None  # None — билета с таким номером больше нет в tickets.docx
    repeat: bool


class Controller:
    def __init__(self, data_dir: Path, rng: random.Random | None = None):
        self.data_dir = Path(data_dir)
        self.rng = rng or random.SystemRandom()
        self.groups: dict[str, list[Student]] = {}
        self.tickets: list[Ticket] = []
        self.selected_group: str | None = None
        self.selected_student: Student | None = None

    @property
    def students_path(self) -> Path:
        return self.data_dir / STUDENTS_FILE

    @property
    def tickets_path(self) -> Path:
        return self.data_dir / TICKETS_FILE

    @property
    def results_path(self) -> Path:
        return self.data_dir / RESULTS_FILE

    def load(self) -> list[str]:
        """Читает входные файлы. Возвращает список ошибок (пустой — всё в порядке)."""
        errors: list[str] = []
        self.selected_group = None
        self.selected_student = None
        try:
            self.groups = load_groups(self.students_path)
        except SourceFileError as error:
            self.groups = {}
            errors.append(str(error))
        try:
            self.tickets = parse_tickets(self.tickets_path)
            if not self.tickets:
                errors.append(f"В {TICKETS_FILE} нет ни одного корректного билета (подробности в lab2.log)")
        except SourceFileError as error:
            self.tickets = []
            errors.append(str(error))
        for message in errors:
            log.error(message)
        log.info("Загружено групп: %d, билетов: %d", len(self.groups), len(self.tickets))
        return errors

    @property
    def group_names(self) -> list[str]:
        return list(self.groups)

    def select_group(self, name: str) -> list[Student]:
        self.selected_group = name if name in self.groups else None
        self.selected_student = None
        return list(self.groups.get(name, []))

    def select_student(self, index: int) -> None:
        students = self.groups.get(self.selected_group or "", [])
        self.selected_student = students[index] if 0 <= index < len(students) else None

    @property
    def can_generate(self) -> bool:
        return bool(self.tickets) and self.selected_group is not None and self.selected_student is not None

    def generate(self) -> Assignment:
        """Определяет билет, сохраняет строку в results.xlsx и возвращает результат.

        Может поднять ResultsLockedError / ResultsFileError — тогда ничего не записано.
        """
        if not self.can_generate:
            raise RuntimeError("Не выбраны группа и студент")
        group, student = self.selected_group, self.selected_student

        first_ticket = find_first_ticket(self.results_path, group, student.last_name, student.first_name)
        repeat = first_ticket is not None
        number = first_ticket if repeat else self.rng.choice(self.tickets).number

        append_result(self.results_path, group, student.last_name, student.first_name, number, repeat)
        ticket = next((t for t in self.tickets if t.number == number), None)
        log.info("%s, %s: билет %d (повтор: %s)", group, student.display_name, number, repeat)
        return Assignment(group, student, number, ticket.questions if ticket else None, repeat)
