from cyclopts import App


def test_app_iter(app):
    """Like a dictionary, __iter__ of an App should yield keys (command names)."""

    @app.command
    def foo():
        pass

    @app.command
    def bar():
        pass

    actual = list(app)
    assert actual == ["--help", "-h", "--version", "foo", "bar"]


def test_app_iter_with_meta(app):
    @app.command
    def foo():
        pass

    @app.command
    def bar():
        pass

    @app.meta.command
    def fizz():
        pass

    actual = list(app)
    assert actual == ["--help", "-h", "--version", "foo", "bar"]

    actual = list(app.meta)
    assert actual == ["--help", "-h", "--version", "fizz", "foo", "bar"]


def test_app_update():
    app1 = App()
    app2 = App()

    @app1.command
    def foo():
        pass

    @app2.command
    def bar():
        pass

    app1.update(app2)

    assert list(app1) == ["--help", "-h", "--version", "foo", "bar"]
