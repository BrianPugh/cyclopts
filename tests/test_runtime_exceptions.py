from typing import Tuple

import pytest

from cyclopts import CycloptsError


def test_runtime_exception_not_enough_tokens(app, console):
    @app.default
    def foo(a: Tuple[int, int, int]):
        pass

    with console.capture() as capture, pytest.raises(CycloptsError):
        app(["1", "2"], exit_on_error=False, console=console)

    actual = capture.get()
    assert actual == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        '│ Parameter "--a" requires 3 arguments. Only got 2.                  │\n'
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_runtime_exception_missing_parameter(app, console):
    @app.default
    def foo(a, b, c):
        pass

    with console.capture() as capture, pytest.raises(CycloptsError):
        app(["1", "2"], exit_on_error=False, console=console)

    actual = capture.get()
    assert actual == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        '│ Parameter "--c" requires an argument.                              │\n'
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )
