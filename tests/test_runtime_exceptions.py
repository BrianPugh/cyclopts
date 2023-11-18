from typing import Tuple

import pytest


@pytest.mark.skip
def test_runtime_exception_not_enough_tokens(app, console):
    @app.default
    def foo(a, b, c):
        pass

    with console.capture() as capture:
        app(["1", "2"])

    actual = capture.get()
    assert actual == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        "│ TODO                                                               │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )
