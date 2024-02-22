import sys

import pytest

from cyclopts.exceptions import ValidationError

if sys.version_info < (3, 9):
    from typing_extensions import Annotated  # pragma: no cover
else:
    from typing import Annotated  # pragma: no cover

from cyclopts import Group, Parameter
from cyclopts.validators import LimitedChoice


def test_limited_choice_default():
    """Mutually-exclusive functionality."""
    validator = LimitedChoice()

    validator()
    validator(foo=100)
    with pytest.raises(ValueError):
        validator(foo=100, bar=200)


def test_limited_choice_default_single():
    validator = LimitedChoice(1)
    with pytest.raises(ValueError):
        validator()
    validator(foo=100)
    with pytest.raises(ValueError):
        validator(foo=100, bar=200)


def test_limited_choice_default_min_max():
    validator = LimitedChoice(1, 2)
    with pytest.raises(ValueError):
        validator()
    validator(foo=100)
    validator(foo=100, bar=200)
    with pytest.raises(ValueError):
        validator(foo=100, bar=200, baz=300)


def test_limited_choice_invalid_min_max():
    with pytest.raises(ValueError):
        LimitedChoice(2, 1)


def test_bind_group_validator_limited_choice(app):
    @app.command
    def foo(
        *,
        car: Annotated[bool, Parameter(group=Group("Vehicle", validator=LimitedChoice()))] = False,
        motorcycle: Annotated[bool, Parameter(group="Vehicle")] = False,
    ):
        pass

    with pytest.raises(ValidationError) as e:
        app("foo --car --motorcycle", exit_on_error=False)

    assert str(e.value) == 'Invalid values for group "Vehicle". Mutually exclusive arguments: {--car, --motorcycle}'

    app("foo")
    app("foo --car")
    app("foo --motorcycle")


def test_bind_group_validator_limited_choice_name_override(app):
    @app.command
    def foo(
        *,
        car: Annotated[bool, Parameter(group=Group("Vehicle", validator=LimitedChoice()))] = False,
        motorcycle: Annotated[bool, Parameter(name="--bike", group="Vehicle")] = False,
    ):
        pass

    with pytest.raises(ValidationError) as e:
        app("foo --car --bike", exit_on_error=False)

    assert str(e.value) == 'Invalid values for group "Vehicle". Mutually exclusive arguments: {--car, --bike}'
