"""Tests for ``Parameter.choices`` -- an explicit choice-set override that is
decoupled from the annotated type (see issue #886).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Literal, Optional

import pytest
from pydantic import BaseModel

from cyclopts import Parameter
from cyclopts.argument import ArgumentCollection
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

    assert_parse_args(foo, "")


def test_choices_completion_force(app):
    """Shell completion always receives the choices, even with show_choices=False."""

    @app.default
    def foo(env: Annotated[str, Parameter(choices=["dev", "prod"], show_choices=False)] = "dev"):
        pass

    (argument,) = [a for a in ArgumentCollection._from_callable(foo) if a.name == "--env"]
    assert argument.get_choices() is None
    assert argument.get_choices(force=True) == ("dev", "prod")


def _argument(func, name):
    (argument,) = [a for a in ArgumentCollection._from_callable(func) if a.name == name]
    return argument


@pytest.mark.parametrize(
    "choices",
    [
        Literal["a", "b", "c"],
        Literal["a", "b"] | Literal["c"],
        ("a", "b", "c"),
    ],
)
def test_choices_accepts_type_hints(choices):
    """``choices`` accepts a type hint and resolves it like hint-derived choices."""

    def foo(x: Annotated[str, Parameter(choices=choices)]):
        pass

    assert _argument(foo, "--x").get_choices() == ("a", "b", "c")


def test_choices_enum_uses_name_transform():
    """An Enum resolves to member names via the parameter's ``name_transform``."""

    def foo(
        color: Annotated[Color, Parameter(choices=Color)],
        loud: Annotated[Color, Parameter(choices=Color, name_transform=str.upper)],
    ):
        pass

    assert _argument(foo, "--color").get_choices() == ("red", "green", "blue")
    assert _argument(foo, "--LOUD").get_choices() == ("RED", "GREEN", "BLUE")


@pytest.mark.parametrize("choices", [Color, Optional[Color], ("red", "green", "blue")])
def test_choices_enum_validation_normalizes_like_converter(app, assert_parse_args, choices):
    """Whenever an Enum is involved (in ``choices`` or the hint), matching follows ``get_enum_member``."""

    @app.default
    def foo(color: Annotated[Color, Parameter(choices=choices)]):
        pass

    assert_parse_args(foo, "--color RED", Color.RED)


def test_choices_enum_converter_receives_listed_spelling(app, assert_parse_args):
    seen = []

    def converter(type_, tokens):
        seen.append(tokens[0].value)
        return tokens[0].value

    @app.default
    def foo(color: Annotated[str, Parameter(choices=Color, converter=converter)]):
        pass

    assert_parse_args(foo, "--color RED", "red")
    assert seen == ["red"]


class EmptyEnum(Enum):
    pass


@pytest.mark.parametrize("choices", [str, list[str], [1, 2], 3, EmptyEnum, (), []])
def test_choices_rejects_non_string_values(choices):
    with pytest.raises(TypeError):
        Parameter(choices=choices)


def test_choices_json_list_expanded_before_validation(app, assert_parse_args):
    @app.default
    def foo(envs: Annotated[list[str], Parameter(choices=["dev", "prod"], json_list=True)]):
        pass

    assert_parse_args(foo, ["--envs", '["dev", "prod"]'], ["dev", "prod"])
    with pytest.raises(CoercionError):
        app(["--envs", '["dev", "nope"]'], exit_on_error=False)


@dataclass
class Cfg:
    name: str


class Model(BaseModel):
    mode: Annotated[str, Parameter(choices=("a", "b"))] = "a"


class EnumModel(BaseModel):
    color: Annotated[Color, Parameter(choices=Color)]


@pytest.mark.parametrize("hint", [Cfg, tuple[str, int], bool])
def test_choices_unsupported_hint_raises_at_definition(hint):
    def foo(x: Annotated[hint, Parameter(choices=["a", "b"])]):  # pyright: ignore[reportInvalidTypeForm]
        pass

    with pytest.raises(ValueError, match="single-token"):
        ArgumentCollection._from_callable(foo)


def test_choices_enforced_for_pydantic_field(app, assert_parse_args):
    @app.default
    def foo(m: Model):
        pass

    assert_parse_args(foo, "--m.mode b", Model(mode="b"))
    with pytest.raises(CoercionError) as e:
        app("--m.mode bad", exit_on_error=False)
    assert 'Choose from: "a", "b".' in str(e.value)


def test_choices_canonical_spelling_reaches_pydantic_enum(app, assert_parse_args):
    """The listed spelling (``RED`` -> ``red``) must survive to pydantic, not the raw input.

    ``_validate_choices`` normalizes ``RED`` to the listed ``red`` before conversion; the
    pydantic path must persist that rewrite, otherwise pydantic sees ``RED`` and rejects it.
    """

    @app.default
    def foo(m: EnumModel):
        pass

    assert_parse_args(foo, "--m.color RED", EnumModel(color=Color.RED))
    assert_parse_args(foo, "--m.color green", EnumModel(color=Color.GREEN))
    with pytest.raises(CoercionError) as e:
        app("--m.color purple", exit_on_error=False)
    assert 'Choose from: "red", "green", "blue".' in str(e.value)


def test_choices_enforced_for_dict_values(app, assert_parse_args):
    @app.default
    def foo(x: Annotated[dict[str, str], Parameter(choices=["a", "b"])]):
        pass

    assert_parse_args(foo, "--x.k a", {"k": "a"})
    with pytest.raises(CoercionError):
        app("--x.k bad", exit_on_error=False)


def test_choices_enforced_for_var_keyword(app, assert_parse_args):
    @app.default
    def foo(**kwargs: Annotated[str, Parameter(choices=["a", "b"])]):
        pass

    assert_parse_args(foo, "--foo a", foo="a")
    with pytest.raises(CoercionError):
        app("--foo bad", exit_on_error=False)


def test_choices_converter_error_not_reported_as_bad_choice(app):
    """A converter failure on a *valid* choice gets the normal conversion error."""

    def bad(type_, tokens):
        raise ValueError

    @app.default
    def foo(env: Annotated[str, Parameter(choices=["dev"], converter=bad)]):
        pass

    with pytest.raises(CoercionError) as e:
        app("--env dev", exit_on_error=False)
    assert "Choose from" not in str(e.value)


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
