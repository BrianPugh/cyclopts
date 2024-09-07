from dataclasses import dataclass, field
from textwrap import dedent
from typing import Annotated, Dict

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import MissingArgumentError


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


def test_bind_dataclass_recursive(app, assert_parse_args, console):
    @dataclass
    class Wheel:
        diameter: int
        "Diameter of wheel in inches."

    @dataclass
    class Engine:
        cylinders: int
        "Number of cylinders the engine has."

        hp: float
        "Amount of horsepower the engine can generate."

    @dataclass
    class Car:
        name: str
        "The name/model of the car."

        mileage: float
        "How many miles the car has driven."

        engine: Annotated[Engine, Parameter(name="*", group="Engine")]
        "The kind of engine the car is using."

        wheel: Wheel
        "The kind of wheels the car is using."

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
        "build --car.name=ford --car.mileage=500 --car.cylinders=4 --car.hp=200 --car.wheel.diameter=18 --license-plate=ABCDEFG",
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
    print(actual)

    expected = dedent(
        """\
        Usage: test_bind_dataclasses build [OPTIONS]

        Build a car.

        ╭─ Engine ───────────────────────────────────────────────────────────╮
        │ --car.cylinders  Number of cylinders the engine has.               │
        │ --car.hp         Amount of horsepower the engine can generate.     │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  --license-plate       License plate identifier to give to car.  │
        │                          [required]                                │
        │    --car.name            The name/model of the car.                │
        │    --car.mileage         How many miles the car has driven.        │
        │    --car.wheel.diameter  Diameter of wheel in inches.              │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_bind_dataclass_recursive_missing_arg(app, assert_parse_args, console):
    """The ``engine`` parameter itself is optional, but if specified it has 2 required fields."""

    @dataclass
    class Engine:
        cylinders: int
        hp: float

    @dataclass
    class Car:
        name: str
        mileage: float
        engine: Annotated[Engine, Parameter(name="*", group="Engine")] = Engine(8, 500)

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
    with pytest.raises(MissingArgumentError):
        app.parse_args(
            "build --car.name=ford --car.mileage=500 --car.hp=200 --license-plate=ABCDEFG",
            exit_on_error=False,
        )
