import sys
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Annotated, Dict

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import (
    ArgumentOrderError,
    MissingArgumentError,
    UnusedCliTokensError,
)


@dataclass
class User:
    id: int
    name: str = "John Doe"
    tastes: Dict[str, int] = field(default_factory=dict)


def test_bind_dataclass(app, assert_parse_args):
    @app.command
    def foo(some_number: int, user: User):
        pass

    external_data = {
        "id": 123,
        # "name" is purposely missing.
        "tastes": {
            "wine": 9,
            "cheese": 7,
            "cabbage": 1,
        },
    }
    assert_parse_args(
        foo,
        "foo 100 --user.id=123 --user.tastes.wine=9 --user.tastes.cheese=7 --user.tastes.cabbage=1",
        100,
        User(**external_data),
    )


@pytest.mark.skipif(sys.version_info < (3, 10), reason="field(kw_only=True) doesn't exist.")
def test_bind_dataclass_recursive(app, assert_parse_args, console):
    @dataclass
    class Wheel:
        diameter: int
        "Diameter of wheel in inches."

    @dataclass
    class Engine:
        cylinders: int
        "Number of cylinders the engine has."

        hp: Annotated[float, Parameter(name=("horsepower", "p"))]
        "Amount of horsepower the engine can generate."

        diesel: bool = False
        "If this engine consumes diesel, instead of gasoline."

    @dataclass
    class Car:
        name: str
        "The name/model of the car."

        mileage: float
        "How many miles the car has driven."

        engine: Annotated[Engine, Parameter(name="*", group="Engine")] = field(kw_only=True)
        "The kind of engine the car is using."

        wheel: Wheel
        "The kind of wheels the car is using."

        n_axles: int = 2
        "Number of axles the car has."

    @app.command
    def build(*, license_plate: str, car: Car):
        """Build a car.

        Parameters
        ----------
        license_plate: str
            License plate identifier to give to car.
        car: Car
            Car specifications.
        """

    assert_parse_args(
        build,
        "build --car.name=ford --car.mileage=500 --car.cylinders=4 --car.p=200 --car.wheel.diameter=18 --license-plate=ABCDEFG",
        car=Car(
            name="ford",
            mileage=500,
            engine=Engine(cylinders=4, hp=200),
            wheel=Wheel(diameter=18),
        ),
        license_plate="ABCDEFG",
    )

    with console.capture() as capture:
        app("build --help", console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_bind_dataclasses build [OPTIONS]

        Build a car.

        ╭─ Engine ───────────────────────────────────────────────────────────╮
        │ *  --car.cylinders           Number of cylinders the engine has.   │
        │                              [required]                            │
        │ *  --car.horsepower --car.p  Amount of horsepower the engine can   │
        │                              generate. [required]                  │
        │    --car.diesel              If this engine consumes diesel,       │
        │      --car.no-diesel         instead of gasoline. [default: False] │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  --license-plate       License plate identifier to give to car.  │
        │                          [required]                                │
        │ *  --car.name            The name/model of the car. [required]     │
        │ *  --car.mileage         How many miles the car has driven.        │
        │                          [required]                                │
        │ *  --car.wheel.diameter  Diameter of wheel in inches. [required]   │
        │    --car.n-axles         Number of axles the car has. [default: 2] │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_bind_dataclass_recursive_missing_arg(app, assert_parse_args, console):
    """The ``engine`` parameter itself is optional, but if specified it has 2 required fields."""

    @dataclass
    class Engine:
        cylinders: int
        hp: float = 100

    @dataclass
    class Car:
        name: str
        mileage: float
        engine: Annotated[Engine, Parameter(name="*", group="Engine")] = field(default_factory=lambda: Engine(8, 500))

    @app.command
    def build(*, license_plate: str, car: Car):
        pass

    # Specifying a complete engine works.
    assert_parse_args(
        build,
        "build --car.name=ford --car.mileage=500 --car.cylinders=4 --car.hp=200 --license-plate=ABCDEFG",
        car=Car(name="ford", mileage=500, engine=Engine(cylinders=4, hp=200)),
        license_plate="ABCDEFG",
    )

    # Specifying NO engine works.
    assert_parse_args(
        build,
        "build --car.name=ford --car.mileage=500 --license-plate=ABCDEFG",
        car=Car(name="ford", mileage=500),
        license_plate="ABCDEFG",
    )

    # Partially defining an engine does NOT work.
    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app.parse_args(
            "build --car.name=ford --car.mileage=500 --car.hp=200 --license-plate=ABCDEFG",
            console=console,
            exit_on_error=False,
        )

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "build" parameter "--car.cylinders" requires an argument.  │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


@pytest.mark.parametrize(
    "cmd",
    [
        "'Bob Smith' 30",
        "--nickname='Bob Smith' --player.years-young=30",
    ],
)
def test_bind_dataclass_double_name_override_no_hyphen(app, assert_parse_args, console, cmd):
    @dataclass
    class User:
        # Beginning with "--" will completely override the parenting parameter name.
        name: Annotated[str, Parameter(name="--nickname")]
        # Not beginning with "--" will tack it on to the parenting parameter name.
        age: Annotated[int, Parameter(name="years-young")]

    @app.default
    def main(user: Annotated[User, Parameter(name="player")]):  # but what about without --?
        print(user)

    assert_parse_args(main, cmd, user=User("Bob Smith", 30))


@pytest.mark.parametrize(
    "cmd_str",
    [
        "100 200",
        "--a 100 --bar 200",
        "--bar 200 100",
    ],
)
def test_bind_dataclass_positionally(app, assert_parse_args, cmd_str, console):
    @dataclass
    class Config:
        a: int = 1
        """Docstring for a."""

        b: Annotated[int, Parameter(name="bar")] = 2
        """This is the docstring for python parameter "b"."""

    @app.default
    def my_default_command(config: Annotated[Config, Parameter(name="*")]):
        print(f"{config=}")

    assert_parse_args(my_default_command, cmd_str, Config(a=100, b=200))

    with console.capture() as capture:
        app("build --help", console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: my-default-command COMMAND [ARGS] [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ A --a      Docstring for a. [default: 1]                           │
        │ BAR --bar  This is the docstring for python parameter "b".         │
        │            [default: 2]                                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


@pytest.mark.skipif(sys.version_info < (3, 10), reason="field(kw_only=True) doesn't exist.")
def test_bind_dataclass_positionally_with_keyword_only_exception_no_default(app, assert_parse_args):
    @dataclass
    class Config:
        a: int = 1
        """Docstring for a."""

        b: Annotated[int, Parameter(name="bar")] = 2
        """This is the docstring for python parameter "b"."""

        c: int = field(kw_only=True)  # pyright: ignore

    @app.default
    def my_default_command(foo, config: Annotated[Config, Parameter(name="*")], bar):
        print(f"{config=}")

    expected = ("v1", Config(100, 200, c=300), "v2")
    assert_parse_args(my_default_command, "v1 100 200 v2 --c=300", *expected)
    assert_parse_args(my_default_command, "--c=300 v1 100 200 v2", *expected)
    with pytest.raises(MissingArgumentError):
        app.parse_args("v1 100 200 300 v2", exit_on_error=False)
    with pytest.raises(ArgumentOrderError):
        app.parse_args("v1 --a=100 200 300 v2", exit_on_error=False)
    with pytest.raises(ArgumentOrderError):
        app.parse_args("v1 --bar=v2 100 200 --c=300", exit_on_error=False)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="field(kw_only=True) doesn't exist.")
def test_bind_dataclass_positionally_with_keyword_only_exception_with_default(app, assert_parse_args):
    @dataclass
    class Config:
        a: int = 1
        """Docstring for a."""

        b: Annotated[int, Parameter(name="bar")] = 2
        """This is the docstring for python parameter "b"."""

        c: int = field(default=5, kw_only=True)  # pyright: ignore

    @app.default
    def my_default_command(config: Annotated[Config, Parameter(name="*")]):
        print(f"{config=}")

    with pytest.raises(UnusedCliTokensError):
        app.parse_args("100 200 300", exit_on_error=False)
