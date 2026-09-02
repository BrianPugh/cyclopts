"""Tests for ``Parameter.choices`` -- an explicit choice-set override that is
decoupled from the annotated type (see issue #886).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Literal

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import CoercionError


@dataclass
class MyClass:
    inner: str


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


_LOOKUP = {"a": MyClass("z"), "b": MyClass("y"), "c": MyClass("x")}


def _lookup_converter(type_, tokens):
    return _LOOKUP[tokens[0].value]


def test_choices_display_overrides_hint(app, console):
    """``choices`` renders in --help even when the hint yields no choices."""

    @app.default
    def foo(
        my_flag: Annotated[
            MyClass,
            Parameter(accepts_keys=False, converter=_lookup_converter, choices=tuple(_LOOKUP)),
        ] = _LOOKUP["a"],
    ):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)
    assert "[choices: a, b, c]" in capture.get()


def test_choices_display_replaces_literal_choices(app, console):
    """An explicit ``choices`` takes precedence over Literal-derived choices."""

    @app.default
    def foo(region: Annotated[Literal["us", "ca"], Parameter(choices=["x", "y", "z"])] = "us"):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)
    actual = capture.get()
    assert "[choices: x, y, z]" in actual
    assert "us" not in actual.split("[choices")[1].split("]")[0]


def test_choices_valid_value_runs_converter(app, assert_parse_args):
    """A valid choice flows through the converter to the internal type."""

    @app.default
    def foo(
        my_flag: Annotated[
            MyClass,
            Parameter(accepts_keys=False, converter=_lookup_converter, choices=tuple(_LOOKUP)),
        ] = _LOOKUP["a"],
    ):
        pass

    assert_parse_args(foo, "b", MyClass("y"))


def test_choices_invalid_value_raises_before_converter(app):
    """An invalid choice raises the standard 'Choose from' error, not a
    converter-internal exception (here a ``KeyError`` on the dict lookup).
    """

    @app.default
    def foo(
        my_flag: Annotated[
            MyClass,
            Parameter(accepts_keys=False, converter=_lookup_converter, choices=tuple(_LOOKUP)),
        ] = _LOOKUP["a"],
    ):
        pass

    with pytest.raises(CoercionError) as e:
        app("d", exit_on_error=False)
    message = str(e.value)
    assert 'Invalid value "d"' in message
    assert 'Choose from: "a", "b", "c".' in message


def test_choices_did_you_mean_suggestion(app):
    @app.default
    def foo(env: Annotated[str, Parameter(choices=["dev", "staging", "prod"])] = "dev"):
        pass

    with pytest.raises(CoercionError) as e:
        app("--env prad", exit_on_error=False)
    assert 'Did you mean "prod"?' in str(e.value)


def test_choices_standalone_on_str(app, assert_parse_args):
    """``choices`` is useful without a converter: constrain a plain ``str``."""

    @app.default
    def foo(env: Annotated[str, Parameter(choices=["dev", "prod"])] = "dev"):
        pass

    assert_parse_args(foo, "--env prod", env="prod")
    with pytest.raises(CoercionError):
        app("--env nope", exit_on_error=False)


def test_choices_validates_each_list_element(app):
    @app.default
    def foo(envs: Annotated[list[str], Parameter(choices=["dev", "prod"])]):
        pass

    with pytest.raises(CoercionError) as e:
        app("--envs dev --envs nope", exit_on_error=False)
    assert 'Invalid value "nope"' in str(e.value)


def test_choices_default_not_validated(app, assert_parse_args):
    """The (internal-type) default bypasses choice validation."""

    @app.default
    def foo(
        my_flag: Annotated[
            MyClass,
            Parameter(accepts_keys=False, converter=_lookup_converter, choices=tuple(_LOOKUP)),
        ] = _LOOKUP["a"],
    ):
        pass

    # No token supplied -> parsing succeeds without validating the (internal-type,
    # non-member) default; the signature default is applied by Python at call time.
    assert_parse_args(foo, "")


def test_choices_completion_force(app):
    """Shell completion always receives the choices, even with show_choices=False."""
    from cyclopts.argument import ArgumentCollection

    @app.default
    def foo(env: Annotated[str, Parameter(choices=["dev", "prod"], show_choices=False)] = "dev"):
        pass

    (argument,) = [a for a in ArgumentCollection._from_callable(foo) if a.name == "--env"]
    assert argument.get_choices() is None  # suppressed on the help page
    assert argument.get_choices(force=True) == ("dev", "prod")  # still offered to completion


@pytest.mark.parametrize(
    "choices",
    [
        Literal["a", "b", "c"],  # Literal
        Literal["a", "b"] | Literal["c"],  # union of Literals
        ("a", "b", "c"),  # plain strings
    ],
)
def test_choices_accepts_type_hints(choices):
    """``choices`` accepts a type hint and resolves it like hint-derived choices."""
    assert Parameter(choices=choices).choices == ("a", "b", "c")


def test_choices_accepts_enum_uses_transformed_member_names():
    """An Enum resolves to its (name-transformed) member names, matching how an
    Enum-annotated parameter displays.
    """
    assert Parameter(choices=Color).choices == ("red", "green", "blue")


def test_choices_literal_display_and_validation(app, console):
    @app.default
    def foo(env: Annotated[str, Parameter(choices=Literal["dev", "prod"])] = "dev"):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)
    assert "[choices: dev, prod]" in capture.get()

    with pytest.raises(CoercionError) as e:
        app("--env nope", exit_on_error=False)
    assert 'Choose from: "dev", "prod".' in str(e.value)


def test_choices_combine_precedence():
    """A downstream ``choices`` overrides an upstream one; unset does not clobber."""
    upstream = Parameter(choices=["a", "b"])
    assert Parameter.combine(upstream, Parameter(help="x")).choices == ("a", "b")
    assert Parameter.combine(upstream, Parameter(choices=["c"])).choices == ("c",)
