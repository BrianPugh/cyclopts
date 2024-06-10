import os
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union

import pytest

import cyclopts


def test_config_env_default(app):
    app = cyclopts.App(
        config=cyclopts.config.Env("CYCLOPTS_TEST_APP_"),
    )

    @app.command
    def foo(bar_baz: int):
        assert bar_baz == 100

    os.environ["CYCLOPTS_TEST_APP_FOO_BAR_BAZ"] = "100"

    app("foo")


def test_config_env_command_false(app):
    app = cyclopts.App(
        config=cyclopts.config.Env("CYCLOPTS_TEST_APP_", command=False),
    )

    @app.command
    def foo(bar: int):
        assert bar == 100

    os.environ["CYCLOPTS_TEST_APP_BAR"] = "100"

    app("foo")
