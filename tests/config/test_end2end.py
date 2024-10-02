from textwrap import dedent

import pytest

from cyclopts.config import Toml
from cyclopts.exceptions import MissingArgumentError

pytest.skip(allow_module_level=True, reason="config is broken until ArgumentCollection is piped all the way through.")


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


def test_config_end2end_deleting_keys(app, assert_parse_args):
    def my_config_foo(apps, commands, mapping):
        # Sets all values to foo
        for key in mapping:
            mapping[key] = ["foo"]

    def my_config_del(apps, commands, mapping):
        # Just unsets everything
        mapping.clear()

    @app.command
    def my_command(key1, key2):
        pass

    app.config = my_config_foo
    assert_parse_args(my_command, "my-command", key1="foo", key2="foo")

    # ``my_config_del`` will delete all the passed in arguments,
    # resulting in a MissingArgumentError.
    app.config = my_config_del
    with pytest.raises(MissingArgumentError):
        app("my-command foo foo", exit_on_error=False)
    app.config = (my_config_foo, my_config_del)
    with pytest.raises(MissingArgumentError):
        app("my-command foo foo", exit_on_error=False)

    # Deleting, then applying foo value should work.
    app.config = (my_config_del, my_config_foo)
    assert_parse_args(my_command, "my-command", key1="foo", key2="foo")
