from textwrap import dedent

import pytest

from cyclopts.config import Toml


@pytest.mark.skip(reason="Need to think carefully about where injection is performed.")
def test_config_end2end(app, tmp_path):
    config_fn = tmp_path / "config.toml"

    config_fn.write_text(
        dedent(
            """\
            [tool.cyclopts]
            key1 = "foo1"
            key2 = "foo2"

            [foo.function1]
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

    command, bound, _ = app.parse_known_args(["foo"])
