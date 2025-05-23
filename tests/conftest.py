import inspect
import sys
from pathlib import Path

import pytest
from rich.console import Console

import cyclopts
from cyclopts import Group, Parameter


def pytest_ignore_collect(collection_path):
    for minor in range(8, 20):
        if sys.version_info < (3, minor) and collection_path.stem.startswith(f"test_py3{minor}_"):
            return True


@pytest.fixture(autouse=True)
def chdir_to_tmp_path(tmp_path, monkeypatch):
    """Automatically change current directory to tmp_path"""
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def app():
    return cyclopts.App()


@pytest.fixture
def console():
    return Console(width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False)


@pytest.fixture
def default_function_groups():
    return (Parameter(), Group("Arguments"), Group("Parameters"))


@pytest.fixture
def assert_parse_args(app):
    def inner(f, cmd: str, *args, **kwargs):
        signature = inspect.signature(f)
        expected_bind = signature.bind(*args, **kwargs)
        actual_command, actual_bind, _ = app.parse_args(cmd, print_error=False, exit_on_error=False)
        assert actual_command == f
        assert actual_bind == expected_bind

    return inner


@pytest.fixture
def assert_parse_args_config(app):
    def inner(config: dict, f, cmd: str, *args, **kwargs):
        signature = inspect.signature(f)
        expected_bind = signature.bind(*args, **kwargs)
        actual_command, actual_bind, _ = app.parse_args(cmd, print_error=False, exit_on_error=False, **config)
        assert actual_command == f
        assert actual_bind == expected_bind

    return inner


@pytest.fixture
def assert_parse_args_partial(app):
    def inner(f, cmd: str, *args, **kwargs):
        signature = inspect.signature(f)
        expected_bind = signature.bind_partial(*args, **kwargs)
        actual_command, actual_bind, _ = app.parse_args(cmd, print_error=False, exit_on_error=False)
        assert actual_command == f
        assert actual_bind == expected_bind

    return inner


@pytest.fixture
def convert():
    """Function that performs a conversion for a given type/cmd pair.

    Goes through the whole app stack.
    """

    def inner(type_, cmd):
        app = cyclopts.App()

        if isinstance(cmd, Path):
            cmd = cmd.as_posix()

        @app.default
        def target(arg1: type_):  # pyright: ignore
            return arg1

        return app(cmd, exit_on_error=False)

    return inner
