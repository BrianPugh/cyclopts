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
