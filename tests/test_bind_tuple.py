import inspect
from typing import List, Tuple

import pytest

from cyclopts.exceptions import MissingArgumentError


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1 2 80 160 255",
        "--coordinates 1 2 --color 80 160 255",
        "--color 80 160 255 --coordinates 1 2",
    ],
)
def test_bind_tuple_basic(app, cmd_str):
    @app.default
    def foo(coordinates: Tuple[int, int], color: Tuple[int, int, int]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind((1, 2), (80, 160, 255))

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1",
        "--coordinates 1",
    ],
)
def test_bind_tuple_insufficient_tokens(app, cmd_str):
    @app.default
    def foo(coordinates: Tuple[int, int]):
        pass

    with pytest.raises(MissingArgumentError):
        app.parse_args(cmd_str)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1 2 --coordinates 3 4 --color 80 160 255",
        "--coordinates 1 2 --color 80 160 255 --coordinates 3 4",
        "--coordinates 1 2 --coordinates 3 4 --color 80 160 255",
        "1 2 3 4 --color 80 160 255",
    ],
)
def test_bind_list_of_tuple(app, cmd_str):
    @app.default
    def foo(coordinates: List[Tuple[int, int]], color: Tuple[int, int, int]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind([(1, 2), (3, 4)], (80, 160, 255))

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind
