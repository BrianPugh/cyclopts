import inspect
from typing import Tuple

import pytest


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1 2 80 160 255",
        "--coordinates 1 2 --color 80 160 255",
        "--color 80 160 255 --coordinates 1 2",
    ],
)
def test_(app, cmd_str):
    @app.default
    def foo(coordinates: Tuple[int, int], color: Tuple[int, int, int]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind((1, 2), (80, 160, 255))

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind
