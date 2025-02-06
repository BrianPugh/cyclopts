from textwrap import dedent
from typing import Annotated

import pytest

from cyclopts import App, Parameter
from cyclopts.config import Toml


def test_config_toml(tmp_path):
    fn = tmp_path / "test.toml"
    fn.write_text(
        dedent(
            """\
            [foo]
            key1 = "foo1"
            key2 = "foo2"

            [foo.function1]
            key1 = "bar1"
            key2 = "bar2"
            """
        )
    )
    config = Toml(fn)
    assert config.config == {
        "foo": {
            "key1": "foo1",
            "key2": "foo2",
            "function1": {
                "key1": "bar1",
                "key2": "bar2",
            },
        }
    }


@pytest.fixture(autouse=True)
def chdir_to_tmp_path(tmp_path, monkeypatch):
    """Automatically change current directory to tmp_path"""
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def config_path(tmp_path):
    """Path to JSON configuration file in tmp_path"""
    return tmp_path / "config.toml"  # same name that was provided to cyclopts.config.Json


def test_config_toml_with_meta(config_path):
    config_path.write_text(
        dedent(
            """\
            [this-test]
            name = "Alice"
            """
        )
    )
    app = App(config=Toml("config.toml", root_keys=("this-test",)))

    @app.meta.default
    def meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    ):
        return app(tokens)

    @app.default
    def main(name: str):
        return name

    assert app.meta([], exit_on_error=False) == "Alice"
