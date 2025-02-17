from dataclasses import dataclass
from typing import Annotated, Iterable, Optional, Sequence

import pytest

from cyclopts import Parameter

LIST_STR_LIKE_TYPES = [list, list[str], Sequence, Sequence[str], Iterable, Iterable[str]]


@dataclass
class User:
    name: str
    age: int


@pytest.mark.parametrize(
    "cmd_str",
    [
        "--values=[1,2,3]",
        "--values [1,2,3]",
        "--values [1,2] --values [3]",
        "--values [1] --values '[2, 3]'",
        "--values 1 --values [2,3]",
        "--values [1] --values [2] --values [3]",
    ],
)
@pytest.mark.parametrize("json_list", [None, True])
def test_json_list_cli_str(app, assert_parse_args, cmd_str, json_list):
    @app.default
    def main(values: Annotated[list[int], Parameter(json_list=json_list)]):
        pass

    assert_parse_args(main, cmd_str, [1, 2, 3])


@pytest.mark.parametrize("annotation", LIST_STR_LIKE_TYPES)
def test_json_list_str_none(app, assert_parse_args, annotation):
    """A ``list`` or ``list[str]`` annotation should **not** be set-able via json-string by default.

    May change in v4.
    """

    @app.default
    def main(values: annotation):  # pyright: ignore
        pass

    assert_parse_args(main, ['["foo", "bar"]'], ['["foo", "bar"]'])


def test_json_list_optional_int(app, assert_parse_args):
    @app.default
    def main(values: list[Optional[int]]):  # pyright: ignore
        pass

    assert_parse_args(main, ["[1, null, 2]"], [1, None, 2])


@pytest.mark.parametrize("annotation", LIST_STR_LIKE_TYPES)
def test_json_list_str_cli_str_true(app, assert_parse_args, annotation):
    @app.default
    def main(values: Annotated[annotation, Parameter(json_list=True)]):  # pyright: ignore
        pass

    assert_parse_args(main, ['["foo", "bar"]'], ["foo", "bar"])


@pytest.mark.parametrize("annotation", [list, list[str]])
def test_json_list_str_cli_str_false(app, assert_parse_args, annotation):
    @app.default
    def main(values: Annotated[annotation, Parameter(json_list=False)]):  # pyright: ignore
        pass

    assert_parse_args(main, ['["foo", "bar"]'], ['["foo", "bar"]'])


@pytest.mark.parametrize(
    "env_str",
    [
        "[1,2,3]",
        "[1, 2, 3]",
    ],
)
@pytest.mark.parametrize("json_list", [None, True])
def test_json_list_env_str(app, assert_parse_args, env_str, monkeypatch, json_list):
    monkeypatch.setenv("VALUES", env_str)

    @app.default
    def main(values: Annotated[list[int], Parameter(env_var="VALUES", json_list=json_list)]):
        pass

    assert_parse_args(main, "", [1, 2, 3])


@pytest.mark.skip(reason="Need to implement token exploding.")
def test_json_list_of_dataclass_cli(app, assert_parse_args):
    @app.default
    def main(values: list[User]):
        pass

    assert_parse_args(
        main,
        ["--values", '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 40}]'],
        [User("Alice", 30), User("Bob", 40)],
    )
