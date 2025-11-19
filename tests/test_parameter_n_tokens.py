"""Tests for Parameter.n_tokens feature (issue #646)."""

from typing import Annotated

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import MissingArgumentError


def test_n_tokens_basic_custom_converter(app, assert_parse_args):
    """Test n_tokens=1 with custom converter that loads a complex type from a single token."""

    class ComplexType:
        """A type that normally requires multiple tokens but can be loaded from a file."""

        def __init__(self, name: str, value: int):
            self.name = name
            self.value = value

        def __eq__(self, other):
            return self.name == other.name and self.value == other.value

    def load_from_id(type_, tokens):
        """Custom converter that loads ComplexType from a single ID token."""
        id_value = tokens[0].value
        # Simulate loading from database/file based on ID
        return ComplexType(name=f"loaded_{id_value}", value=int(id_value) * 100)

    @app.default
    def foo(obj: Annotated[ComplexType, Parameter(n_tokens=1, converter=load_from_id, accepts_keys=False)]):
        pass

    assert_parse_args(foo, "5", obj=ComplexType(name="loaded_5", value=500))


def test_n_tokens_two_tokens(app, assert_parse_args):
    """Test n_tokens=2 with custom converter."""

    def combine_tokens(type_, tokens):
        """Custom converter that combines two tokens."""
        return f"{tokens[0].value}:{tokens[1].value}"

    @app.default
    def foo(*, value: Annotated[str, Parameter(n_tokens=2, converter=combine_tokens)]):
        pass

    assert_parse_args(foo, "--value hello world", value="hello:world")


def test_n_tokens_consume_all(app, assert_parse_args):
    """Test n_tokens=-1 to consume all remaining tokens."""

    def join_all(type_, tokens):
        """Custom converter that joins all tokens."""
        return " ".join(t.value for t in tokens)

    @app.default
    def foo(*, msg: Annotated[str, Parameter(n_tokens=-1, consume_multiple=True, converter=join_all)]):
        pass

    assert_parse_args(foo, "--msg hello world from cyclopts", msg="hello world from cyclopts")


def test_n_tokens_var_positional(app, assert_parse_args):
    """Test n_tokens with *args to verify per-element behavior."""

    def pair_converter(type_, tokens):
        """Convert two tokens into a tuple."""
        return (tokens[0].value, int(tokens[1].value))

    @app.default
    def foo(*pairs: Annotated[tuple[str, int], Parameter(n_tokens=2, converter=pair_converter)]):
        pass

    assert_parse_args(foo, "alice 10 bob 20 charlie 30", ("alice", 10), ("bob", 20), ("charlie", 30))


def test_n_tokens_without_converter(app, assert_parse_args):
    """Test n_tokens works without custom converter (though, a bit non-sensical)."""

    @app.default
    def foo(*, values: Annotated[tuple[int, int], Parameter(n_tokens=2)]):
        pass

    assert_parse_args(foo, "--values 10 20", values=(10, 20))


def test_n_tokens_error_message(app):
    """Test that error messages reflect custom n_tokens."""

    def failing_converter(type_, tokens):
        """Converter that expects 2 tokens."""
        return int(tokens[0].value) + int(tokens[1].value)

    @app.default
    def foo(*, value: Annotated[int, Parameter(n_tokens=2, converter=failing_converter)]):
        return value

    # Provide only 1 token when 2 are expected
    with pytest.raises(MissingArgumentError) as exc_info:
        app("--value 10", exit_on_error=False)

    # The error should mention that 2 tokens are required
    assert "2" in str(exc_info.value)


def test_n_tokens_accepts_keys_false(app, assert_parse_args):
    """Test n_tokens with accepts_keys=False."""

    class Config:
        """A config type that would normally have sub-keys."""

        def __init__(self, host: str, port: int):
            self.host = host
            self.port = port

        def __eq__(self, other):
            return self.host == other.host and self.port == other.port

    def load_config(type_, tokens):
        """Load config from a file path."""
        # Simulate loading from a file
        filepath = tokens[0].value
        if filepath == "prod.conf":
            return Config("prod.example.com", 443)
        else:
            return Config("dev.example.com", 8080)

    @app.default
    def foo(*, config: Annotated[Config, Parameter(n_tokens=1, converter=load_config, accepts_keys=False)]):
        pass

    assert_parse_args(foo, "--config prod.conf", config=Config("prod.example.com", 443))


def test_n_tokens_with_iterable_type(app, assert_parse_args):
    """Test n_tokens with list type to override default consume-all behavior."""

    def limited_list_converter(type_, tokens):
        """Convert exactly 3 tokens into a list."""
        return [int(t.value) for t in tokens]

    @app.default
    def foo(*, values: Annotated[list[int], Parameter(n_tokens=3, converter=limited_list_converter)]):
        pass

    assert_parse_args(foo, "--values 10 20 30", values=[10, 20, 30])


def test_n_tokens_positional_arg(app, assert_parse_args):
    """Test n_tokens with positional arguments."""

    def pair_converter(type_, tokens):
        """Convert two tokens into a string."""
        return f"{tokens[0].value}-{tokens[1].value}"

    @app.default
    def foo(pair: Annotated[str, Parameter(n_tokens=2, converter=pair_converter)]):
        pass

    assert_parse_args(foo, "hello world", pair="hello-world")


def test_n_tokens_kwargs(app, assert_parse_args):
    """Test n_tokens with **kwargs - each value should consume n_tokens."""

    def pair_converter(type_, tokens):
        """Combine two tokens with a dash."""
        return f"{tokens[0].value}-{tokens[1].value}"

    @app.default
    def foo(**kwargs: Annotated[str, Parameter(n_tokens=2, converter=pair_converter)]):
        pass

    assert_parse_args(foo, "--key1 a b --key2 c d", key1="a-b", key2="c-d")


def test_n_tokens_dict_type(app, assert_parse_args):
    """Test n_tokens with dict type - each value should consume n_tokens."""

    def dict_converter(type_, tokens):
        """Convert dict where each value is 2 tokens combined."""
        result = {}
        for key, token_list in tokens.items():
            # Each value should have 2 tokens
            result[key] = f"{token_list[0].value}:{token_list[1].value}"
        return result

    @app.default
    def foo(*, config: Annotated[dict[str, str], Parameter(n_tokens=2, converter=dict_converter)]):
        pass

    assert_parse_args(
        foo,
        "--config.host localhost 8080 --config.db postgres 5432",
        config={"host": "localhost:8080", "db": "postgres:5432"},
    )


def test_n_tokens_tuple_element_without_converter(app, assert_parse_args):
    """Test n_tokens on tuple elements without custom converter.

    Note: n_tokens works for token counting, but the tuple gets a list of values
    instead of a combined string since there's no custom converter at the element level.
    """

    @app.default
    def foo(
        data: tuple[
            Annotated[list[str], Parameter(n_tokens=2)],  # Will be list of 2 strings
            int,
        ],
    ):
        pass

    assert_parse_args(foo, "a b 10", data=(["a", "b"], 10))


def test_n_tokens_list_consume_all(app, assert_parse_args):
    """Test that n_tokens with list correctly maintains consume_all behavior.

    When n_tokens is used with a list, the converter receives ALL tokens and must
    handle the grouping itself. The n_tokens value affects how many tokens are consumed
    from the CLI, maintaining consume_all behavior for iterables.
    """

    def list_converter(type_, tokens):
        """Group tokens into pairs and combine them."""
        from cyclopts.utils import grouper

        pairs = grouper(tokens, 2)
        return [f"{a.value}-{b.value}" for a, b in pairs]

    @app.default
    def foo(*, items: Annotated[list[str], Parameter(n_tokens=2, converter=list_converter, consume_multiple=True)]):
        pass

    assert_parse_args(foo, "--items a b c d e f", items=["a-b", "c-d", "e-f"])
