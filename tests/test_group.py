import sys
from typing import Union
from unittest.mock import Mock

import pytest

from cyclopts import App, Group, Parameter

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated


class SentinelError(Exception):
    pass


def upper(type_, *args: str):
    return args[0].upper()


def test_group_default_parameter_converter(app, assert_parse_args):
    food_group = Group("Food", default_parameter=Parameter(converter=upper))

    @app.default
    def foo(ice_cream: Annotated[str, Parameter(group=food_group)]):
        pass

    assert_parse_args(foo, "chocolate", "CHOCOLATE")


def test_group_default_parameter_validator(app):
    validator = Mock()

    food_group = Group("Food", default_parameter=Parameter(validator=validator))

    @app.default
    def foo(ice_cream: Annotated[str, Parameter(group=food_group)]):
        pass

    app.parse_args("chocolate")
    validator.assert_called_once()


def test_group_validator(app):
    validator = Mock()

    group = Group("Spices", validator=validator)

    @app.default
    def foo(
        salt: Annotated[bool, Parameter("--rock-salt", group=group)] = False,
        pepper: Annotated[bool, Parameter("--peppercorn", group=group)] = False,
        ketchup: bool = False,
    ):
        pass

    app.parse_args("--rock-salt --peppercorn --ketchup")

    validator.assert_called_once_with(salt=True, pepper=True)
