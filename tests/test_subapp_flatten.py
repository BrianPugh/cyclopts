"""Tests for subapp flattening feature (name="*")."""

import pytest

from cyclopts import App


def test_flatten_basic(app):
    """Test basic flattening of subapp commands."""
    subapp = App(name="sub")

    @subapp.command
    def foo():
        return "foo"

    @subapp.command
    def bar():
        return "bar"

    app.command(subapp, name="*")

    assert app("foo") == "foo"
    assert app("bar") == "bar"


def test_flatten_dynamic_registration(app):
    """Test that commands added to subapp after flattening are still accessible."""
    subapp = App(name="sub")

    @subapp.command
    def foo():
        return "foo"

    app.command(subapp, name="*")

    @subapp.command
    def bar():
        return "bar"

    assert app("foo") == "foo"
    assert app("bar") == "bar"


def test_flatten_parent_precedence(app):
    """Test that parent commands take precedence over flattened commands."""

    @app.command
    def foo():  # pyright: ignore[reportRedeclaration]
        return "parent_foo"

    subapp = App(name="sub")

    @subapp.command
    def foo():  # noqa: F811
        return "subapp_foo"

    @subapp.command
    def bar():
        return "bar"

    app.command(subapp, name="*")

    assert app("foo") == "parent_foo"
    assert app("bar") == "bar"


def test_flatten_multiple_subapps(app):
    """Test flattening multiple subapps with collision handling."""
    subapp1 = App(name="sub1")

    @subapp1.command
    def foo():  # pyright: ignore[reportRedeclaration]
        return "foo1"

    @subapp1.command
    def bar():
        return "bar1"

    subapp2 = App(name="sub2")

    @subapp2.command
    def foo():  # noqa: F811
        return "foo2"

    @subapp2.command
    def baz():
        return "baz2"

    app.command(subapp1, name="*")
    app.command(subapp2, name="*")

    # First registered subapp wins on collision
    assert app("foo") == "foo1"
    assert app("bar") == "bar1"
    assert app("baz") == "baz2"


@pytest.mark.parametrize(
    "method,expected",
    [
        ("contains_foo", True),
        ("contains_bar", False),
        ("iter_has_foo", True),
        ("iter_no_duplicates", True),
        ("getitem_works", True),
        ("resolved_commands", True),
        ("registered_commands", True),
    ],
)
def test_flatten_dict_interface(app, method, expected):
    """Test that flattened commands work with dict-like interfaces."""
    subapp = App(name="sub")

    @subapp.command
    def foo():
        return "foo"

    app.command(subapp, name="*")

    if method == "contains_foo":
        assert ("foo" in app) == expected
    elif method == "contains_bar":
        assert ("bar" in app) == expected
    elif method == "iter_has_foo":
        assert ("foo" in list(app)) == expected
    elif method == "iter_no_duplicates":
        commands = list(app)
        assert commands.count("foo") == 1
    elif method == "getitem_works":
        foo_app = app["foo"]
        assert foo_app.default_command() == "foo"
    elif method == "resolved_commands":
        assert ("foo" in app.resolved_commands()) == expected
    elif method == "registered_commands":
        registered = app._registered_commands
        assert ("foo" in registered) == expected
        assert "--help" not in registered


@pytest.mark.parametrize(
    "obj,error_match",
    [
        (lambda: "foo", "only supported for App instances"),
        ("some.module:function", "only supported for App instances"),
    ],
)
def test_flatten_error_non_app(app, obj, error_match):
    """Test that flattening only works with App instances."""
    with pytest.raises(TypeError, match=error_match):
        app.command(obj, name="*")


def test_flatten_error_with_kwargs(app):
    """Test that flattening with kwargs raises error."""
    subapp = App(name="sub")

    with pytest.raises(ValueError, match="Cannot supply additional configuration"):
        app.command(subapp, name="*", help_flags=[])


def test_flatten_nested_subapp(app):
    """Test flattening only affects direct commands, not nested subapps."""
    subapp2 = App(name="sub2")

    @subapp2.command
    def deeply_nested():
        return "deep"

    subapp1 = App(name="sub1")
    subapp1.command(subapp2, name="nested")

    @subapp1.command
    def shallow():
        return "shallow"

    app.command(subapp1, name="*")

    assert app("shallow") == "shallow"
    assert app("nested deeply-nested") == "deep"


def test_flatten_recursive(app):
    """Test that flatten works recursively through multiple levels."""
    subapp1 = App(name="sub1")

    @subapp1.command
    def foo():
        return "foo"

    subapp2 = App(name="sub2")

    @subapp2.command
    def bar():
        return "bar"

    subapp1.command(subapp2, name="*")
    app.command(subapp1, name="*")

    assert app("foo") == "foo"
    assert app("bar") == "bar"


def test_flatten_with_arguments(app):
    """Test flattening works with commands that have arguments."""
    subapp = App(name="sub")

    @subapp.command
    def foo(x: int, y: str):
        return f"{x}-{y}"

    app.command(subapp, name="*")

    assert app("foo 42 hello") == "42-hello"
