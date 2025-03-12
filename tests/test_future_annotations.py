from __future__ import annotations

from dataclasses import dataclass


def test_future_annotations_basic(app, assert_parse_args):
    @app.default
    def default(value: str):
        pass

    assert_parse_args(default, "foo", "foo")


# TODO: Resolving stringified type-hinted class with closure/local scope
# is really hard.
@dataclass
class Movie:
    title: str
    year: int


def test_future_annotations_dataclass(app, assert_parse_args):
    """
    https://github.com/BrianPugh/cyclopts/issues/352
    """

    @app.command
    def add(movie: Movie):
        print(f"Adding movie: {movie}")

    assert_parse_args(add, "add BladeRunner 1982", Movie("BladeRunner", 1982))
