"""Разбор tickets.docx.

Формат:
    Билет 1
    1. Вопрос первый
    2. Вопрос второй
    3. Вопрос третий

Заголовок — абзац «Билет N» (допускается «Билет №N», регистр не важен).
Вопрос — абзац «N. текст» / «N) текст» или абзац из автоматической нумерации Word.
Некорректные билеты пропускаются с записью в лог, разбор продолжается.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from docx import Document

from . import SourceFileError

log = logging.getLogger(__name__)

QUESTIONS_PER_TICKET = 3
HEADER_RE = re.compile(r"^\s*билет\s*№?\s*(\d+)\s*[.:]?\s*$", re.IGNORECASE)
QUESTION_RE = re.compile(r"^\s*\d+\s*[.)]\s*(\S.*)$")


@dataclass(frozen=True)
class Ticket:
    number: int
    questions: tuple[str, ...]


def parse_tickets(path: str | os.PathLike) -> list[Ticket]:
    path = Path(path)
    if not path.exists():
        raise SourceFileError(f"Не найден файл с билетами: {path}")
    try:
        document = Document(str(path))
    except Exception as error:  # битый файл, не docx, нет доступа
        raise SourceFileError(f"Не удалось прочитать {path.name}: {error}") from error
    return parse_paragraphs(
        (paragraph.text, _is_auto_numbered(paragraph)) for paragraph in document.paragraphs
    )


def parse_paragraphs(paragraphs: Iterable[tuple[str, bool]]) -> list[Ticket]:
    """Разбирает последовательность (текст абзаца, есть ли у абзаца автонумерация)."""
    tickets: list[Ticket] = []
    seen_numbers: set[int] = set()
    number: int | None = None
    questions: list[str] = []
    skipping = False  # идём по билету с нераспознанным заголовком

    def close_ticket() -> None:
        if number is None:
            return
        if len(questions) < QUESTIONS_PER_TICKET:
            log.error(
                "Билет %d: найдено вопросов %d из %d — билет пропущен",
                number, len(questions), QUESTIONS_PER_TICKET,
            )
        elif number in seen_numbers:
            log.error("Билет %d встречается повторно — дубликат пропущен", number)
        else:
            if len(questions) > QUESTIONS_PER_TICKET:
                log.warning(
                    "Билет %d: вопросов %d, используются первые %d",
                    number, len(questions), QUESTIONS_PER_TICKET,
                )
            tickets.append(Ticket(number, tuple(questions[:QUESTIONS_PER_TICKET])))
            seen_numbers.add(number)

    for index, (raw_text, auto_numbered) in enumerate(paragraphs, start=1):
        text = raw_text.strip()
        if not text:
            continue

        header = HEADER_RE.match(text)
        if header:
            close_ticket()
            number, questions, skipping = int(header.group(1)), [], False
            if number < 1:
                log.error("Абзац %d: номер билета должен быть больше 0 — билет пропущен", index)
                number, skipping = None, True
            continue

        question = QUESTION_RE.match(text)
        if question or auto_numbered:
            if number is not None:
                questions.append(question.group(1).strip() if question else text)
            elif not skipping:
                log.error("Абзац %d: вопрос до первого заголовка билета — пропущен: %r", index, text)
            continue

        # Не заголовок и не вопрос: считаем это нераспознанным заголовком.
        # Вопросы под ним не должны приклеиться к предыдущему билету.
        close_ticket()
        log.error("Абзац %d: не распознан заголовок билета %r — билет пропущен", index, text)
        number, questions, skipping = None, [], True

    close_ticket()
    return tickets


def _is_auto_numbered(paragraph) -> bool:
    p_pr = paragraph._p.pPr
    if p_pr is not None and p_pr.numPr is not None:
        return True
    style_name = paragraph.style.name if paragraph.style is not None else ""
    return style_name.startswith("List Number")
