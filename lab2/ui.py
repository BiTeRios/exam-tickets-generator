"""Tkinter-интерфейс. Вся логика — в Controller, здесь только виджеты и диалоги."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .controller import Assignment, Controller
from .results import ResultsError, ResultsLockedError

PAD = 8


class TicketApp:
    def __init__(self, root: tk.Tk, controller: Controller, dialogs=messagebox):
        self.root = root
        self.controller = controller
        self.dialogs = dialogs  # подменяется в тестах, чтобы окна не блокировали
        self.result_window: ResultWindow | None = None

        root.title("Генератор экзаменационных билетов")
        root.minsize(520, 260)
        frame = ttk.Frame(root, padding=PAD * 2)
        frame.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Группа:").grid(row=0, column=0, sticky="w", pady=PAD, padx=(0, PAD))
        self.group_var = tk.StringVar()
        self.group_box = ttk.Combobox(frame, textvariable=self.group_var, state="readonly")
        self.group_box.grid(row=0, column=1, sticky="ew", pady=PAD)
        self.group_box.bind("<<ComboboxSelected>>", self.on_group_selected)

        ttk.Label(frame, text="Студент:").grid(row=1, column=0, sticky="w", pady=PAD, padx=(0, PAD))
        self.student_var = tk.StringVar()
        self.student_box = ttk.Combobox(frame, textvariable=self.student_var, state="disabled")
        self.student_box.grid(row=1, column=1, sticky="ew", pady=PAD)
        self.student_box.bind("<<ComboboxSelected>>", self.on_student_selected)

        self.generate_button = ttk.Button(frame, text="Сгенерировать билет", command=self.on_generate)
        self.generate_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(PAD * 2, PAD))

        self.status_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.status_var, foreground="#555", wraplength=420).grid(
            row=3, column=0, columnspan=2, sticky="w"
        )
        self.reload_button = ttk.Button(frame, text="Перезагрузить файлы", command=self.reload)
        self.reload_button.grid(row=4, column=0, columnspan=2, sticky="e", pady=(PAD, 0))

        self.reload()

    # --- загрузка и выбор -------------------------------------------------

    def reload(self) -> None:
        errors = self.controller.load()
        names = self.controller.group_names
        self.group_box.configure(values=names, state="readonly" if names else "disabled")
        self.group_var.set("")
        self._set_students([])
        if errors:
            self.status_var.set("Ошибка загрузки: " + " ".join(errors))
            self.dialogs.showerror(
                "Не удалось загрузить данные",
                "\n\n".join(errors)
                + f"\n\nПроверьте файлы в папке:\n{self.controller.data_dir}\n"
                "и нажмите «Перезагрузить файлы».",
            )
        else:
            self.status_var.set(
                f"Групп: {len(names)}, билетов: {len(self.controller.tickets)}. Выберите группу."
            )
        self._update_button()

    def on_group_selected(self, _event=None) -> None:
        students = self.controller.select_group(self.group_var.get())
        self._set_students(students)
        if students:
            self.status_var.set(f"Студентов в группе: {len(students)}. Выберите студента.")
        else:
            self.status_var.set("В выбранной группе нет студентов.")
        self._update_button()

    def on_student_selected(self, _event=None) -> None:
        self.controller.select_student(self.student_box.current())
        if self.controller.can_generate:
            self.status_var.set("Нажмите «Сгенерировать билет».")
        self._update_button()

    def _set_students(self, students) -> None:
        self.student_var.set("")
        self.student_box.configure(
            values=[s.display_name for s in students],
            state="readonly" if students else "disabled",
        )

    def _update_button(self) -> None:
        self.generate_button.state(["!disabled"] if self.controller.can_generate else ["disabled"])

    # --- генерация ----------------------------------------------------------

    def on_generate(self) -> None:
        if not self.controller.can_generate:
            return
        while True:
            try:
                assignment = self.controller.generate()
                break
            except ResultsLockedError as error:
                retry = self.dialogs.askretrycancel(
                    "Файл журнала занят",
                    f"{error}\n\nЗакройте results.xlsx и нажмите «Повторить».",
                )
                if not retry:
                    self.dialogs.showwarning(
                        "Билет не выдан", "Запись в results.xlsx не сохранена, билет не выдан."
                    )
                    return
            except ResultsError as error:
                self.dialogs.showerror("Ошибка журнала", f"{error}\n\nБилет не выдан.")
                return
        self.status_var.set(
            f"{assignment.student.display_name}: билет № {assignment.ticket_number}"
            + (" (повтор)" if assignment.repeat else "")
        )
        self.result_window = ResultWindow(self.root, assignment)


class ResultWindow:
    """Модальное окно результата. ESC закрывает только его."""

    def __init__(self, parent: tk.Tk, assignment: Assignment):
        self.window = tk.Toplevel(parent)
        self.window.title("Ваш билет")
        self.window.transient(parent)
        self.window.resizable(False, False)

        frame = ttk.Frame(self.window, padding=PAD * 3)
        frame.grid()
        ttk.Label(frame, text=f"{assignment.group}, {assignment.student.display_name}").grid(
            sticky="w"
        )
        ttk.Label(
            frame, text=f"Ваш билет № {assignment.ticket_number}", font=("Segoe UI", 18, "bold")
        ).grid(sticky="w", pady=(PAD, PAD * 2))

        if assignment.repeat:
            ttk.Label(
                frame,
                text="Билет уже выдавался этому студенту — показан тот же номер.",
                foreground="#a35200",
            ).grid(sticky="w", pady=(0, PAD))

        if assignment.questions:
            for number, question in enumerate(assignment.questions, start=1):
                ttk.Label(frame, text=f"{number}. {question}", wraplength=520, justify="left").grid(
                    sticky="w", pady=2
                )
        else:
            ttk.Label(
                frame,
                text=f"Вопросы билета № {assignment.ticket_number} не найдены в tickets.docx.",
                foreground="#b00020",
            ).grid(sticky="w")

        ttk.Label(frame, text="ESC — закрыть", foreground="#777").grid(sticky="e", pady=(PAD * 2, 0))

        self.window.bind("<Escape>", self.close)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.grab_set()
        self.window.focus_force()

    def close(self, _event=None) -> None:
        self.window.grab_release()
        self.window.destroy()
