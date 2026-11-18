"""Проверка правил интерфейса на настоящем Tkinter (окна не показываются пользователю надолго)."""

import random

import pytest

tk = pytest.importorskip("tkinter")

from lab2 import results  # noqa: E402
from lab2.controller import Controller  # noqa: E402
from lab2.results import read_rows  # noqa: E402
from lab2.ui import TicketApp  # noqa: E402


class FakeDialogs:
    def __init__(self, retry_answers=()):
        self.calls = []
        self.retry_answers = list(retry_answers)

    def showerror(self, title, message):
        self.calls.append(("error", title, message))

    def showwarning(self, title, message):
        self.calls.append(("warning", title, message))

    def askretrycancel(self, title, message):
        self.calls.append(("retry", title, message))
        return self.retry_answers.pop(0) if self.retry_answers else False


@pytest.fixture(scope="module")
def tk_root():
    # Один Tk на модуль: повторное создание Tk() на Windows иногда не находит init.tcl.
    try:
        window = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"Tk недоступен: {error}")
    window.geometry("+-2000+-2000")  # за пределами экрана
    yield window
    window.destroy()


@pytest.fixture
def root(tk_root):
    yield tk_root
    for child in tk_root.winfo_children():
        child.destroy()
    tk_root.update()


def make_app(root, data_dir, dialogs=None):
    dialogs = dialogs or FakeDialogs()
    app = TicketApp(root, Controller(data_dir, rng=random.Random(0)), dialogs=dialogs)
    root.update()
    return app, dialogs


def select(app, group, student_index=None):
    app.group_var.set(group)
    app.on_group_selected()
    if student_index is not None:
        app.student_box.current(student_index)
        app.on_student_selected()
    app.root.update()


def button_enabled(app):
    return not app.generate_button.instate(["disabled"])


def test_groups_loaded_and_button_disabled_at_start(root, data_dir):
    app, dialogs = make_app(root, data_dir)
    assert list(app.group_box["values"]) == ["ИТ-41", "ИТ-42", "ИТ-43"]
    assert not button_enabled(app)
    assert dialogs.calls == []


def test_group_fills_students_and_button_needs_both(root, data_dir):
    app, _ = make_app(root, data_dir)
    select(app, "ИТ-41")
    assert list(app.student_box["values"]) == ["Иванов Иван", "Петрова Анна"]
    assert not button_enabled(app)
    select(app, "ИТ-41", 1)
    assert button_enabled(app)
    select(app, "ИТ-42")
    assert app.student_var.get() == ""
    assert not button_enabled(app)


def test_empty_group(root, data_dir):
    app, _ = make_app(root, data_dir)
    select(app, "ИТ-43")
    assert list(app.student_box["values"]) in ([], [""])
    assert app.student_box.instate(["disabled"])
    assert not button_enabled(app)


def test_generate_opens_result_and_escape_closes_only_it(root, data_dir):
    app, _ = make_app(root, data_dir)
    select(app, "ИТ-41", 0)
    app.on_generate()
    root.update()

    window = app.result_window.window
    assert window.winfo_exists()
    assert len(read_rows(data_dir / "results.xlsx")) == 2  # сохранено сразу

    window.event_generate("<Escape>")
    root.update()
    assert not window.winfo_exists()
    assert root.winfo_exists()
    assert button_enabled(app)  # можно выдавать билет следующему


def test_missing_files_show_error_without_crash(root, tmp_path):
    app, dialogs = make_app(root, tmp_path)
    assert dialogs.calls and dialogs.calls[0][0] == "error"
    assert app.group_box.instate(["disabled"])
    assert not button_enabled(app)


def test_locked_results_retry_then_success(root, data_dir, monkeypatch):
    app, dialogs = make_app(root, data_dir, FakeDialogs(retry_answers=[True]))
    select(app, "ИТ-41", 0)
    real_replace = results.os.replace
    attempts = {"n": 0}

    def flaky_replace(src, dst):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise PermissionError(13, "used by another process")
        return real_replace(src, dst)

    monkeypatch.setattr(results.os, "replace", flaky_replace)
    app.on_generate()
    root.update()

    assert [c[0] for c in dialogs.calls] == ["retry"]
    assert app.result_window is not None
    assert len(read_rows(data_dir / "results.xlsx")) == 2


def test_locked_results_cancel_issues_no_ticket(root, data_dir, monkeypatch):
    app, dialogs = make_app(root, data_dir, FakeDialogs(retry_answers=[False]))
    select(app, "ИТ-41", 0)

    def locked(src, dst):
        raise PermissionError(13, "used by another process")

    monkeypatch.setattr(results.os, "replace", locked)
    app.on_generate()
    root.update()

    assert [c[0] for c in dialogs.calls] == ["retry", "warning"]
    assert app.result_window is None
    assert not (data_dir / "results.xlsx").exists()
