import pytest

from cyclopts import CommandCollisionError


def test_command_collision(app):
    @app.command
    def foo():
        pass

    with pytest.raises(CommandCollisionError):

        @app.command
        def foo():  # noqa: F811
            pass

    with pytest.raises(CommandCollisionError):

        @app.command(name="foo")
        def bar():
            pass


def test_command_collision_meta(app):
    @app.command
    def foo():
        pass

    with pytest.raises(CommandCollisionError):

        @app.meta.command
        def foo():  # noqa: F811
            pass

    with pytest.raises(CommandCollisionError):

        @app.meta.command(name="foo")
        def bar():
            pass


def test_command_collision_default(app):
    """Cannot register multiple functions to default."""

    @app.default
    def foo():
        pass

    with pytest.raises(CommandCollisionError):

        @app.default
        def bar():
            pass
