from dataclasses import dataclass
from typing import Annotated
from unittest.mock import Mock

import pytest

from cyclopts import Parameter, ValidationError
from cyclopts.exceptions import CoercionError
from cyclopts.token import Token


@pytest.fixture
def validator():
    return Mock()


def test_custom_converter(app, assert_parse_args):
    def custom_converter(type_, tokens):
        return 2 * int(tokens[0].value)

    @app.default
    def foo(age: Annotated[int, Parameter(converter=custom_converter)]):
        pass

    assert_parse_args(foo, "5", age=10)


def test_custom_converter_dict(app, assert_parse_args):
    def custom_converter(type_, tokens):
        return {k: 2 * int(v[0].value) for k, v in tokens.items()}

    @app.default
    def foo(*, color: Annotated[dict[str, int], Parameter(converter=custom_converter)]):
        pass

    assert_parse_args(foo, "--color.red 5 --color.green 10", color={"red": 10, "green": 20})


def test_custom_converter_user_value_error_single_token(app):
    def custom_converter(type_, tokens):
        raise ValueError

    @app.default
    def foo(age: Annotated[int, Parameter(converter=custom_converter)]):
        pass

    with pytest.raises(CoercionError) as e:
        app("5", exit_on_error=False)
    assert str(e.value) == 'Invalid value for AGE: unable to convert "5" into int.'


def test_custom_converter_user_value_error_multi_token(app):
    def custom_converter(type_, tokens):
        raise ValueError

    @app.default
    def foo(age: Annotated[tuple[int, int], Parameter(converter=custom_converter)]):
        pass

    with pytest.raises(CoercionError) as e:
        app("5 6", exit_on_error=False)
    assert str(e.value) == "Invalid value for --age: unable to convert value to tuple[int, int]."


def test_custom_converter_user_value_error_with_message(app):
    def custom_converter(type_, tokens):
        raise ValueError("Some user-provided message.")

    @app.default
    def foo(age: Annotated[int, Parameter(converter=custom_converter)]):
        pass

    with pytest.raises(CoercionError) as e:
        app("5", exit_on_error=False)
    assert str(e.value) == "Some user-provided message."


def test_custom_converter_user_kwargs_error(app):
    def custom_converter(type_, tokens):
        raise ValueError

    @app.default
    def foo(**kwargs: Annotated[int, Parameter(converter=custom_converter)]):
        pass

    with pytest.raises(CoercionError) as e:
        app("--foo 5", exit_on_error=False)
    assert str(e.value) == 'Invalid value for --foo: unable to convert "5" into int.'


def test_custom_converter_user_kwargs_error_with_message(app):
    def custom_converter(type_, tokens):
        raise ValueError("Some user-provided message.")

    @app.default
    def foo(**kwargs: Annotated[int, Parameter(converter=custom_converter)]):
        pass

    with pytest.raises(CoercionError) as e:
        app("--foo 5", exit_on_error=False)
    assert str(e.value) == "Invalid value for --foo: Some user-provided message."


def test_custom_validator_positional_or_keyword(app, assert_parse_args, validator):
    @app.default
    def foo(age: Annotated[int, Parameter(validator=validator)]):
        pass

    assert_parse_args(foo, "10", age=10)
    validator.assert_called_once_with(int, 10)


def test_custom_validator_var_keyword(app, assert_parse_args, validator):
    @app.default
    def foo(**age: Annotated[int, Parameter(validator=validator)]):
        pass

    assert_parse_args(foo, "--age=10", age=10)
    validator.assert_called_once_with(int, 10)


def test_custom_validator_var_positional(app, assert_parse_args, validator):
    @app.default
    def foo(*age: Annotated[int, Parameter(validator=validator)]):
        pass

    assert_parse_args(foo, "10", 10)
    validator.assert_called_once_with(int, 10)


def test_custom_validators(app, assert_parse_args):
    def lower_bound(type_, value):
        if value <= 0:
            raise ValueError("An unreasonable age was entered.")

    def upper_bound(type_, value):
        if value > 150:
            raise ValueError("An unreasonable age was entered.")

    @app.default
    def foo(age: Annotated[int, Parameter(validator=[lower_bound, upper_bound])]):
        pass

    assert_parse_args(foo, "10", 10)

    with pytest.raises(ValidationError):
        app.parse_args("0", print_error=False, exit_on_error=False)

    with pytest.raises(ValidationError):
        app.parse_args("200", print_error=False, exit_on_error=False)


def test_custom_converter_and_validator(app, assert_parse_args, validator):
    def custom_validator(type_, value):
        if not (0 < value < 150):
            raise ValueError("An unreasonable age was entered.")

    def custom_converter(type_, tokens):
        return 2 * int(tokens[0].value)

    @app.default
    def foo(age: Annotated[int, Parameter(converter=custom_converter, validator=validator)]):
        pass

    assert_parse_args(foo, "5", 10)

    validator.assert_called_once_with(int, 10)


def test_custom_validator_on_default_signature_value(app, validator):
    @app.default
    def foo(age: Annotated[int, Parameter(validator=validator)] = -1):
        pass

    app.parse_args("", print_error=False, exit_on_error=False)
    validator.assert_called_once_with(int, -1)


def test_custom_command_validator(app, assert_parse_args):
    validator = Mock()

    @app.default(validator=validator)
    def foo(a: int, b: int, c: int):
        pass

    assert_parse_args(foo, "1 2 3", 1, 2, 3)
    validator.assert_called_once_with(a=1, b=2, c=3)


def test_custom_converter_inside_class(app, mocker):
    converter = mocker.Mock(return_value=5)

    @Parameter(name="*")
    @dataclass
    class Config:
        foo: Annotated[int, Parameter(converter=converter)]

    @app.default
    def default(config: Config):
        pass

    app("bar")

    converter.assert_called_once_with(int, (Token(value="bar", source="cli"),))


def test_classmethod_validator_string_reference(app, assert_parse_args):
    """String reference to a classmethod validator on a Parameter-decorated class."""

    @Parameter(name="*", validator="validate")
    @dataclass
    class TextStyle:
        color: str
        bold: bool = False
        italic: bool = False

        @classmethod
        def validate(cls, value):
            if value.bold and value.italic:
                raise ValueError("Cannot use both --bold and --italic together.")

    @app.default
    def main(style: TextStyle):
        pass

    assert_parse_args(main, "--color red --bold", style=TextStyle(color="red", bold=True))

    with pytest.raises(ValidationError):
        app.parse_args("--color red --bold --italic", print_error=False, exit_on_error=False)


def test_classmethod_validator_direct_reference(app, assert_parse_args):
    """Direct classmethod reference exercises the inspect.ismethod branch."""

    @dataclass
    class TextStyle:
        color: str
        bold: bool = False
        italic: bool = False

        @classmethod
        def validate(cls, value):
            if value.bold and value.italic:
                raise ValueError("Cannot use both --bold and --italic together.")

    @app.default
    def main(style: Annotated[TextStyle, Parameter(name="*", validator=TextStyle.validate)]):
        pass

    assert_parse_args(main, "--color red --bold", style=TextStyle(color="red", bold=True))

    with pytest.raises(ValidationError):
        app.parse_args("--color red --bold --italic", print_error=False, exit_on_error=False)


def test_staticmethod_validator_string_reference(app, assert_parse_args):
    """Staticmethods follow the (type_, value) calling convention."""
    seen = {}

    @Parameter(name="*", validator="validate")
    @dataclass
    class TextStyle:
        color: str
        bold: bool = False

        @staticmethod
        def validate(type_, value):
            seen["type_"] = type_
            seen["value"] = value
            if value.color == "invalid":
                raise ValueError("bad color")

    @app.default
    def main(style: TextStyle):
        pass

    assert_parse_args(main, "--color red --bold", style=TextStyle(color="red", bold=True))
    assert seen["type_"] is TextStyle
    assert seen["value"] == TextStyle(color="red", bold=True)


def test_staticmethod_validator_direct_reference(app, assert_parse_args):
    """Direct staticmethod reference."""

    @dataclass
    class TextStyle:
        color: str

        @staticmethod
        def validate(type_, value):
            if value.color == "invalid":
                raise ValueError("bad color")

    @app.default
    def main(style: Annotated[TextStyle, Parameter(name="*", validator=TextStyle.validate)]):
        pass

    assert_parse_args(main, "--color red", style=TextStyle(color="red"))

    with pytest.raises(ValidationError):
        app.parse_args("--color invalid", print_error=False, exit_on_error=False)


def test_validator_string_reference_in_list(app, assert_parse_args):
    """Strings can be intermixed with callables in a validator list."""
    external_calls = []

    def external(type_, value):
        external_calls.append(value)

    @Parameter(name="*", validator=["validate_a", external, "validate_b"])
    @dataclass
    class Config:
        n: int

        @classmethod
        def validate_a(cls, value):
            if value.n < 0:
                raise ValueError("n must be >= 0")

        @classmethod
        def validate_b(cls, value):
            if value.n > 100:
                raise ValueError("n must be <= 100")

    @app.default
    def main(config: Config):
        pass

    assert_parse_args(main, "--n 5", config=Config(n=5))
    assert external_calls == [Config(n=5)]

    with pytest.raises(ValidationError):
        app.parse_args("--n -1", print_error=False, exit_on_error=False)

    with pytest.raises(ValidationError):
        app.parse_args("--n 200", print_error=False, exit_on_error=False)


def test_classmethod_validator_string_reference_nested_annotated(app, assert_parse_args):
    """String validator on a nested Annotated type triggers the ``_convert`` validator path."""
    seen = []

    class Score(int):
        @classmethod
        def validate(cls, value):
            seen.append(value)
            if value > 100:
                raise ValueError("score too high")

    Validated = Annotated[Score, Parameter(validator="validate")]

    @app.default
    def main(scores: tuple[Validated, Validated]):  # pyright: ignore[reportInvalidTypeForm]
        pass

    assert_parse_args(main, "10 20", scores=(Score(10), Score(20)))
    assert seen == [10, 20]

    with pytest.raises(ValidationError):
        app.parse_args("10 200", print_error=False, exit_on_error=False)


def test_staticmethod_validator_string_reference_nested_annotated(app, assert_parse_args):
    """Staticmethod string validator on a nested Annotated follows the ``(type_, value)`` calling convention in ``_convert``."""
    seen = []

    class Score(int):
        @staticmethod
        def validate(type_, value):
            seen.append((type_, value))
            if value > 100:
                raise ValueError("score too high")

    Validated = Annotated[Score, Parameter(validator="validate")]

    @app.default
    def main(scores: tuple[Validated, Validated]):  # pyright: ignore[reportInvalidTypeForm]
        pass

    assert_parse_args(main, "10 20", scores=(Score(10), Score(20)))
    assert seen == [(Score, 10), (Score, 20)]


def test_classmethod_validator_string_reference_var_keyword(app, assert_parse_args):
    """String validator with ``**kwargs`` exercises the ``VAR_KEYWORD`` branch in ``Argument.validate``."""
    seen = []

    class Bounded(int):
        @classmethod
        def validate(cls, value):
            seen.append(value)
            if value < 0:
                raise ValueError("must be non-negative")

    @app.default
    def main(**vals: Annotated[Bounded, Parameter(validator="validate")]):
        pass

    assert_parse_args(main, "--a=1 --b=2", a=Bounded(1), b=Bounded(2))
    assert sorted(seen) == [1, 2]

    with pytest.raises(ValidationError):
        app.parse_args("--a=-1", print_error=False, exit_on_error=False)


def test_staticmethod_validator_string_reference_var_keyword(app, assert_parse_args):
    """Staticmethod string validator with ``**kwargs`` uses ``(type_, value)`` calling convention."""
    seen = []

    class Bounded(int):
        @staticmethod
        def validate(type_, value):
            seen.append((type_, value))

    @app.default
    def main(**vals: Annotated[Bounded, Parameter(validator="validate")]):
        pass

    assert_parse_args(main, "--a=1 --b=2", a=Bounded(1), b=Bounded(2))
    assert sorted(seen) == [(Bounded, 1), (Bounded, 2)]


def test_classmethod_validator_string_reference_var_positional(app, assert_parse_args):
    """String validator with ``*args`` exercises the ``VAR_POSITIONAL`` branch in ``Argument.validate``."""
    seen = []

    class Bounded(int):
        @classmethod
        def validate(cls, value):
            seen.append(value)
            if value < 0:
                raise ValueError("must be non-negative")

    @app.default
    def main(*vals: Annotated[Bounded, Parameter(validator="validate")]):
        pass

    assert_parse_args(main, "1 2 3", Bounded(1), Bounded(2), Bounded(3))
    assert seen == [1, 2, 3]

    with pytest.raises(ValidationError):
        app.parse_args("1 -1", print_error=False, exit_on_error=False)


def test_staticmethod_validator_string_reference_var_positional(app, assert_parse_args):
    """Staticmethod string validator with ``*args`` uses ``(type_, value)`` calling convention."""
    seen = []

    class Bounded(int):
        @staticmethod
        def validate(type_, value):
            seen.append((type_, value))

    @app.default
    def main(*vals: Annotated[Bounded, Parameter(validator="validate")]):
        pass

    assert_parse_args(main, "1 2", Bounded(1), Bounded(2))
    assert seen == [(Bounded, 1), (Bounded, 2)]
