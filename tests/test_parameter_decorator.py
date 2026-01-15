from dataclasses import dataclass
from textwrap import dedent
from typing import Annotated

import pytest
from attrs import define

from cyclopts import Parameter
from cyclopts.exceptions import UnknownOptionError


@pytest.mark.parametrize("decorator", [dataclass, define])
def test_parameter_decorator_dataclass(app, assert_parse_args, decorator):
    @Parameter(name="*")  # Flatten namespace.
    @decorator
    class User:
        name: str
        age: int

    @app.command
    def create(*, user: User | None = None):
        pass

    assert_parse_args(create, "create")
    assert_parse_args(create, "create --name=Bob --age=100", user=User("Bob", 100))  # pyright: ignore[reportCallIssue]


@pytest.mark.parametrize("decorator", [dataclass, define])
def test_parameter_decorator_dataclass_nested_1(app, decorator, console):
    """
    https://github.com/BrianPugh/cyclopts/issues/320
    """

    @decorator
    class S3Path:
        bucket: Annotated[str, Parameter()]
        key: Annotated[str, Parameter()]

    @Parameter(name="*")  # Flatten namespace.
    @decorator
    class S3CliParams:
        path: Annotated[S3Path, Parameter(name="*")]
        region: Annotated[str, Parameter(name="region")]

    @app.command
    def action(*, s3_path: S3CliParams):
        pass

    with console.capture() as capture:
        app("action --help", console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_parameter_decorator action --bucket STR --key STR --region
        STR

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  --bucket  [required]                                            │
        │ *  --key     [required]                                            │
        │ *  --region  [required]                                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_parameter_decorator_dataclass_inheritance(app, assert_parse_args):
    @Parameter(name="person")  # Should override the name="u" below.
    @Parameter(name="u", negative_bool=[])
    @dataclass
    class User:
        name: str
        age: int
        privileged: bool = False

    @Parameter(name="a", negative_bool=None)  # Should revert to Cyclopts defaults
    @dataclass
    class Admin(User):
        privileged: bool = True

    @app.command
    def create(*, user: User | None = None, admin: Admin | None = None):
        pass

    assert_parse_args(create, "create --person.name=Bob --person.age=100", user=User("Bob", 100))
    with pytest.raises(UnknownOptionError):
        app("create --person.no-privileged", exit_on_error=False)

    assert_parse_args(create, "create --a.name=Bob --a.age=100", admin=Admin("Bob", 100))
    assert_parse_args(
        create, "create --a.name=Bob --a.age=100 --a.no-privileged", admin=Admin("Bob", 100, privileged=False)
    )


def test_parameter_class_decorator_with_annotated(app, assert_parse_args):
    """Test that @Parameter on a class works when the type is wrapped in Annotated.

    This is a regression test for a bug where __cyclopts__ was checked before
    unwrapping Annotated, so class-level Parameter settings were ignored.
    """

    @Parameter(allow_leading_hyphen=True)
    class MyType:
        def __init__(self, value: str):
            self.value = value

        def __eq__(self, other):
            return self.value == other.value

    @app.default
    def foo(arg: Annotated[MyType, Parameter(help="Custom help text.")]):
        pass

    # The class-level allow_leading_hyphen=True should be respected
    # even when MyType is wrapped in Annotated with additional Parameter config
    assert_parse_args(foo, "-", arg=MyType("-"))
    assert_parse_args(foo, "--foo", arg=MyType("--foo"))
