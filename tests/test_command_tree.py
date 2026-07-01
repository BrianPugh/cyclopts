"""Tests for App.command_tree() method."""

from rich.console import Console
from rich.tree import Tree

from cyclopts import App


def _render(tree: Tree) -> str:
    console = Console(width=200)
    with console.capture() as capture:
        console.print(tree)
    return capture.get()


def _build_app() -> App:
    app = App(name="my-app")

    render = App(name="render")
    app.command(render)

    @render.command
    def map():
        """Render maps."""

    @render.command
    def video():
        """Render video."""

    @app.command
    def archive():
        """Archive tools."""

    @app.command(show=False)
    def secret():
        """Hidden command."""

    return app


def test_command_tree_returns_tree():
    """command_tree returns a rich Tree renderable rooted at the app name."""
    app = _build_app()
    tree = app.command_tree()
    assert isinstance(tree, Tree)
    out = _render(tree)
    assert "my-app" in out
    assert "render" in out
    assert "map" in out
    assert "video" in out
    assert "archive" in out


def test_command_tree_descriptions_by_default():
    out = _render(_build_app().command_tree())
    assert "Render maps." in out
    assert "Archive tools." in out


def test_command_tree_no_description():
    out = _render(_build_app().command_tree(description=False))
    assert "map" in out
    assert "Render maps." not in out


def test_command_tree_max_depth():
    out = _render(_build_app().command_tree(max_depth=1))
    assert "render" in out
    assert "archive" in out
    assert "map" not in out
    assert "video" not in out


def test_command_tree_excludes_hidden_and_builtin():
    out = _render(_build_app().command_tree())
    assert "secret" not in out
    assert "--help" not in out
    assert "--version" not in out


def test_command_tree_include_hidden():
    out = _render(_build_app().command_tree(include_hidden=True))
    assert "secret" in out
