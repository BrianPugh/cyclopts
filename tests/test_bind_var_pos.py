def test_bind_var_pos(app):
    """Checks if "Alice" gets erroneously unpacked into ``("A", "l", "i", "c", "e")``."""

    @app.default
    def default(*tokens: str):
        assert tokens == ("Alice",)

    app(["Alice"])


def test_bind_custom_class_only_var_positional(app, assert_parse_args):
    """It's quite common for classes with *args to really only intend to consume 1 element."""

    class MyCustomClass:
        def __init__(self, *args: int):
            self.args = args

    @app.default
    def default(value: MyCustomClass):
        pass

    assert_parse_args(default, "100", MyCustomClass(100))
