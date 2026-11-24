"""Environment variable names from ``config.Env`` in generated documentation."""

import pytest

from cyclopts import App
from cyclopts.config import Env

FORMATS = ["markdown", "rst", "html"]


def _make_app(*, command: bool = True) -> App:
    app = App(name="demo", config=Env("DEMO_", command=command), result_action="return_value")

    @app.default
    def main(verbose: bool = False):
        """Root command."""

    @app.command
    def serve(port: int = 8080):
        """Serve."""
        return port

    db = App(name="db")
    app.command(db)

    @db.command
    def migrate(dry_run: bool = False):
        """Migrate."""
        return dry_run

    return app


@pytest.mark.parametrize("output_format", FORMATS)
def test_generate_docs_env_var_includes_command_chain(output_format):
    docs = _make_app().generate_docs(output_format=output_format)

    assert "DEMO_VERBOSE" in docs
    assert "DEMO_SERVE_PORT" in docs
    assert "DEMO_DB_MIGRATE_DRY_RUN" in docs
    # Names without the command segments are ignored at runtime.
    assert "DEMO_PORT" not in docs
    assert "DEMO_DRY_RUN" not in docs
    assert "DEMO_MIGRATE_DRY_RUN" not in docs


@pytest.mark.parametrize("output_format", FORMATS)
def test_generate_docs_env_var_without_command_prefix(output_format):
    docs = _make_app(command=False).generate_docs(output_format=output_format)

    assert "DEMO_PORT" in docs
    assert "DEMO_DRY_RUN" in docs
    assert "DEMO_SERVE_PORT" not in docs
    assert "DEMO_DB_MIGRATE_DRY_RUN" not in docs


def test_generate_docs_env_var_matches_runtime(monkeypatch):
    app = _make_app()
    docs = app.generate_docs(output_format="markdown")
    assert "DEMO_SERVE_PORT" in docs

    monkeypatch.setenv("DEMO_SERVE_PORT", "2222")
    assert app(["serve"]) == 2222


@pytest.mark.parametrize("output_format", FORMATS)
def test_generate_docs_env_var_meta_option(output_format):
    app = _make_app()

    @app.meta.default
    def meta(*tokens: str, quiet: bool = False):
        pass

    docs = app.generate_docs(output_format=output_format)

    assert "DEMO_QUIET" in docs
    # A meta app runs before command dispatch, so its names never include command segments.
    assert "DEMO_SERVE_QUIET" not in docs
    assert "DEMO_DB_MIGRATE_QUIET" not in docs
