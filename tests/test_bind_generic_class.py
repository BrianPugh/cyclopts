from textwrap import dedent
from typing import Annotated, Dict, Literal, Optional

from cyclopts import Parameter


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
        tastes: Optional[Dict[str, int]] = None,
        outfit: Optional[Annotated[Outfit, Parameter(accepts_keys=True)]] = None,
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


def test_bind_generic_class_accepts_default_1_args(app, assert_parse_args, console):
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
    def foo(coords: Coordinates):
        pass

    assert_parse_args(foo, "foo 100 200", Coordinates(100, 200))

    with console.capture() as capture:
        app("foo --help", console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_bind_generic_class foo [ARGS] [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  COORDS.X --coords.x  [required]                                 │
        │ *  COORDS.Y --coords.y  [required]                                 │
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
