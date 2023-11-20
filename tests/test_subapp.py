from cyclopts import App


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
