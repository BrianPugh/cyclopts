import pytest


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1 --b 2 --c=c-value-manual --meta-flag",
        "1 --b=2 --c=c-value-manual --meta-flag",
        "1 --b=2 --c c-value-manual --meta-flag",
    ],
)
def test_meta_basic(app, cmd_str):
    @app.default
    def foo(a: int, b: int, c="c-value"):
        assert a == 1
        assert b == 2
        assert c == "c-value-manual"

    @app.meta.default
    def meta(*tokens, meta_flag: bool = False):
        assert meta_flag
        app(tokens)

    app.meta(cmd_str)
