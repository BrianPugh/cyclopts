def test_bind_var_pos(app):
    """Checks if "Alice" gets erroneously unpacked into ``("A", "l", "i", "c", "e")``."""

    @app.default
    def default(*tokens: str):
        assert tokens == ("Alice",)

    app(["Alice"])
