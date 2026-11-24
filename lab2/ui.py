"""Tkinter-интерфейс. Вся логика — в Controller, здесь только виджеты и диалоги."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .controller import Assignment, Controller
from .results import ResultsError, ResultsLockedError

PAD = 8
BACKGROUND = "#edf4fd"
SURFACE = "#ffffff"
TEXT = "#172b46"
MUTED = "#49617d"
BORDER = "#c5d7ed"
ACCENT = "#235fa9"
ACCENT_HOVER = "#1a4e92"
ACCENT_PRESSED = "#163e76"
ACCENT_TINT = "#dfeaf9"
BODY_FONT = ("Segoe UI", 11)
TITLE_FONT = ("Segoe UI", 21, "bold")


def _configure_styles(root: tk.Tk) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Lab2.TFrame", background=BACKGROUND)
    style.configure(
        "Card.Lab2.TFrame", background=SURFACE, bordercolor=BORDER,
        lightcolor=BORDER, darkcolor=BORDER, borderwidth=1, relief="solid",
    )
    style.configure("Lab2.TLabel", background=BACKGROUND, foreground=TEXT, font=BODY_FONT)
    style.configure("Title.Lab2.TLabel", font=TITLE_FONT)
    style.configure("Detail.Lab2.TLabel", foreground=MUTED)
    style.configure("Ticket.Lab2.TLabel", foreground=ACCENT, font=TITLE_FONT)
    style.configure("Card.Lab2.TLabel", background=SURFACE)
    style.configure("Field.Card.Lab2.TLabel", font=("Segoe UI", 10, "bold"))
    style.configure("Number.Card.Lab2.TLabel", foreground=ACCENT, font=("Segoe UI", 11, "bold"))

    style.configure(
        "Lab2.TCombobox", padding=(9, 6), background=ACCENT_TINT,
        foreground=TEXT, fieldbackground=SURFACE, arrowcolor=ACCENT,
        bordercolor=BORDER, lightcolor=SURFACE, darkcolor=SURFACE,
    )
    style.map(
        "Lab2.TCombobox", fieldbackground=[("disabled", BACKGROUND), ("readonly", SURFACE)],
        foreground=[("disabled", MUTED)], bordercolor=[("focus", ACCENT)],
        selectbackground=[("readonly", ACCENT_TINT)], selectforeground=[("readonly", TEXT)],
    )
    style.configure(
        "Lab2.TButton", font=BODY_FONT, padding=(12, 7), focuscolor=ACCENT,
        bordercolor=BORDER, lightcolor=SURFACE, darkcolor=SURFACE,
        background=SURFACE, foreground=TEXT,
    )
    style.map("Lab2.TButton", background=[("pressed", BORDER), ("active", ACCENT_TINT)])
    style.configure(
        "Primary.Lab2.TButton", font=("Segoe UI", 11, "bold"),
        padding=(12, 9), focuscolor=SURFACE,
    )
    style.map(
        "Primary.Lab2.TButton",
        background=[("disabled", ACCENT_TINT), ("pressed", ACCENT_PRESSED),
                    ("active", ACCENT_HOVER), ("!disabled", ACCENT)],
        foreground=[("disabled", MUTED), ("!disabled", SURFACE)],
        bordercolor=[("disabled", BORDER), ("!disabled", ACCENT)],
        lightcolor=[("disabled", ACCENT_TINT), ("!disabled", ACCENT)],
        darkcolor=[("disabled", ACCENT_TINT), ("!disabled", ACCENT)],
    )


class TicketApp:
    def __init__(self, root: tk.Tk, controller: Controller, dialogs=messagebox):
        self.root = root
        self.controller = controller
        self.dialogs = dialogs  # подменяется в тестах, чтобы окна не блокировали
        self.result_window: ResultWindow | None = None

        _configure_styles(root)
        root.title("Генератор экзаменационных билетов")
        root.minsize(520, 350)
        frame = ttk.Frame(root, padding=PAD * 3, style="Lab2.TFrame")
        frame.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Генератор билетов", style="Title.Lab2.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, PAD * 2)
        )
        form = ttk.Frame(frame, padding=PAD * 2, style="Card.Lab2.TFrame")
        form.grid(row=1, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)

        ttk.Label(form, text="Группа", style="Field.Card.Lab2.TLabel").grid(row=0, column=0, sticky="w")
        self.group_var = tk.StringVar()
        self.group_box = ttk.Combobox(
            form, textvariable=self.group_var, state="readonly", style="Lab2.TCombobox", font=BODY_FONT
        )
        self.group_box.grid(row=1, column=0, sticky="ew", pady=(PAD // 2, PAD + 4))
        self.group_box.bind("<<ComboboxSelected>>", self.on_group_selected)

        ttk.Label(form, text="Студент", style="Field.Card.Lab2.TLabel").grid(row=2, column=0, sticky="w")
        self.student_var = tk.StringVar()
        self.student_box = ttk.Combobox(
            form, textvariable=self.student_var, state="disabled", style="Lab2.TCombobox", font=BODY_FONT
        )
        self.student_box.grid(row=3, column=0, sticky="ew", pady=(PAD // 2, PAD * 2))
        self.student_box.bind("<<ComboboxSelected>>", self.on_student_selected)

        self.generate_button = ttk.Button(
            form, text="Сгенерировать билет", command=self.on_generate, style="Primary.Lab2.TButton"
        )
        self.generate_button.grid(row=4, column=0, sticky="ew")

        footer = ttk.Frame(frame, style="Lab2.TFrame")
        footer.grid(row=2, column=0, sticky="ew", pady=(PAD * 2, 0))
        footer.columnconfigure(0, weight=1)
        self.status_var = tk.StringVar()
        ttk.Label(
            footer, textvariable=self.status_var, style="Detail.Lab2.TLabel",
            wraplength=250, justify="left",
        ).grid(row=0, column=0, sticky="w", padx=(0, PAD))
        self.reload_button = ttk.Button(
            footer, text="Перезагрузить файлы", command=self.reload, style="Lab2.TButton"
        )
        self.reload_button.grid(row=0, column=1, sticky="e")

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

        frame = ttk.Frame(self.window, padding=PAD * 3, style="Lab2.TFrame")
        frame.grid()
        ttk.Label(
            frame, text=f"Ваш билет № {assignment.ticket_number}", style="Ticket.Lab2.TLabel"
        ).grid(sticky="w")
        ttk.Label(
            frame, text=f"{assignment.group}, {assignment.student.display_name}",
            style="Detail.Lab2.TLabel", wraplength=480, justify="left",
        ).grid(sticky="w", pady=(PAD // 2, PAD * 2))

        if assignment.repeat:
            ttk.Label(
                frame, text="Повторная выдача. Номер билета сохранён.", style="Detail.Lab2.TLabel",
                wraplength=480, justify="left",
            ).grid(sticky="w", pady=(0, PAD))

        questions = ttk.Frame(frame, padding=(PAD * 2, PAD), style="Card.Lab2.TFrame")
        questions.grid(sticky="ew")
        if assignment.questions:
            for row, question in enumerate(assignment.questions):
                ttk.Label(questions, text=f"{row + 1}.", style="Number.Card.Lab2.TLabel").grid(
                    row=row, column=0, sticky="nw", padx=(0, PAD + 4), pady=PAD,
                )
                ttk.Label(
                    questions, text=question, style="Card.Lab2.TLabel", wraplength=440, justify="left",
                ).grid(row=row, column=1, sticky="w", pady=PAD)
        else:
            ttk.Label(
                questions, text=f"Вопросы билета № {assignment.ticket_number} не найдены в tickets.docx.",
                style="Card.Lab2.TLabel", wraplength=440, justify="left",
            ).grid(sticky="w", pady=PAD)

        ttk.Button(frame, text="Закрыть (Esc)", command=self.close, style="Lab2.TButton").grid(
            sticky="e", pady=(PAD * 2, 0)
        )

        self.window.bind("<Escape>", self.close)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.grab_set()
        self.window.focus_force()

    def close(self, _event=None) -> None:
        self.window.grab_release()
        self.window.destroy()
