from textwrap import dedent

from cyclopts.config import Toml


def test_config_end2end(app, tmp_path, assert_parse_args):
    config_fn = tmp_path / "config.toml"

    config_fn.write_text(
        dedent(
            """\
            [tool.cyclopts]
            key1 = "foo1"
            key2 = "foo2"

            [tool.cyclopts.function1]
            key3 = "bar1"
            key4 = "bar2"
            """
        )
    )

    app.config = Toml(config_fn, root_keys=["tool", "cyclopts"])

    @app.default
    def default(key1, key2):
        pass

    @app.command
    def function1(key3, key4):
        pass

    assert_parse_args(default, "foo", key1="foo", key2="foo2")
    assert_parse_args(function1, "function1 --key4=fizz", key3="bar1", key4="fizz")
