from dataclasses import dataclass
from typing import Optional

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import UnknownOptionError


def test_parameter_decorator_dataclass(app, assert_parse_args):
    @Parameter(name="*")  # Flatten namespace.
    @dataclass
    class User:
        name: str
        age: int

    @app.command
    def create(*, user: Optional[User] = None):
        pass

    assert_parse_args(create, "create")
    assert_parse_args(create, "create --name=Bob --age=100", user=User("Bob", 100))


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
