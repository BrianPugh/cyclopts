from textwrap import dedent
from typing import Annotated, Dict, Optional

import pytest
from attrs import define, field

from cyclopts import Parameter
from cyclopts.exceptions import MissingArgumentError


@define
class Outfit:
    body: str
    head: str


@define
class User:
    id: int
    name: str = "John Doe"
    tastes: Dict[str, int] = field(factory=dict)
    outfit: Optional[Outfit] = None
    staff: Annotated[bool, Parameter(parse=False)] = False


def test_bind_attrs(app, assert_parse_args, console):
    @app.command
    def foo(user: User):
        pass

    assert_parse_args(
        foo,
        "foo --user.id=123 --user.tastes.wine=9 --user.tastes.cheese=7 --user.tastes.cabbage=1 --user.outfit.body=t-shirt --user.outfit.head=baseball-cap",
        User(id=123, tastes={"wine": 9, "cheese": 7, "cabbage": 1}, outfit=Outfit(body="t-shirt", head="baseball-cap")),
    )

    with console.capture() as capture:
        app("foo --help", console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_bind_attrs foo [ARGS] [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  USER.ID --user.id          [required]                           │
        │    USER.NAME --user.name      [default: John Doe]                  │
        │    USER.TASTES --user.tastes  [default: _Nothing.NOTHING]          │
        │    USER.OUTFIT.BODY                                                │
        │      --user.outfit.body                                            │
        │    USER.OUTFIT.HEAD                                                │
        │      --user.outfit.head                                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_bind_attrs_accepts_keys_false(app, assert_parse_args, console):
    @define
    class SimpleClass:
        value: int
        name: str

    @app.command
    def foo(example: Annotated[SimpleClass, Parameter(accepts_keys=False)]):
        pass

    assert_parse_args(foo, "foo 5 foo", SimpleClass(5, "foo"))
    assert_parse_args(foo, "foo --example=5 foo", SimpleClass(5, "foo"))

    with console.capture() as capture:
        app("foo --help", console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_bind_attrs foo [ARGS] [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  EXAMPLE --example  [required]                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_bind_attrs_kw_only(app, assert_parse_args):
    @define
    class Engine:
        cylinders: int
        volume: float
        power: Annotated[float, Parameter(name="--power")] = field(kw_only=True)

    @app.default
    def default(engine: Engine):
        pass

    assert_parse_args(default, "4 100 --power=200", Engine(4, 100, power=200))
    assert_parse_args(default, "--power=200 4 100", Engine(4, 100, power=200))
    assert_parse_args(default, "4 --power=200 100", Engine(4, 100, power=200))
    with pytest.raises(MissingArgumentError):
        app.parse_args("4 100 200", exit_on_error=False)
