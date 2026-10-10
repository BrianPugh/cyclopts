import pytest


@pytest.mark.parametrize(
    "type_",
    [
        dict[str, str],
        dict,
        dict,
    ],
)
def test_bind_dict_str_to_str(app, assert_parse_args, type_):
    @app.command
    def foo(d: type_):  # pyright: ignore
        pass

    assert_parse_args(foo, "foo --d.key_1='val1' --d.key-2='val2'", d={"key_1": "val1", "key-2": "val2"})


def test_bind_dict_str_to_int_typing(app, assert_parse_args):
    @app.command
    def foo(d: dict[str, int]):
        pass

    assert_parse_args(foo, "foo --d.key1=7 --d.key2=42", d={"key1": 7, "key2": 42})


def test_bind_dict_str_to_int_builtin(app, assert_parse_args):
    @app.command
    def foo(d: dict[str, int]):
        pass

    assert_parse_args(foo, "foo --d.key1=7 --d.key2=42", d={"key1": 7, "key2": 42})


def test_bind_dict_with_mixed_keys_and_regular_params(app, assert_parse_args):
    """Test that dict parameters with keys work alongside regular parameters."""

    @app.command
    def foo(name: str, config: dict[str, int], count: int):
        pass

    assert_parse_args(
        foo,
        "foo --name=test --config.key1=7 --config.key2=42 --count=3",
        name="test",
        config={"key1": 7, "key2": 42},
        count=3,
    )


def test_bind_dict_value_type_validator(app):
    """A ``dict`` value type's ``Parameter`` validator is honored.

    Every other container honors element-level ``Parameter`` metadata; ``dict``
    used to silently discard it.
    """
    from cyclopts.exceptions import ValidationError
    from cyclopts.types import PositiveInt

    @app.command
    def foo(d: dict[str, PositiveInt]):
        return d

    assert app("foo --d.a=5", exit_on_error=False, result_action="return_value") == {"a": 5}

    with pytest.raises(ValidationError):
        app("foo --d.a=-5", exit_on_error=False, result_action="return_value")


def test_bind_dict_value_type_converter(app):
    """A ``dict`` value type's ``Parameter`` converter is honored."""
    from typing import Annotated

    from cyclopts import Parameter

    def upper_converter(type_, tokens):
        return tokens[0].value.upper()

    @app.command
    def foo(d: dict[str, Annotated[str, Parameter(converter=upper_converter)]]):
        return d

    assert app("foo --d.a=xyz", exit_on_error=False, result_action="return_value") == {"a": "XYZ"}


def test_bind_dict_value_type_validator_nested_in_dataclass(app):
    from dataclasses import dataclass

    from cyclopts.exceptions import ValidationError
    from cyclopts.types import PositiveInt

    @dataclass
    class Config:
        d: dict[str, PositiveInt]

    @app.command
    def foo(config: Config):
        return config

    with pytest.raises(ValidationError):
        app("foo --config.d.a=-5", exit_on_error=False, result_action="return_value")


@pytest.mark.parametrize(
    "cmd_str, expected",
    [
        ('--d=\'{"a": 1, "b": 2}\'', {"a": 1, "b": 2}),
        ("--d={}", {}),
    ],
)
def test_bind_dict_from_cli_json(app, assert_parse_args, cmd_str, expected):
    @app.default
    def main(d: dict[str, int]):
        pass

    assert_parse_args(main, cmd_str, d=expected)


def test_bind_dict_field_from_cli_json(app, assert_parse_args):
    from dataclasses import dataclass, field

    @dataclass
    class Options:
        mapping: dict[str, int] = field(default_factory=dict)

    @app.default
    def main(options: Options):
        pass

    assert_parse_args(main, "--options.mapping='{\"a\": 1}'", options=Options(mapping={"a": 1}))


def test_bind_dict_from_env_json(app, assert_parse_args, monkeypatch):
    from typing import Annotated

    from cyclopts import Parameter

    @app.default
    def main(d: Annotated[dict[str, int], Parameter(env_var="D")]):
        pass

    monkeypatch.setenv("D", '{"a": 1}')
    assert_parse_args(main, "", d={"a": 1})
