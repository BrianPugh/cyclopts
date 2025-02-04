from dataclasses import dataclass
from textwrap import dedent
from typing import Annotated, Optional

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
    def create(*, user: Optional[User] = None):
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
        Usage: test_parameter_decorator action [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  --bucket  [required]                                            │
        │ *  --key     [required]                                            │
        │ *  --region  [required]                                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_parameter_decorator_dataclass_inheritance(app, assert_parse_args):
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
    def create(*, user: Optional[User] = None, admin: Optional[Admin] = None):
        pass

    assert_parse_args(create, "create --u.name=Bob --u.age=100", user=User("Bob", 100))
    with pytest.raises(UnknownOptionError):
        app("create --u.no-privileged", exit_on_error=False)

    assert_parse_args(create, "create --a.name=Bob --a.age=100", admin=Admin("Bob", 100))
    assert_parse_args(
        create, "create --a.name=Bob --a.age=100 --a.no-privileged", admin=Admin("Bob", 100, privileged=False)
    )
