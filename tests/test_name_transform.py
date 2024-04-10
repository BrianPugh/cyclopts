import pytest

from cyclopts import App, default_name_transform


@pytest.mark.parametrize(
    "before,after",
    [
        ("FOO", "foo"),
        ("_FOO", "foo"),
        ("_FOO_", "foo"),
        ("_F_O_O_", "f-o-o"),
    ],
)
def test_default_name_transform(before, after):
    assert default_name_transform(before) == after


def test_app_name_transform_default(app):
    @app.command
    def _F_O_O_():  # noqa: N802
        pass

    assert "f-o-o" in app


def test_app_name_transform_custom(app):
    def name_transform(s: str) -> str:
        return "my-custom-name-transform"

    app.name_transform = name_transform

    @app.command
    def foo():
        pass

    assert "my-custom-name-transform" in app


def test_subapp_name_transform_custom(app):
    """A subapp with an explicitly set ``name_transform`` should NOT inherit from parent."""

    def name_transform_1(s: str) -> str:
        return "my-custom-name-transform-1"

    def name_transform_2(s: str) -> str:
        return "my-custom-name-transform-2"

    app.name_transform = name_transform_1

    app.command(subapp := App(name="bar", name_transform=name_transform_2))

    @subapp.command
    def foo():
        pass

    assert "my-custom-name-transform-2" in subapp


def test_subapp_name_transform_custom_inherited(app):
    """A subapp without an explicitly set ``name_transform`` should inherit it from the first parent."""

    def name_transform(s: str) -> str:
        return "my-custom-name-transform"

    app.name_transform = name_transform

    app.command(subapp := App(name="bar"))

    @subapp.command
    def foo():
        pass

    assert "my-custom-name-transform" in subapp


@pytest.mark.skip(reason="TODO")
def test_parameter_name_transform_default(app):
    pass


@pytest.mark.skip(reason="TODO")
def test_parameter_name_transform_custom(app):
    pass
