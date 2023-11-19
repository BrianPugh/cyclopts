import pytest


@pytest.mark.parametrize(
    "cmd_str",
    [
        "a-value --b b-value --c=c-value-manual",
    ],
)
def test_meta_basic(app, cmd_str):
    @app.default
    def foo(a: int, b: int, c="c-value"):
        assert a == "a-value"
        assert b == "b-value"
        assert c == "c-value-manual"

    @app.meta.default
    def meta(*tokens, meta_flag: bool = False):
        assert meta_flag
        app(tokens)

    app.meta(cmd_str)
