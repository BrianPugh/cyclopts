from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, NamedTuple, TypedDict

import attrs
from pydantic import BaseModel

from cyclopts import Parameter


def test_future_annotations_basic(app, assert_parse_args):
    @app.default
    def default(value: str):
        pass

    assert_parse_args(default, "foo", "foo")


# TODO: Resolving stringified type-hinted class with closure/local scope
# is really hard.
@dataclass
class DataclassMovie:
    title: str
    year: int


def test_future_annotations_dataclass(app, assert_parse_args):
    """
    https://github.com/BrianPugh/cyclopts/issues/352
    """

    @app.command
    def add(movie: DataclassMovie):
        print(f"Adding movie: {movie}")

    assert_parse_args(add, "add BladeRunner 1982", DataclassMovie("BladeRunner", 1982))


# This is unrelated to "from __future__ import annotations", but it's a very similar problem
class GenericMovie:
    def __init__(self, title: str, year: int):
        self.title = title
        self.year = year

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.title == other.title and self.year == other.year


def test_future_annotations_generic_class(app, assert_parse_args):
    @app.command
    def add(movie: Annotated[GenericMovie, Parameter(accepts_keys=True)]):
        print(f"Adding movie: {movie}")

    assert_parse_args(add, "add BladeRunner 1982", GenericMovie("BladeRunner", 1982))


@attrs.define
class AttrsMovie:
    title: str
    year: int


def test_future_annotations_attrs_movie(app, assert_parse_args):
    @app.command
    def add(movie: Annotated[AttrsMovie, Parameter(accepts_keys=True)]):
        print(f"Adding movie: {movie}")

    assert_parse_args(add, "add BladeRunner 1982", AttrsMovie("BladeRunner", 1982))


class TypedDictMovie(TypedDict):
    title: str
    year: int


def test_future_annotations_typed_dict_movie(app, assert_parse_args):
    @app.command
    def add(movie: Annotated[TypedDictMovie, Parameter(accepts_keys=True)]):
        print(f"Adding movie: {movie}")

    assert_parse_args(
        add, "add --movie.title=BladeRunner --movie.year=1982", TypedDictMovie(title="BladeRunner", year=1982)
    )


class NamedTupleMovie(NamedTuple):
    title: str
    year: int


def test_future_annotations_named_tuple_movie(app, assert_parse_args):
    @app.command
    def add(movie: Annotated[NamedTupleMovie, Parameter(accepts_keys=True)]):
        print(f"Adding movie: {movie}")

    assert_parse_args(add, "add BladeRunner 1982", NamedTupleMovie(title="BladeRunner", year=1982))


class PydanticMovie(BaseModel):
    title: str
    year: int


def test_future_annotations_pydantic_movie(app, assert_parse_args):
    @app.command
    def add(movie: Annotated[PydanticMovie, Parameter(accepts_keys=True)]):
        print(f"Adding movie: {movie}")

    assert_parse_args(add, "add BladeRunner 1982", PydanticMovie(title="BladeRunner", year=1982))
