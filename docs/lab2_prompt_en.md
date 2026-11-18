# Lab 2 — engineered prompt for the coding agent

> Step 1 of the lab ("Prompt Engineering"): the Russian assignment was turned into a
> precise English specification before any code was generated. English keeps the
> prompt short in tokens and unambiguous for the model. The prompt below was
> written with Claude (instead of ChatGPT/Gemini) and then given to the coding agent.

---

You are extending an existing Python 3.10+ repository (`exam-tickets-generator`).
Lab 1 lives in package `lab1/` (console app, `openpyxl`, `pytest`). Do not modify `lab1/`.
Create a new package `lab2/` with a **Tkinter (ttk) desktop app**. Allowed extra
dependency: `python-docx`. No other third-party packages.

## Files

Default data folder: `lab2/data/` (overridable with `--data-dir`). Run: `python -m lab2`.

| File | Direction | Format |
|---|---|---|
| `students.xlsx` | input | One sheet per group, sheet name = group name. Row 1 = header. From row 2: column A = last name, column B = first name. Skip rows where both are empty. Trim spaces. |
| `tickets.docx` | input | Paragraph `Билет N` starts a ticket (also accept `Билет №N`, case-insensitive, optional trailing `.`/`:`). Following paragraphs `N. text` (or `N) text`, or Word auto-numbered list paragraphs) are questions. Empty paragraphs are ignored. |
| `results.xlsx` | output | Columns: `Группа | Фамилия | Имя | Номер билета | Дата и время | Повтор (да/нет)`. Created with this header if missing. Append-only. |

## Ticket parsing rules

- A non-empty paragraph that is neither a valid header nor a question is an
  **unrecognised header**: log an error, and skip every question until the next valid
  header (never attach them to the previous ticket).
- A ticket with fewer than 3 questions is skipped and logged. If it has more than 3,
  keep the first 3 and log a warning.
- A duplicate ticket number is skipped and logged (first one wins).
- Parsing never raises because of bad content; it returns the valid tickets.
- Log to `lab2.log` in the data folder via the standard `logging` module.

## UI behaviour

1. On start, combobox #1 is filled with sheet names of `students.xlsx` (groups).
2. Selecting a group fills combobox #2 with that group's students as `Фамилия Имя`.
   A group without students → empty combobox #2, button stays disabled, no exception.
3. Button `Сгенерировать билет` is enabled **only** when both a group and a student are
   selected. Changing the group clears the student and disables the button.
4. Clicking the button: decide the ticket, **save the row to `results.xlsx` first**,
   then open a modal result window: `Ваш билет № N` and the three questions.
5. `Esc` closes the result window only; the main window stays open for the next student.
   `Esc` in the main window does nothing.

## Ticket assignment (idempotent)

- Key = (group, last name, first name), compared after trimming, case-insensitive.
- If the key already exists in `results.xlsx`: reuse the ticket number from the
  **first** (topmost) row for this key, append a new row with `Повтор = да`.
- Otherwise: choose a random ticket from the parsed valid tickets, append a row with
  `Повтор = нет`.
- If a reused ticket number is no longer present in `tickets.docx`, still show the
  number and say that its questions were not found.

## Robustness

- Missing or unreadable `students.xlsx` / `tickets.docx` at start: show a clear message,
  keep the window open, disable the controls, offer a `Перезагрузить файлы` button.
- `results.xlsx` locked by Excel (PermissionError on read or write): show
  "file is open, close it and press Retry" with Retry/Cancel; Retry tries again,
  Cancel shows that the ticket was **not** issued. Never crash.
- Save each row immediately: write to a temp file in the same folder, `fsync`,
  then `os.replace` over `results.xlsx`. Existing rows are never changed.

## Architecture

- `lab2/students.py`, `lab2/tickets.py`, `lab2/results.py` — file I/O, no Tkinter.
- `lab2/controller.py` — UI-independent state: groups, selected group/student,
  `can_generate`, `generate()` returning the assignment. All UI rules are testable here.
- `lab2/ui.py` — thin Tkinter layer calling the controller.

## Unit tests (`tests/lab2/`, pytest)

At minimum: parsing a ticket from a generated `.docx` (valid, fewer than 3 questions,
unrecognised header, duplicates, auto-numbered list), students by group (including an
empty group), idempotency (same student twice → same ticket, second row `да`, rows
appended not modified), locked results file, missing input files, button enable rules,
and `Esc` closing only the result window.
