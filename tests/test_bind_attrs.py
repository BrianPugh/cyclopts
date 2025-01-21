from textwrap import dedent
from typing import Annotated, Dict, Optional

import pytest
from attrs import define, field

from cyclopts import Parameter
from cyclopts.exceptions import MissingArgumentError, UnknownOptionError


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
    admin: Annotated[bool, Parameter(negative="not-admin")] = False
    vip: Annotated[bool, Parameter(negative="--not-vip")] = False
    staff: Annotated[bool, Parameter(parse=False)] = False


def test_bind_attrs(app, assert_parse_args, console):
    @app.command
    def foo(user: User):
        pass

    assert_parse_args(
        foo,
        "foo --user.id=123 --user.tastes.wine=9 --user.tastes.cheese=7 --user.tastes.cabbage=1 --user.outfit.body=t-shirt --user.outfit.head=baseball-cap --user.admin",
        User(
            id=123,
            tastes={"wine": 9, "cheese": 7, "cabbage": 1},
            outfit=Outfit(body="t-shirt", head="baseball-cap"),
            admin=True,
        ),
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
        │    USER.TASTES --user.tastes                                       │
        │    USER.OUTFIT.BODY                                                │
        │      --user.outfit.body                                            │
        │    USER.OUTFIT.HEAD                                                │
        │      --user.outfit.head                                            │
        │    USER.ADMIN --user.admin    [default: False]                     │
        │      --user.not-admin                                              │
        │    USER.VIP --user.vip        [default: False]                     │
        │      --not-vip                                                     │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_bind_attrs_flatten(app, assert_parse_args, console):
    @app.command
    def foo(user: Annotated[User, Parameter(name="*")]):
        pass

    assert_parse_args(
        foo,
        "foo --id=123 --tastes.wine=9 --tastes.cheese=7 --tastes.cabbage=1 --outfit.body=t-shirt --outfit.head=baseball-cap --admin",
        User(
            id=123,
            tastes={"wine": 9, "cheese": 7, "cabbage": 1},
            outfit=Outfit(body="t-shirt", head="baseball-cap"),
            admin=True,
        ),
    )

    with console.capture() as capture:
        app("foo --help", console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_bind_attrs foo [ARGS] [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  ID --id                    [required]                           │
        │    NAME --name                [default: John Doe]                  │
        │    TASTES --tastes                                                 │
        │    OUTFIT.BODY --outfit.body                                       │
        │    OUTFIT.HEAD --outfit.head                                       │
        │    ADMIN --admin --not-admin  [default: False]                     │
        │    VIP --vip --not-vip        [default: False]                     │
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


def test_bind_attrs_unknown_option(app, assert_parse_args):
    @define
    class Engine:
        cylinders: int
        volume: float

    @app.default
    def default(engine: Engine):
        pass

    with pytest.raises(UnknownOptionError):
        app("--engine.cylinders 4 --this-parameter-does-not-exist 100", exit_on_error=False)


def test_bind_attrs_alias(app, assert_parse_args):
    @define
    class Engine:
        cylinders: int
        volume: float = field(alias="cc")

    @app.default
    def default(engine: Engine):
        pass

    assert_parse_args(default, "--engine.cylinders 4 --engine.cc 100", Engine(cylinders=4, cc=100.0))

    with pytest.raises(UnknownOptionError):
        app("--engine.cylinders 4 --engine.volume 100", exit_on_error=False)
