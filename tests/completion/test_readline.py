"""``complete_line`` is pure (app + typed line -> words), so these run without a PTY."""

from pathlib import Path
from typing import Annotated, Literal

import pytest

from cyclopts import App, Parameter
from cyclopts.completion._readline import complete_line, make_readline_completer


@pytest.fixture
def app():
    app = App(name="prog")

    @app.command
    def deploy(env: Literal["prod", "staging"], *, region: str = "us", verbose: bool = False, path: Path = Path()):
        pass

    @app.command
    def delete(name: Annotated[str, Parameter(completer=lambda ctx: ["alpha", "beta", "my file"])]):
        pass

    @app.command(show=False)
    def hidden():
        pass

    return app


@pytest.mark.parametrize(
    "line, expected",
    [
        ("", ["deploy", "delete"]),
        ("de", ["deploy", "delete"]),
        ("dep", ["deploy"]),
        ("deploy ", ["prod", "staging"]),
        ("deploy p", ["prod"]),
        ("deploy prod --region ", []),
        ("--", ["--help", "--version"]),
        ("delete a", ["alpha"]),
        ("delete 'my", ["'my file'"]),
        ('delete "my', ["'my file'"]),
        ("delete --name=b", ["--name=beta"]),
    ],
)
def test_complete_line(app, line, expected):
    assert complete_line(app, line) == expected


def test_complete_line_options_listed(app):
    assert complete_line(app, "deploy prod --") == [
        "--env",
        "--region",
        "--verbose",
        "--no-verbose",
        "--path",
        "--help",
        "--version",
    ]


def test_complete_line_paths(app, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.txt").touch()
    (tmp_path / "data.bak").touch()
    (tmp_path / "other").touch()

    assert complete_line(app, "deploy prod --path da") == ["data/", "data.bak"]
    assert complete_line(app, "deploy prod --path data/") == ["data/a.txt"]
    assert complete_line(app, "deploy prod --path ./da") == ["./data/", "./data.bak"]


def test_complete_line_remapped_bare_flags(app):
    with app.app_stack([], {"remap_flags": True}):
        assert complete_line(app, "he") == ["help"]
        assert complete_line(app, "v") == ["version"]
        assert complete_line(app, "deploy he") == []
    assert complete_line(app, "he") == []


def test_complete_line_hidden_not_offered(app):
    assert complete_line(app, "h") == []


def test_readline_completer_states(app, mocker):
    readline = mocker.MagicMock()
    readline.get_line_buffer.return_value = "deploy p TRAILING"
    readline.get_endidx.return_value = len("deploy p")
    completer = make_readline_completer(app, readline)

    assert completer("p", 0) == "prod"
    assert completer("p", 1) is None


def test_readline_completer_swallows_errors(app, mocker):
    readline = mocker.MagicMock()
    readline.get_line_buffer.side_effect = RuntimeError("boom")
    completer = make_readline_completer(app, readline)

    assert completer("", 0) is None
