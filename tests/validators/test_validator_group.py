from typing import Annotated

import pytest

from cyclopts import Argument, Group, Parameter, Token
from cyclopts.argument import ArgumentCollection
from cyclopts.exceptions import ValidationError
from cyclopts.validators import LimitedChoice


@pytest.fixture
def argument_collection_0():
    return ArgumentCollection(
        [
            Argument(cparam=Parameter(name="--foo")),
            Argument(cparam=Parameter(name="--bar")),
            Argument(cparam=Parameter(name="--baz")),
        ]
    )


@pytest.fixture
def argument_collection_1():
    return ArgumentCollection(
        [
            Argument(
                tokens=[Token(keyword="--foo", value="100", source="test")],
                cparam=Parameter(name="--foo"),
                value=100,
            ),
            Argument(cparam=Parameter(name="--bar")),
            Argument(cparam=Parameter(name="--baz")),
        ]
    )


@pytest.fixture
def argument_collection_2():
    return ArgumentCollection(
        [
            Argument(
                tokens=[Token(keyword="--foo", value="100", source="test")],
                cparam=Parameter(name="--foo"),
                value=100,
            ),
            Argument(
                tokens=[Token(keyword="--bar", value="200", source="test")],
                cparam=Parameter(name="--bar"),
                value=200,
            ),
            Argument(cparam=Parameter(name="--baz")),
        ]
    )


@pytest.fixture
def argument_collection_3():
    return ArgumentCollection(
        [
            Argument(
                tokens=[Token(keyword="--foo", value="100", source="test")],
                cparam=Parameter(name="--foo"),
                value=100,
            ),
            Argument(
                tokens=[Token(keyword="--bar", value="200", source="test")],
                cparam=Parameter(name="--bar"),
                value=200,
            ),
            Argument(
                tokens=[Token(keyword="--baz", value="300", source="test")],
                cparam=Parameter(name="--baz"),
                value=300,
            ),
        ]
    )


def test_limited_choice_default_success(argument_collection_0, argument_collection_1):
    """Mutually-exclusive functionality."""
    validator = LimitedChoice()
    validator(argument_collection_0)
    validator(argument_collection_1)


@pytest.mark.parametrize("min", [None, 1])
def test_limited_choice_default_failure(min, argument_collection_2):
    """Mutually-exclusive functionality."""
    if min is None:
        validator = LimitedChoice()
    else:
        validator = LimitedChoice(min)
    validator = LimitedChoice()
    with pytest.raises(ValueError):
        validator(argument_collection_2)


def test_limited_choice_default_min_max(
    argument_collection_0, argument_collection_1, argument_collection_2, argument_collection_3
):
    validator = LimitedChoice(1, 2)
    with pytest.raises(ValueError):
        validator(argument_collection_0)
    validator(argument_collection_1)
    validator(argument_collection_2)
    with pytest.raises(ValueError):
        validator(argument_collection_3)


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
