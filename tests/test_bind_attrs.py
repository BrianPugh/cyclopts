from textwrap import dedent
from typing import Annotated

import pytest
from attrs import Factory, define, field

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
    tastes: dict[str, int] = field(factory=dict)
    outfit: Outfit | None = None
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
        Usage: test_bind_attrs foo USER.ID [ARGS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  USER.ID --user.id        [required]                             │
        │    USER.NAME --user.name    [default: John Doe]                    │
        │    --user.tastes DICT[STR,  [default: {}]                          │
        │      INT]                                                          │
        │    --user.outfit.body STR                                          │
        │    --user.outfit.head STR                                          │
        │    --user.admin             [default: False]                       │
        │      --user.not-admin                                              │
        │    --user.vip --not-vip     [default: False]                       │
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
        Usage: test_bind_attrs foo ID [ARGS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  ID --id                  [required]                             │
        │    NAME --name              [default: John Doe]                    │
        │    --tastes DICT[STR, INT]  [default: {}]                          │
        │    --outfit.body STR                                               │
        │    --outfit.head STR                                               │
        │    --admin --not-admin      [default: False]                       │
        │    --vip --not-vip          [default: False]                       │
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
        Usage: test_bind_attrs foo EXAMPLE

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


def test_attrs_field_metadata_help(app, console):
    """Test that attrs field metadata={"help": "..."} is used for help text."""

    @define
    class Config:
        name: str = field(default="default", metadata={"help": "Help from metadata."})

        age: Annotated[int, Parameter(help="Parameter help takes precedence.")] = field(
            default=25, metadata={"help": "This metadata help is ignored."}
        )

        count: int = field(default=10)
        """Docstring for count."""

        size: int = field(default=5, metadata={"help": "Metadata help overrides docstring."})
        """This docstring is ignored."""

    @app.default
    def main(config: Config):
        pass

    with console.capture() as capture:
        app("--help", console=console)

    actual = capture.get()

    assert "Help from metadata." in actual

    assert "Parameter help takes precedence." in actual
    assert "This metadata help is ignored." not in actual

    assert "Docstring for count." in actual

    assert "Metadata help overrides docstring." in actual
    assert "This docstring is ignored." not in actual


def test_attrs_inheritance_simple(app, console):
    """Test that docstrings from base attrs class are inherited by derived class."""

    @define
    class BaseClass:
        """Base class."""

        some_arg: int = 42
        """BaseClass.some_arg docstring."""

    @define
    class DerivedClass(BaseClass):
        """Derived class."""

        some_other_arg: str = "some_other_arg default value"
        """DerivedClass.some_other_arg docstring."""

    @app.default
    def main(params: DerivedClass):
        pass

    with console.capture() as capture:
        app("--help", console=console)

    actual = capture.get()

    # Check that both base and derived docstrings are present
    assert "BaseClass.some_arg docstring." in actual
    assert "DerivedClass.some_other_arg docstring." in actual


def test_bind_attrs_command_factory_help(app, console):
    """Attrs commands must not leak the ``attrs.NOTHING`` sentinel into help text.

    https://github.com/BrianPugh/cyclopts/issues/857
    """

    @app.command
    @define
    class Test:
        numbers: list[int] = field(factory=lambda: [1, 2, 3])

    with console.capture() as capture:
        app("test --help", console=console)

    actual = capture.get()

    assert "NOTHING" not in actual
    assert "[default: [1, 2, 3]]" in actual


def test_bind_attrs_command_takes_self_factory(app, console):
    """``takes_self`` factories cannot be resolved during introspection.

    The factory needs a constructed instance, so the field has no introspectable
    default: help must not show one (and must not leak the ``attrs.NOTHING``
    sentinel), yet the factory still runs at construction time when no token is
    given, and an explicit token overrides it.

    https://github.com/BrianPugh/cyclopts/issues/857
    """

    @app.command
    @define
    class Test:
        base: int = 5
        derived: int = field(default=Factory(lambda self: self.base * 2, takes_self=True))

        def __call__(self) -> int:
            return self.derived

    with console.capture() as capture:
        app("test --help", console=console)

    actual = capture.get()

    assert "NOTHING" not in actual
    # ``derived`` has no introspectable default; only ``base`` shows one.
    assert "[default: 5]" in actual
    assert actual.count("[default:") == 1

    # Factory resolves at construction when no token is provided.
    assert app(["test"], result_action=("call_if_callable", "return_value"), exit_on_error=False) == 10
    assert app(["test", "--base", "10"], result_action=("call_if_callable", "return_value"), exit_on_error=False) == 20
    # Explicit token overrides the factory.
    assert (
        app(["test", "--derived", "99"], result_action=("call_if_callable", "return_value"), exit_on_error=False) == 99
    )
