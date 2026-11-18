import pytest

from lab1.console_input import (
    EscapePressed,
    ask_non_empty,
    read_line,
    wait_enter_or_esc,
)


def keys(*sequence):
    """Превращает строки в поток нажатий для getch."""
    stream = iter("".join(sequence))
    return lambda: next(stream)


class Screen:
    def __init__(self):
        self.text = ""

    def __call__(self, chunk):
        self.text += chunk


def test_reads_line_until_enter():
    assert read_line("Last name: ", keys("Иванов\r"), Screen()) == "Иванов"


def test_backspace_removes_last_char():
    assert read_line("> ", keys("Ivx\bnov\r"), Screen()) == "Ivnov"


def test_backspace_on_empty_line_is_ignored():
    assert read_line("> ", keys("\b\bAb\r"), Screen()) == "Ab"


def test_escape_aborts_input():
    with pytest.raises(EscapePressed):
        read_line("> ", keys("Iva\x1b"), Screen())


def test_escape_as_first_key_aborts_input():
    with pytest.raises(EscapePressed):
        read_line("> ", keys("\x1b"), Screen())


def test_special_keys_are_skipped():
    # \xe0H — стрелка вверх, \x00; — F1
    assert read_line("> ", keys("A\xe0HB\x00;C\r"), Screen()) == "ABC"


def test_ctrl_c_raises_keyboard_interrupt():
    with pytest.raises(KeyboardInterrupt):
        read_line("> ", keys("\x03"), Screen())


def test_ask_non_empty_repeats_on_empty_and_strips():
    screen = Screen()
    value = ask_non_empty("Last name: ", keys("\r", "   \r", "  Petrov  \r"), screen)
    assert value == "Petrov"
    assert screen.text.count("Last name: ") == 3
    assert screen.text.count("не может быть пустым") == 2


def test_wait_enter_or_esc():
    assert wait_enter_or_esc(keys("x\r")) is True
    assert wait_enter_or_esc(keys("x\x1b")) is False
