"""Tests for the 'cyclopts tree' command."""

from textwrap import dedent

import pytest

from cyclopts.cli import app as cyclopts_cli

NESTED_SCRIPT = dedent(
    """\
    from cyclopts import App

    app = App(name="my-app")

    render = App(name="render")
    app.command(render)

    @render.command
    def map():
        '''Render maps.'''

    @render.command
    def transect():
        '''Render transects.'''

    @app.command
    def archive():
        '''Archive tools.'''

    @app.command(show=False)
    def secret():
        '''Hidden command.'''
    """
)


def test_tree_nested(tmp_path, capsys):
    """Tree shows nested commands with connectors."""
    script = tmp_path / "nested.py"
    script.write_text(NESTED_SCRIPT)

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["tree", str(script)])

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "my-app" in out
    assert "render" in out
    assert "map" in out
    assert "transect" in out
    assert "archive" in out
    # Tree connectors are rendered.
    assert "├" in out or "└" in out


def test_tree_descriptions_shown_by_default(tmp_path, capsys):
    """Short descriptions appear next to command names by default."""
    script = tmp_path / "desc.py"
    script.write_text(NESTED_SCRIPT)

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["tree", str(script)])

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Render maps." in out
    assert "Archive tools." in out


def test_tree_no_description(tmp_path, capsys):
    """--no-description suppresses the description text."""
    script = tmp_path / "nodesc.py"
    script.write_text(NESTED_SCRIPT)

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["tree", str(script), "--no-description"])

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "map" in out
    assert "Render maps." not in out
    assert "Archive tools." not in out


@pytest.mark.parametrize("flag", ["--max-depth", "-m"])
def test_tree_max_depth(tmp_path, capsys, flag):
    """--max-depth/-m limits the displayed depth."""
    script = tmp_path / "depth.py"
    script.write_text(NESTED_SCRIPT)

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["tree", str(script), flag, "1"])

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "render" in out
    assert "archive" in out
    # Nested commands beyond depth 1 are not shown.
    assert "map" not in out
    assert "transect" not in out


def test_tree_excludes_hidden_and_builtin(tmp_path, capsys):
    """Hidden commands and built-in help/version flags are excluded."""
    script = tmp_path / "hidden.py"
    script.write_text(NESTED_SCRIPT)

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["tree", str(script)])

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "secret" not in out
    assert "--help" not in out
    assert "--version" not in out


def test_tree_app_notation(tmp_path, capsys):
    """':app' notation selects a specific app object."""
    script = tmp_path / "multi.py"
    script.write_text(
        dedent(
            """\
            from cyclopts import App

            app1 = App(name="app1")
            app2 = App(name="app2")

            @app1.command
            def foo():
                pass

            @app2.command
            def bar():
                pass
            """
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        cyclopts_cli(["tree", f"{script}:app2"])

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "app2" in out
    assert "bar" in out
    assert "foo" not in out
