import pytest

from cyclopts import App, Parameter
from cyclopts.exceptions import UnknownOptionError


def test_subapp_basic(app):
    @app.command
    def foo(a: int, b: int, c: int):
        return a + b + c

    app.command(bar := App(name="bar"))

    @bar.command
    def fizz(a: int, b: int, c: int):
        return a - b - c

    @bar.command
    def buzz():
        return 100

    @bar.default
    def default(a: int):
        return 100 * a

    assert 6 == app("foo 1 2 3")
    assert -4 == app("bar fizz 1 2 3")
    assert 100 == app("bar buzz")
    assert 200 == app("bar 2")


def test_subapp_must_have_name(app):
    with pytest.raises(ValueError):
        app.command(App())  # Failure on attempting to register an app without an explicit name.

    app.command(App(), name="foo")  # However, this is fine.


def test_subapp_registering_cannot_have_other_kwargs(app):
    with pytest.raises(ValueError):
        app.command(App(name="foo"), help="this is invalid.")


def test_subapp_cannot_be_default(app):
    with pytest.raises(TypeError):
        app.default(App(name="foo"))

    with pytest.raises(TypeError):
        App(default_command=App(name="foo"))


def test_resolve_default_parameter_1():
    """Test that sub-app inherits default_parameter from parent when it doesn't have its own."""
    # Parent app sets negative_bool=() to disable --no- flags globally
    parent_app = App(default_parameter=Parameter(negative_bool=()))

    parent_app.command(sub_app := App(name="bar"))

    @sub_app.default
    def sub_command(*, flag: bool = False):
        return flag

    result = parent_app("bar --flag")
    assert result is True

    # This should fail because --no-flag shouldn't exist due to negative_bool=()
    with pytest.raises(UnknownOptionError):
        parent_app("bar --no-flag", exit_on_error=False)


def test_resolve_default_parameter_2():
    """Test that sub-app's default_parameter overrides parent's default_parameter."""
    # Parent app disables --no- flags, but sub-app re-enables them with custom prefix
    parent_app = App(default_parameter=Parameter(negative_bool=()))

    parent_app.command(sub_app := App(name="bar", default_parameter=Parameter(negative_bool="disable-")))

    @sub_app.default
    def sub_command(*, flag: bool = False):
        return flag

    # Test through conventional calling interface - the sub-app's default_parameter should take precedence
    # The sub-app should use --disable- prefix instead of --no-
    result = parent_app("bar --disable-flag")
    assert result is False

    # The standard --no-flag shouldn't work
    with pytest.raises(UnknownOptionError):
        parent_app("bar --no-flag", exit_on_error=False)


def test_subapp_name_alias(app, assert_parse_args):
    @app.command(alias="bar")
    def foo(a):
        pass

    assert_parse_args(foo, "foo 5", "5")
    assert_parse_args(foo, "bar 5", "5")


def test_subapp_name_and_alias(app, assert_parse_args):
    """https://github.com/BrianPugh/cyclopts/issues/508"""

    @app.command(name=["fizz", "buzz"], alias="bar")
    def foo(a):
        pass

    assert_parse_args(foo, "fizz 5", "5")
    assert_parse_args(foo, "buzz 5", "5")
    assert_parse_args(foo, "bar 5", "5")
