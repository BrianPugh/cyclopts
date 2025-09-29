from textwrap import dedent
from typing import Annotated, Literal

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import MissingArgumentError


class Outfit:
    def __init__(self, body: str, head: str):
        self.body = body
        self.head = head

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.body == other.body and self.head == other.head


class User:
    def __init__(
        self,
        id: int,
        name: str = "John Doe",
        tastes: dict[str, int] | None = None,
        outfit: Annotated[Outfit, Parameter(accepts_keys=True)] | None = None,
    ):
        self.id = id
        self.name = name
        self.tastes = tastes if tastes is not None else {}
        self.outfit = outfit

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return (
            self.id == other.id
            and self.name == other.name
            and self.tastes == other.tastes
            and self.outfit == other.outfit
        )


def test_bind_generic_class_accepts_keys_true(app, assert_parse_args):
    @app.command
    def foo(user: Annotated[User, Parameter(accepts_keys=True)]):
        pass

    assert_parse_args(
        foo,
        "foo --user.id=123 --user.tastes.wine=9 --user.tastes.cheese=7 --user.tastes.cabbage=1 --user.outfit.body=t-shirt --user.outfit.head=baseball-cap",
        User(id=123, tastes={"wine": 9, "cheese": 7, "cabbage": 1}, outfit=Outfit(body="t-shirt", head="baseball-cap")),
    )


def test_bind_generic_class_accepts_keys_none_1_args(app, assert_parse_args, console):
    class User:
        def __init__(self, age: int):
            self.age = age

        def __eq__(self, other):
            if not isinstance(other, type(self)):
                return False
            return self.age == other.age

    @app.command
    def foo(user: User):
        pass

    assert_parse_args(foo, "foo 100", User(100))

    with console.capture() as capture:
        app("foo --help", console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_bind_generic_class foo [ARGS] [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  USER.AGE --user.age  [required]                                 │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_bind_generic_class_accepts_keys_false_1_args(app, assert_parse_args, console):
    class User:
        def __init__(self, age: int):
            self.age = age

        def __eq__(self, other):
            if not isinstance(other, type(self)):
                return False
            return self.age == other.age

    @app.command
    def foo(user: Annotated[User, Parameter(accepts_keys=False)]):
        pass

    assert_parse_args(foo, "foo 100", User(100))

    with console.capture() as capture:
        app("foo --help", console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_bind_generic_class foo [ARGS] [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  USER --user  [required]                                         │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


class Coordinates:
    def __init__(
        self,
        x: float,
        y: float,
        *,
        color: Literal["red", "green", "blue"] = "red",
    ):
        self.x = x
        self.y = y
        self.color = color

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.x == other.x and self.y == other.y and self.color == other.color


def test_bind_generic_class_accepts_default_multiple_args(app, assert_parse_args, console):
    @app.command
    def foo(coords: Coordinates, priority: int):
        pass

    assert_parse_args(foo, "foo 100 200 7", Coordinates(100, 200), 7)

    with console.capture() as capture:
        app("foo --help", console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_bind_generic_class foo [ARGS] [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  COORDS.X --coords.x  [required]                                 │
        │ *  COORDS.Y --coords.y  [required]                                 │
        │ *  PRIORITY --priority  [required]                                 │
        │    --coords.color       [choices: red, green, blue] [default: red] │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_bind_generic_class_accepts_false_multiple_args(app, assert_parse_args, console):
    @app.command
    def foo(coords: Annotated[Coordinates, Parameter(accepts_keys=False)]):
        pass

    assert_parse_args(foo, "foo 100 200", Coordinates(100, 200))

    with console.capture() as capture:
        app("foo --help", console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_bind_generic_class foo [ARGS] [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  COORDS --coords  [required]                                     │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_bind_generic_class_keyword_with_positional_only_subkeys(app, console, assert_parse_args):
    """This test has a keyword-only parameter that has position-only subkeys, which are skipped."""

    class User:
        def __init__(self, name: str, age: int, /):
            self.name = name
            self.age = age

        def __eq__(self, other):
            if not isinstance(other, type(self)):
                return False
            return self.name == other.name and self.age == other.age

    @app.command
    def foo(*, user: User):
        pass

    assert_parse_args(foo, "foo --user Bob 30", user=User("Bob", 30))

    with console.capture() as capture:
        app("foo --help", console=console)

    actual = capture.get()

    # No arguments/parameters
    expected = dedent(
        """\
        Usage: test_bind_generic_class foo [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  --user  [required]                                              │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected

    with pytest.raises(MissingArgumentError):
        app("foo --user.name=Bob --user.age=100", exit_on_error=False)
