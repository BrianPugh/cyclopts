from typing import Annotated

import pytest

from cyclopts import Argument, Group, Parameter, Token
from cyclopts.argument import ArgumentCollection
from cyclopts.exceptions import ValidationError
from cyclopts.validators import LimitedChoice, all_or_none


@pytest.fixture
def argument_collection_0():
    return ArgumentCollection(
        [
            Argument(parameter=Parameter(name="--foo")),
            Argument(parameter=Parameter(name="--bar")),
            Argument(parameter=Parameter(name="--baz")),
        ]
    )


@pytest.fixture
def argument_collection_1():
    return ArgumentCollection(
        [
            Argument(
                tokens=[Token(keyword="--foo", value="100", source="test")],
                parameter=Parameter(name="--foo"),
                value=100,
            ),
            Argument(parameter=Parameter(name="--bar")),
            Argument(parameter=Parameter(name="--baz")),
        ]
    )


@pytest.fixture
def argument_collection_2():
    return ArgumentCollection(
        [
            Argument(
                tokens=[Token(keyword="--foo", value="100", source="test")],
                parameter=Parameter(name="--foo"),
                value=100,
            ),
            Argument(
                tokens=[Token(keyword="--bar", value="200", source="test")],
                parameter=Parameter(name="--bar"),
                value=200,
            ),
            Argument(parameter=Parameter(name="--baz")),
        ]
    )


@pytest.fixture
def argument_collection_3():
    return ArgumentCollection(
        [
            Argument(
                tokens=[Token(keyword="--foo", value="100", source="test")],
                parameter=Parameter(name="--foo"),
                value=100,
            ),
            Argument(
                tokens=[Token(keyword="--bar", value="200", source="test")],
                parameter=Parameter(name="--bar"),
                value=200,
            ),
            Argument(
                tokens=[Token(keyword="--baz", value="300", source="test")],
                parameter=Parameter(name="--baz"),
                value=300,
            ),
        ]
    )


def test_limited_choice_default_success(argument_collection_0, argument_collection_1, argument_collection_2):
    validator = LimitedChoice()  # Mutually-exclusive functionality.
    validator(argument_collection_0)  # no tokens
    validator(argument_collection_1)  # 1 token

    validator = LimitedChoice(2)
    validator(argument_collection_2)  # 2 tokens
    with pytest.raises(ValueError):
        validator(argument_collection_0)

    validator = LimitedChoice(2, allow_none=True)
    validator(argument_collection_0)


def test_limited_choice_failure_1(argument_collection_2):
    validator = LimitedChoice()
    with pytest.raises(ValueError):
        # 2 supplied tokens, but we only allow 1
        validator(argument_collection_2)


def test_limited_choice_failure_2(argument_collection_2, argument_collection_3):
    validator = LimitedChoice(2)
    validator(argument_collection_2)
    with pytest.raises(ValueError):
        validator(argument_collection_3)


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
    """Minimum value must be less than maximum value."""
    with pytest.raises(ValueError):
        LimitedChoice(2, 1)


def test_limited_choice_all_or_none(argument_collection_0, argument_collection_1, argument_collection_3):
    """All arguments in the group must be supplied."""
    all_or_none(argument_collection_0)  # none
    all_or_none(argument_collection_3)  # all

    with pytest.raises(ValueError):
        all_or_none(argument_collection_1)  # 1 out of 3


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


def test_group_validator_complete_argument_collection(app, mocker):
    custom_validator = mocker.MagicMock()
    group = Group("Vehicle", validator=(custom_validator,))

    @app.default
    def default(
        *,
        car: Annotated[bool, Parameter(group=group)] = False,
        motorcycle: Annotated[bool, Parameter(group=group)] = False,
    ):
        pass

    app([])

    custom_validator.assert_called_once()
    argument_collection_names = [x.name for x in custom_validator.call_args_list[0][0][0]]
    assert argument_collection_names == ["--car", "--motorcycle"]


def test_limited_choice_negative_flag_error_message(app):
    """Test for Issue #631: Error message should show the actual flag the user typed.

    When a mutually exclusive validation error occurs, the error message should display
    the exact flags the user provided, not alternative names for the same parameter.

    This tests that negative flags (--neg) appear in error messages when used,
    rather than showing the positive flag name (--affirm).
    """
    group = Group(show=False, validator=LimitedChoice())

    @app.default
    def cmd(
        *,
        param: Annotated[bool, Parameter(name=("--affirm", "-a"), negative=("--neg", "-n"), group=group)] = False,
        opt: Annotated[int, Parameter(group=group)] = 0,
    ):
        pass

    # Test with negative flag
    with pytest.raises(ValidationError) as exc_info:
        app("--neg --opt 10", exit_on_error=False)

    error_message = str(exc_info.value)
    assert "--neg" in error_message
    assert "--opt" in error_message
    assert "--affirm" not in error_message

    # Test with positive flag
    with pytest.raises(ValidationError) as exc_info:
        app("--affirm --opt 10", exit_on_error=False)

    error_message = str(exc_info.value)
    assert "--affirm" in error_message
    assert "--opt" in error_message
    assert "--neg" not in error_message

    # Test with short negative flag
    with pytest.raises(ValidationError) as exc_info:
        app("-n --opt 10", exit_on_error=False)

    error_message = str(exc_info.value)
    assert "-n" in error_message
    assert "--opt" in error_message

    # Test with short positive flag
    with pytest.raises(ValidationError) as exc_info:
        app("-a --opt 10", exit_on_error=False)

    error_message = str(exc_info.value)
    assert "-a" in error_message
    assert "--opt" in error_message
