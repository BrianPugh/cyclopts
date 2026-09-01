from textwrap import dedent

import pytest

from cyclopts import App, CycloptsError
from cyclopts.config._yaml import Yaml


def test_config_yaml(tmp_path):
    fn = tmp_path / "test.yaml"
    fn.write_text(
        dedent(
            """\
            foo:
                key1: foo1
                key2: foo2

                function1:
                    key1: bar1
                    key2: bar2
            """
        )
    )
    config = Yaml(fn)
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


def test_config_yaml_default_encoding_reads_non_ascii(tmp_path):
    """Non-ASCII content is read correctly with the default (UTF-8-encoded file)."""
    fn = tmp_path / "test.yaml"
    fn.write_text("name: café ☕\n", encoding="utf-8")
    config = Yaml(fn)
    assert config.config == {"name": "café ☕"}


def test_config_yaml_explicit_encoding(tmp_path):
    """An explicit ``encoding`` reads a file written in that (non-UTF-8) encoding."""
    fn = tmp_path / "test.yaml"
    fn.write_text("name: café\n", encoding="latin-1")
    config = Yaml(fn, encoding="latin-1")
    assert config.config == {"name": "café"}


@pytest.mark.parametrize("contents", ["", "# only a comment\n"])
def test_config_yaml_empty_document(tmp_path, contents):
    """An empty (or comments-only) YAML file is an empty config, not a crash."""
    fn = tmp_path / "test.yaml"
    fn.write_text(contents)

    config = Yaml(fn)
    assert config.config == {}

    app = App(config=config, result_action="return_value")

    @app.default
    def main(x: int = 7):
        return x

    assert app([], exit_on_error=False) == 7


def test_config_yaml_non_mapping_document(tmp_path):
    """A YAML document that is not a mapping raises a clean CycloptsError."""
    fn = tmp_path / "test.yaml"
    fn.write_text("- a\n- b\n")

    app = App(config=Yaml(fn, source="test.yaml"), result_action="return_value")

    @app.default
    def main(x: int = 7):
        return x

    with pytest.raises(CycloptsError) as e:
        app([], exit_on_error=False)

    assert str(e.value) == 'Configuration in "test.yaml" must be a mapping, but got list.'
