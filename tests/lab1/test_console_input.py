import pytest

from lab1.console_input import (
    SPECIAL_KEY,
    EscapePressed,
    ask_non_empty,
    make_windows_getch,
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
    assert read_line("> ", keys("A", SPECIAL_KEY, "B", SPECIAL_KEY, "C\r"), Screen()) == "ABC"


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


def windows_getch(sequence, pending_after):
    """Имитация msvcrt: pending_after — индексы символов, после которых буфер не пуст."""
    stream = list(sequence)
    position = {"i": 0}

    def getwch():
        ch = stream[position["i"]]
        position["i"] += 1
        return ch

    def kbhit():
        return position["i"] - 1 in pending_after

    return make_windows_getch(getwch, kbhit)


def test_windows_arrow_key_becomes_special_key():
    # стрелка вверх приходит как E0 + 'H', код уже лежит в буфере
    getch = windows_getch("\xe0HA", pending_after={0})
    assert getch() == SPECIAL_KEY
    assert getch() == "A"


def test_windows_function_key_with_zero_prefix():
    getch = windows_getch("\x00;B", pending_after=set())
    assert getch() == SPECIAL_KEY
    assert getch() == "B"


def test_windows_letter_a_grave_is_kept():
    # буква «à» — тот же код E0, но после неё буфер пуст
    getch = windows_getch("\xe0lex\r", pending_after=set())
    assert read_line("> ", getch, Screen()) == "\xe0lex"
