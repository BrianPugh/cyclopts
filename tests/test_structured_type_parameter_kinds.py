"""Tests for structured types with various parameter kinds (POSITIONAL_ONLY, VAR_POSITIONAL, etc)."""

import sys
from dataclasses import dataclass, field
from typing import Annotated

import pytest

from cyclopts import Parameter


class GenericClassWithMixedKinds:
    """A generic class that uses __init__ with mixed parameter kinds."""

    def __init__(self, pos_only: int, /, normal: str, *args: int, kw_only: float, **kwargs: str):
        self.pos_only = pos_only
        self.normal = normal
        self.args = args
        self.kw_only = kw_only
        self.kwargs = kwargs

    def __eq__(self, other):
        if not isinstance(other, GenericClassWithMixedKinds):
            return NotImplemented
        return (
            self.pos_only == other.pos_only
            and self.normal == other.normal
            and self.args == other.args
            and self.kw_only == other.kw_only
            and self.kwargs == other.kwargs
        )

    def __repr__(self):
        return (
            f"GenericClassWithMixedKinds(pos_only={self.pos_only}, normal={self.normal}, "
            f"args={self.args}, kw_only={self.kw_only}, kwargs={self.kwargs})"
        )


class GenericClassPositionalOnly:
    """A class with only positional-only parameters."""

    def __init__(self, a: int, b: str, /):
        self.a = a
        self.b = b

    def __eq__(self, other):
        if not isinstance(other, GenericClassPositionalOnly):
            return NotImplemented
        return self.a == other.a and self.b == other.b

    def __repr__(self):
        return f"GenericClassPositionalOnly(a={self.a}, b={self.b})"


class GenericClassKeywordOnly:
    """A class with only keyword-only parameters."""

    def __init__(self, *, x: int, y: str):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if not isinstance(other, GenericClassKeywordOnly):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        return f"GenericClassKeywordOnly(x={self.x}, y={self.y})"


class GenericClassPositionalOnlyAndKeywordOnly:
    """A class with both positional-only and keyword-only parameters."""

    def __init__(self, a: int, /, *, z: str):
        self.a = a
        self.z = z

    def __eq__(self, other):
        if not isinstance(other, GenericClassPositionalOnlyAndKeywordOnly):
            return NotImplemented
        return self.a == other.a and self.z == other.z

    def __repr__(self):
        return f"GenericClassPositionalOnlyAndKeywordOnly(a={self.a}, z={self.z})"


def test_generic_class_positional_only(app, assert_parse_args):
    """Test that POSITIONAL_ONLY parameters are passed as positional arguments."""

    @app.default
    def cmd(obj: Annotated[GenericClassPositionalOnly, Parameter(name="*")]):
        return obj

    assert_parse_args(cmd, "42 hello", obj=GenericClassPositionalOnly(42, "hello"))


def test_generic_class_keyword_only(app, assert_parse_args):
    """Test that KEYWORD_ONLY parameters are passed as keyword arguments."""

    @app.default
    def cmd(obj: Annotated[GenericClassKeywordOnly, Parameter(name="*")]):
        return obj

    # Should work with keywords
    assert_parse_args(cmd, "--x 10 --y world", obj=GenericClassKeywordOnly(x=10, y="world"))


def test_generic_class_keyword_only_positionally(app, assert_parse_args):
    """Test keyword-only class with accepts_keys=False (forces positional parsing)."""

    @app.default
    def cmd(obj: Annotated[GenericClassKeywordOnly, Parameter(name="obj", accepts_keys=False)]):
        return obj

    # With accepts_keys=False, values are passed positionally but converted to kwargs internally
    assert_parse_args(cmd, "--obj 10 world", obj=GenericClassKeywordOnly(x=10, y="world"))


def test_generic_class_positional_only_and_keyword_only(app, assert_parse_args):
    """Test mixed POSITIONAL_ONLY and KEYWORD_ONLY parameters."""

    @app.default
    def cmd(obj: Annotated[GenericClassPositionalOnlyAndKeywordOnly, Parameter(name="*")]):
        return obj

    # Positional-only passed as positional, keyword-only as keyword
    assert_parse_args(cmd, "5 --z test", obj=GenericClassPositionalOnlyAndKeywordOnly(5, z="test"))

    # This tests the critical fix: positional value for 'a', keyword arg for 'z'
    assert_parse_args(cmd, "--z test 5", obj=GenericClassPositionalOnlyAndKeywordOnly(5, z="test"))


@dataclass
class DataclassWithKwOnly:
    """Dataclass with kw_only fields."""

    a: int
    b: str = field(kw_only=True)
    c: float = field(default=3.14, kw_only=True)


def test_dataclass_kw_only_mixed(app, assert_parse_args):
    """Test dataclass with mix of normal and kw_only fields."""

    @app.default
    def cmd(config: Annotated[DataclassWithKwOnly, Parameter(name="*")]):
        return config

    # Normal field as positional, kw_only as keyword
    assert_parse_args(cmd, "100 --b hello --c 2.5", config=DataclassWithKwOnly(a=100, b="hello", c=2.5))

    # Order shouldn't matter for keyword-only
    assert_parse_args(cmd, "--b hello 100 --c 2.5", config=DataclassWithKwOnly(a=100, b="hello", c=2.5))

    # Using default for optional kw_only field
    assert_parse_args(cmd, "100 --b world", config=DataclassWithKwOnly(a=100, b="world"))


@dataclass(kw_only=True)
class DataclassFullyKwOnly:
    """Fully keyword-only dataclass."""

    name: str
    age: int


def test_dataclass_fully_kw_only(app, assert_parse_args):
    """Test dataclass that is entirely kw_only."""

    @app.default
    def cmd(person: Annotated[DataclassFullyKwOnly, Parameter(name="*")]):
        return person

    # With keywords
    assert_parse_args(cmd, "--name Alice --age 30", person=DataclassFullyKwOnly(name="Alice", age=30))


def test_dataclass_fully_kw_only_with_accepts_keys_false(app, assert_parse_args):
    """Test that kw_only dataclass works with accepts_keys=False.

    This is the exact scenario from issue #648.
    """

    @dataclass(kw_only=True)
    class Config:
        name: str

    @app.default
    def cmd(config: Annotated[Config, Parameter(name="config", accepts_keys=False)]):
        return config

    assert_parse_args(cmd, "--config Bob", config=Config(name="Bob"))


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Requires Python 3.10+ for positional-only in dataclass")
def test_dataclass_positional_only_and_keyword_only():
    """Test dataclass with both positional-only and keyword-only fields.

    Note: Python dataclasses don't directly support positional-only parameters.
    This test is included for completeness but may not be applicable.
    """
    # Dataclasses don't support positional-only parameters directly.
    # They only support kw_only. This test documents that limitation.
    pass


def test_generic_class_all_keyword_or_positional(app, assert_parse_args):
    """Test that POSITIONAL_OR_KEYWORD works correctly."""

    class SimpleClass:
        def __init__(self, x: int, y: str):
            self.x = x
            self.y = y

        def __eq__(self, other):
            if not isinstance(other, SimpleClass):
                return NotImplemented
            return self.x == other.x and self.y == other.y

    @app.default
    def cmd(obj: Annotated[SimpleClass, Parameter(name="*")]):
        return obj

    # Both should work: positional and keyword
    assert_parse_args(cmd, "42 hello", obj=SimpleClass(42, "hello"))
    assert_parse_args(cmd, "--x 42 --y hello", obj=SimpleClass(42, "hello"))


@dataclass
class DataclassNested:
    """Nested dataclass for testing."""

    inner: DataclassFullyKwOnly
    outer: str


def test_nested_dataclass_with_kw_only(app, assert_parse_args):
    """Test nested dataclass where inner is kw_only."""

    @app.default
    def cmd(data: Annotated[DataclassNested, Parameter(name="*")]):
        return data

    # Inner kw_only dataclass fields should be accessible
    assert_parse_args(
        cmd,
        "--inner.name Alice --inner.age 25 --outer test",
        data=DataclassNested(inner=DataclassFullyKwOnly(name="Alice", age=25), outer="test"),
    )
