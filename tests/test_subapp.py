import pytest

from cyclopts import App, Parameter


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


def test_subapp_default_parameter_resolution():
    parent_app_1 = App(default_parameter=Parameter(show_default=True))

    sub_app = App(name="foo")
    parent_app_1.command(sub_app)

    # Standard Single Resolution
    assert sub_app.default_parameter == Parameter(show_default=True)

    parent_app_2 = App(default_parameter=Parameter(show_default=False, negative=()))
    parent_app_2.command(sub_app)

    # 2-Parent Resolution
    assert sub_app.default_parameter == Parameter(show_default=True, negative=())
