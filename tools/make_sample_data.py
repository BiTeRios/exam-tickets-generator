"""Создаёт демонстрационные students.xlsx и tickets.docx в lab2/data.

Запуск: python tools/make_sample_data.py [ПАПКА]
"""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from openpyxl import Workbook

GROUPS = {
    "ИТ-41": [
        ("Иванов", "Иван"),
        ("Петрова", "Анна"),
        ("Сидоренко", "Максим"),
        ("Русу", "Елена"),
        ("Чебан", "Дмитрий"),
    ],
    "ИТ-42": [
        ("Морарь", "Ион"),
        ("Козлова", "Мария"),
        ("Лунгу", "Виктор"),
        ("Попеску", "Кристина"),
    ],
    "ИТ-43": [],  # пустая группа — для проверки требования из ТЗ
}

TICKETS = [
    ("Жизненный цикл программного обеспечения: основные модели.",
     "Функциональные и нефункциональные требования, примеры.",
     "Назначение системы контроля версий Git, основные команды."),
    ("Каскадная модель разработки: достоинства и недостатки.",
     "Диаграмма вариантов использования UML: элементы и связи.",
     "Ветвление в Git: создание ветки, слияние, Pull Request."),
    ("Гибкие методологии: принципы Agile Manifesto.",
     "Техническое задание: структура и требования к содержанию.",
     "Модульное тестирование: цели и пример unit-теста."),
    ("Scrum: роли, артефакты и события.",
     "Диаграмма классов UML: ассоциация, агрегация, композиция.",
     "Принципы SOLID: формулировки и примеры нарушений."),
    ("Kanban: визуализация потока и ограничение WIP.",
     "Диаграмма последовательности UML: назначение и элементы.",
     "Рефакторинг: признаки кода, требующего рефакторинга."),
    ("Спиральная модель жизненного цикла и управление рисками.",
     "Архитектурный шаблон MVC: компоненты и их взаимодействие.",
     "Непрерывная интеграция (CI): назначение и типовой конвейер."),
    ("Оценка трудоёмкости: метод покерного планирования.",
     "Шаблоны проектирования: порождающие, структурные, поведенческие.",
     "Код-ревью: цели, практики, типичные замечания."),
    ("Управление требованиями: трассируемость и изменение требований.",
     "Клиент-серверная архитектура и REST API.",
     "Виды тестирования: модульное, интеграционное, системное, приёмочное."),
    ("Генеративный ИИ в разработке ПО: возможности и риски.",
     "Проектирование базы данных: нормальные формы.",
     "Обработка ошибок и исключений: подходы и лучшие практики."),
    ("Prompt engineering: как формулировать задачи для ИИ-ассистента.",
     "Диаграмма деятельности UML: назначение и элементы.",
     "Документирование кода и README: что должно быть описано."),
]


def make_students(path: Path) -> None:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for group, students in GROUPS.items():
        sheet = workbook.create_sheet(group)
        sheet.append(["Фамилия", "Имя"])
        for student in students:
            sheet.append(list(student))
        sheet.column_dimensions["A"].width = 18
        sheet.column_dimensions["B"].width = 14
    workbook.save(path)


def make_tickets(path: Path) -> None:
    document = Document()
    for number, questions in enumerate(TICKETS, start=1):
        document.add_paragraph(f"Билет {number}")
        for index, question in enumerate(questions, start=1):
            document.add_paragraph(f"{index}. {question}")
        document.add_paragraph("")
    document.save(path)


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "lab2" / "data"
    target.mkdir(parents=True, exist_ok=True)
    make_students(target / "students.xlsx")
    make_tickets(target / "tickets.docx")
    print(f"Созданы {target / 'students.xlsx'} и {target / 'tickets.docx'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
