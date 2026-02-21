from typing import Annotated

import pytest

import cyclopts
from cyclopts import Parameter
from cyclopts.exceptions import RequiresEqualsError


def test_requires_equals_with_equals(app, assert_parse_args):
    """--option=value should work with requires_equals=True."""

    @app.default
    def main(*, name: Annotated[str, Parameter(requires_equals=True)]):
        pass

    assert_parse_args(main, "--name=alice", name="alice")


def test_requires_equals_space_separated_rejected(app):
    """--option value should be rejected with requires_equals=True."""

    @app.default
    def main(*, name: Annotated[str, Parameter(requires_equals=True)]):
        pass

    with pytest.raises(RequiresEqualsError):
        app.parse_args("--name alice", print_error=False, exit_on_error=False)


def test_requires_equals_missing_value(app):
    """--option with no value at all should be rejected with requires_equals=True."""

    @app.default
    def main(*, name: Annotated[str, Parameter(requires_equals=True)]):
        pass

    with pytest.raises(RequiresEqualsError):
        app.parse_args("--name", print_error=False, exit_on_error=False)


def test_requires_equals_boolean_flag_unaffected(app, assert_parse_args):
    """Boolean flags should work regardless of requires_equals."""

    @app.default
    def main(*, verbose: Annotated[bool, Parameter(requires_equals=True)] = False):
        pass

    assert_parse_args(main, "--verbose", verbose=True)


def test_requires_equals_short_option_unaffected(app, assert_parse_args):
    """Short options (-o value) should not be affected by requires_equals."""

    @app.default
    def main(*, name: Annotated[str, Parameter(name=["-n", "--name"], requires_equals=True)]):
        pass

    assert_parse_args(main, "-n alice", name="alice")


def test_requires_equals_short_option_long_rejected(app):
    """The long form should still be rejected when using space separation."""

    @app.default
    def main(*, name: Annotated[str, Parameter(name=["-n", "--name"], requires_equals=True)]):
        pass

    with pytest.raises(RequiresEqualsError):
        app.parse_args("--name alice", print_error=False, exit_on_error=False)


def test_requires_equals_default_false(app, assert_parse_args):
    """Default behavior (requires_equals=False) should accept space-separated."""

    @app.default
    def main(*, name: str):
        pass

    assert_parse_args(main, "--name alice", name="alice")
    assert_parse_args(main, "--name=alice", name="alice")


def test_requires_equals_app_default_parameter():
    """App-wide default_parameter should apply requires_equals to all params."""
    app = cyclopts.App(
        result_action="return_value",
        default_parameter=Parameter(requires_equals=True),
    )

    @app.default
    def main(*, name: str, count: int):
        pass

    _, bound, _ = app.parse_args("--name=alice --count=3", print_error=False, exit_on_error=False)
    assert bound.arguments == {"name": "alice", "count": 3}


def test_requires_equals_app_default_parameter_rejects_space():
    """App-wide requires_equals should reject space-separated values."""
    app = cyclopts.App(
        result_action="return_value",
        default_parameter=Parameter(requires_equals=True),
    )

    @app.default
    def main(*, name: str, count: int):
        pass

    with pytest.raises(RequiresEqualsError):
        app.parse_args("--name alice --count=3", print_error=False, exit_on_error=False)


def test_requires_equals_error_message(app):
    """Error message should recommend using = syntax."""

    @app.default
    def main(*, name: Annotated[str, Parameter(requires_equals=True)]):
        pass

    with pytest.raises(RequiresEqualsError, match=r'Use "--name=VALUE"'):
        app.parse_args("--name alice", print_error=False, exit_on_error=False)


def test_requires_equals_mixed_parameters(app, assert_parse_args):
    """Mix of requires_equals=True and default parameters."""

    @app.default
    def main(
        *,
        strict: Annotated[str, Parameter(requires_equals=True)],
        loose: str,
    ):
        pass

    assert_parse_args(main, "--strict=hello --loose world", strict="hello", loose="world")


def test_requires_equals_mixed_parameters_reject(app):
    """requires_equals only applies to the parameter it's set on."""

    @app.default
    def main(
        *,
        strict: Annotated[str, Parameter(requires_equals=True)],
        loose: str,
    ):
        pass

    with pytest.raises(RequiresEqualsError):
        app.parse_args("--strict hello --loose world", print_error=False, exit_on_error=False)


def test_requires_equals_takes_priority_over_consume_multiple(app):
    """requires_equals takes priority over consume_multiple; space-separated values are rejected."""

    @app.default
    def main(*, urls: Annotated[list[str], Parameter(requires_equals=True, consume_multiple=True)]):
        pass

    with pytest.raises(RequiresEqualsError):
        app.parse_args("--urls a b c", print_error=False, exit_on_error=False)


def test_requires_equals_consume_multiple_repeated_equals(app):
    """With requires_equals, list values can be provided by repeating --option=value."""

    @app.default
    def main(*, urls: Annotated[list[str], Parameter(requires_equals=True)]):
        pass

    _, bound, _ = app.parse_args("--urls=a --urls=b --urls=c", print_error=False, exit_on_error=False)
    assert bound.arguments == {"urls": ["a", "b", "c"]}
