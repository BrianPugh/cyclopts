from typing import List, Tuple

import pytest

from cyclopts.exceptions import MissingArgumentError


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1 2 80 160 255",
        "--coordinates 1 2 --color 80 160 255",
        "--color 80 160 255 --coordinates 1 2",
        "--color 80 160 255 --coordinates=1 2",
    ],
)
def test_bind_tuple_basic(app, cmd_str, assert_parse_args):
    @app.default
    def foo(coordinates: Tuple[int, int], color: Tuple[int, int, int]):
        pass

    assert_parse_args(foo, cmd_str, (1, 2), (80, 160, 255))


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1 2 alice 100 200",
        "--coordinates 1 2 --data alice 100 200",
        "--data alice 100 200 --coordinates 1 2",
    ],
)
def test_bind_tuple_nested(app, cmd_str, assert_parse_args):
    @app.default
    def foo(coordinates: Tuple[int, int], data: Tuple[Tuple[str, int], int]):
        pass

    assert_parse_args(foo, cmd_str, (1, 2), (("alice", 100), 200))


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1 2 alice 100 bob 200",
        "--coordinates 1 2 --data alice 100 --data bob 200",
        "--data alice 100 --coordinates 1 2 --data bob 200",
    ],
)
def test_bind_tuple_ellipsis(app, cmd_str, assert_parse_args):
    @app.default
    def foo(coordinates: Tuple[int, int], data: Tuple[Tuple[str, int], ...]):
        pass

    assert_parse_args(foo, cmd_str, (1, 2), (("alice", 100), ("bob", 200)))


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1 2 3",
        "--values 1 --values 2 --values 3",
    ],
)
def test_bind_tuple_no_inner_types(app, cmd_str, assert_parse_args):
    @app.default
    def foo(values: Tuple):
        pass

    # Interpreted as a string because:
    #     1. Tuple -> Tuple[Any, ...]
    #     2. Any is treated the same as no annotation.
    #     3. Even if a default value was supplied, we couldn't unambiguously infer a type.
    #     4. This falls back to string.
    assert_parse_args(foo, cmd_str, ("1", "2", "3"))


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
        app.parse_args(cmd_str, print_error=False, exit_on_error=False)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "--coordinates 1 2 --color 80 160 255 --coordinates 3 4",
        "--coordinates 1 2 --coordinates 3 4 --color 80 160 255",
        "1 2 3 4 --color 80 160 255",
    ],
)
def test_bind_list_of_tuple(app, cmd_str, assert_parse_args):
    @app.default
    def foo(coordinates: List[Tuple[int, int]], color: Tuple[int, int, int]):
        pass

    assert_parse_args(foo, cmd_str, [(1, 2), (3, 4)], (80, 160, 255))
