import sys
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Annotated

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
    tastes: dict[str, int] = field(default_factory=dict)


def test_bind_dataclass(app, assert_parse_args, console):
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


def test_bind_dataclass_missing_all_arguments(app, assert_parse_args, console):
    """We expect to see the first subargument (--user.id) in the error message,
    not the root "--user".
    """

    @app.default
    def default(some_number: int, user: User):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app("123", error_console=console, exit_on_error=False)
    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Parameter "--user.id" requires an argument.                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_bind_dataclass_recursive(app, assert_parse_args, console, normalize_trailing_whitespace):
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

        engine: Annotated[Engine, Parameter(name="*", group="Engine")] = field(kw_only=True)  # pyright: ignore
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
        Usage: test_bind_dataclasses build --license-plate STR --car.name STR
        --car.mileage FLOAT --car.cylinders INT --car.horsepower FLOAT
        --car.wheel.diameter INT [OPTIONS]

        Build a car.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  --license-plate       License plate identifier to give to car.  │
        │                          [required]                                │
        │ *  --car.name            The name/model of the car. [required]     │
        │ *  --car.mileage         How many miles the car has driven.        │
        │                          [required]                                │
        │ *  --car.wheel.diameter  Diameter of wheel in inches. [required]   │
        │    --car.n-axles         Number of axles the car has. [default: 2] │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Engine ───────────────────────────────────────────────────────────╮
        │ *  --car.cylinders           Number of cylinders the engine has.   │
        │                              [required]                            │
        │ *  --car.horsepower --car.p  Amount of horsepower the engine can   │
        │                              generate. [required]                  │
        │    --car.diesel              If this engine consumes diesel,       │
        │      --car.no-diesel         instead of gasoline. [default: False] │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert normalize_trailing_whitespace(actual) == expected


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
            error_console=console,
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
        a: int = field()  # intentionally empty field to make sure stuff doesn't assume this field has a default.
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
        Usage: test_bind_dataclasses A [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  A --a      Docstring for a. [required]                          │
        │    BAR --bar  This is the docstring for python parameter "b".      │
        │               [default: 2]                                         │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_bind_dataclass_default_factory_help(app, console):
    @dataclass
    class Config:
        a: int = field(default_factory=lambda: 5)
        """Docstring for a."""

    @app.default
    def my_default_command(config: Annotated[Config | None, Parameter(name="*")] = None):
        print(f"{config=}")

    with console.capture() as capture:
        app("--help", console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_bind_dataclasses [ARGS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ A --a  Docstring for a. [default: 5]                               │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


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


def test_bind_dataclass_positionally_with_keyword_only_exception_with_default(app, assert_parse_args):
    @dataclass
    class Config:
        a: int = 1
        """Docstring for a."""

        b: Annotated[int, Parameter(name="bar")] = 2
        """This is the docstring for python parameter "b"."""

        c: int = field(default=5, kw_only=True)  # pyright: ignore

    @app.default
    def my_default_command(config: Annotated[Config | None, Parameter(name="*")] = None):
        print(f"{config=}")

    with pytest.raises(UnusedCliTokensError):
        app.parse_args("100 200 300", exit_on_error=False)


def test_bind_dataclass_tuple_in_var_args(app, assert_parse_args):
    @dataclass
    class Square:
        center: tuple[float, float]
        side_length: float

    @app.default
    def my_default_command(*squares: Square):
        pass

    assert_parse_args(my_default_command, "10 20 30", Square(center=(10.0, 20.0), side_length=30.0))


def test_bind_dataclass_with_alias_attribute(app, assert_parse_args):
    """https://github.com/BrianPugh/cyclopts/issues/505"""

    @Parameter(name="*", negative=False)
    @dataclass
    class DataclassParameters:
        with_alias: Annotated[
            bool,
            Parameter(
                alias="-a",
                help="Parameter that uses alias.",
            ),
        ] = False

        with_iterable: Annotated[
            bool, Parameter(["--with-iterable", "-i"], help="Parameter that uses an iterable as name.")
        ] = False

    @app.default
    def main(*, params: DataclassParameters | None = None) -> None:
        pass

    assert_parse_args(main, "-a", params=DataclassParameters(with_alias=True, with_iterable=False))
    assert_parse_args(main, "--with-alias", params=DataclassParameters(with_alias=True, with_iterable=False))


def test_bind_dataclass_star_parameter_better_error_message(app, console):
    """Test that Parameter(name="*") raises ValueError at app setup time when parameter has no default."""

    @Parameter(name="*")
    @dataclass
    class Foo:
        bar: int = 12

    def cmd(foo: Foo):
        print(foo)

    expected_message = (
        r'Parameter "foo" in function .* has all optional values, uses Parameter\(name="\*"\), but itself has no default value\. Consider either:\n'
        r'    1\) If immutable, providing a default value "foo: Foo = Foo\(\)"\n'
        r'    2\) Otherwise, declaring it optional like "foo: Foo \| None = None" and instanting the foo object in the function body:\n'
        r"           if foo is None:\n"
        r"               foo = Foo\(\)"
    )

    with pytest.raises(ValueError, match=expected_message):
        app.default(cmd)


def test_bind_dataclass_with_varargs_consume_all(app, assert_parse_args):
    """Test dataclass with *args field that consumes all remaining tokens."""

    @dataclass
    class FileProcessor:
        output: str
        inputs: tuple[str, ...]

    @app.default
    def process(config: Annotated[FileProcessor, Parameter(name="*")]):
        pass

    assert_parse_args(
        process,
        "out.txt in1.txt in2.txt in3.txt",
        config=FileProcessor(output="out.txt", inputs=("in1.txt", "in2.txt", "in3.txt")),
    )


def test_dataclass_field_metadata_help(app, console):
    """Test that dataclass Field metadata={"help": "..."} is used for help text."""

    @dataclass
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


def test_bind_dataclass_direct_parent_match_issue_647(app, assert_parse_args):
    """Test that --foo bar baz correctly converts to Foo(name="bar", age=25).

    Previously, parent arguments with children would match directly (e.g., --foo),
    consume tokens, but then fail to properly construct the object because
    children had no tokens. The fix allows parent arguments to convert their
    tokens as positional arguments to the structured type.

    See: https://github.com/BrianPugh/cyclopts/issues/647
    """

    @dataclass
    class Foo:
        name: str
        age: int

    @app.default
    def cmd(*, foo: Annotated[Foo, Parameter()] = Foo(name="default", age=0)):  # noqa: B008
        return foo

    # This should work: directly provide values after parent name (positional-style)
    assert_parse_args(cmd, "--foo bar 25", foo=Foo(name="bar", age=25))

    # This should also still work: explicit nested keys
    assert_parse_args(cmd, "--foo.name baz --foo.age 30", foo=Foo(name="baz", age=30))

    # No arguments should use the function default (tested separately)
    _, bound, _ = app.parse_args("", print_error=False, exit_on_error=False)
    assert "foo" not in bound.arguments
    result = cmd(**bound.arguments)
    assert result == Foo(name="default", age=0)


def test_bind_dataclass_kw_only_with_accepts_keys_false_issue_648(app, assert_parse_args):
    """Test that kw_only dataclass with accepts_keys=False works.

    When a dataclass is kw_only=True, it cannot accept positional arguments.
    With accepts_keys=False, Cyclopts should still pass values as keyword arguments.

    See: https://github.com/BrianPugh/cyclopts/issues/648
    """

    @dataclass(kw_only=True)
    class Foo:
        name: str

    @app.default
    def cmd(*, foo: Annotated[Foo, Parameter(accepts_keys=False)]) -> Foo:
        return foo

    assert_parse_args(cmd, "--foo Alice", foo=Foo(name="Alice"))


@pytest.mark.skipif(sys.version_info < (3, 14), reason="Requires Python 3.14+ for field(doc=...)")
def test_dataclass_field_doc_parameter_help(app, console):
    """Test that Python 3.14's dataclass field(doc=...) parameter is used for help text."""

    @dataclass
    class Config:
        name: str = field(default="default", doc="Help from doc parameter.")  # type: ignore[call-arg]

        age: Annotated[int, Parameter(help="Parameter help takes precedence.")] = field(
            default=25,
            doc="This doc is ignored.",  # type: ignore[call-arg]
        )

        count: int = field(default=10, doc="Doc parameter help.")  # type: ignore[call-arg]

        size: int = field(
            default=5,
            metadata={"help": "Metadata help takes precedence over doc."},
            doc="This doc is ignored.",  # type: ignore[call-arg]
        )

        height: int = field(default=8)
        """Docstring for height."""

        width: int = field(default=12, doc="Doc parameter overrides docstring.")  # type: ignore[call-arg]
        """This docstring is ignored."""

    @app.default
    def main(config: Config):
        pass

    with console.capture() as capture:
        app("--help", console=console)

    actual = capture.get()

    assert "Help from doc parameter." in actual

    assert "Parameter help takes precedence." in actual
    assert "This doc is ignored." not in actual

    assert "Doc parameter help." in actual

    assert "Metadata help takes precedence" in actual

    assert "Docstring for height." in actual

    assert "Doc parameter overrides docstring." in actual
    assert "This docstring is ignored." not in actual


def test_dataclass_inheritance_simple(app, console):
    """Test that docstrings from base dataclass are inherited by derived class.

    Regression test for: https://github.com/BrianPugh/cyclopts/issues/691
    """

    @dataclass
    class BaseClass:
        """Base class."""

        some_arg: int = 42
        """BaseClass.some_arg docstring."""

    @dataclass
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


def test_dataclass_inheritance_multi_level(app, console):
    """Test that docstrings propagate through multiple inheritance levels."""

    @dataclass
    class GrandparentClass:
        """Grandparent class."""

        grandparent_field: int = 1
        """Grandparent field doc."""

    @dataclass
    class ParentClass(GrandparentClass):
        """Parent class."""

        parent_field: int = 2
        """Parent field doc."""

    @dataclass
    class ChildClass(ParentClass):
        """Child class."""

        child_field: int = 3
        """Child field doc."""

    @app.default
    def main(params: ChildClass):
        pass

    with console.capture() as capture:
        app("--help", console=console)

    actual = capture.get()

    # Check that all three levels of docstrings are present
    assert "Grandparent field doc." in actual
    assert "Parent field doc." in actual
    assert "Child field doc." in actual


def test_dataclass_inheritance_override_docstring(app, console):
    """Test that derived class can override base class docstrings."""

    @dataclass
    class BaseClass:
        """Base class."""

        shared_field: int = 1
        """Base docstring."""

    @dataclass
    class DerivedClass(BaseClass):
        """Derived class."""

        shared_field: int = 2
        """Derived docstring overrides base."""

        new_field: str = "new"
        """New field in derived."""

    @app.default
    def main(params: DerivedClass):
        pass

    with console.capture() as capture:
        app("--help", console=console)

    actual = capture.get()

    # Derived class docstring should take precedence
    assert "Derived docstring overrides base." in actual
    assert "Base docstring." not in actual
    assert "New field in derived." in actual


def test_dataclass_inheritance_with_parameter_name_star(app, console, normalize_trailing_whitespace):
    """Test inheritance with Parameter(name='*') works correctly."""

    @dataclass
    class BaseConfig:
        """Base configuration."""

        verbose: bool = False
        """Enable verbose output."""

    @dataclass
    class ExtendedConfig(BaseConfig):
        """Extended configuration."""

        debug: bool = False
        """Enable debug mode."""

    @app.default
    def main(config: Annotated[ExtendedConfig | None, Parameter(name="*")] = None):
        pass

    with console.capture() as capture:
        app("--help", console=console)

    actual = capture.get()

    # Both base and derived docstrings should be present
    assert "Enable verbose output." in actual
    assert "Enable debug mode." in actual


def test_dataclass_inheritance_no_docstrings_in_derived(app, console):
    """Test that base docstrings work even if derived class has no docstrings."""

    @dataclass
    class BaseClass:
        """Base class."""

        base_field: int = 1
        """Base field documentation."""

    @dataclass
    class DerivedClass(BaseClass):
        """Derived class."""

        # No docstring for this field
        derived_field: int = 2

    @app.default
    def main(params: DerivedClass):
        pass

    with console.capture() as capture:
        app("--help", console=console)

    actual = capture.get()

    # Base docstring should be present
    assert "Base field documentation." in actual
