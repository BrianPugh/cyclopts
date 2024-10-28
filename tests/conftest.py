import sys
from pathlib import Path

import pytest
from rich.console import Console

import cyclopts
import cyclopts.utils
from cyclopts import Group, Parameter


def pytest_ignore_collect(collection_path):
    for minor in range(8, 20):
        if sys.version_info < (3, minor) and collection_path.stem.startswith(f"test_py3{minor}_"):
            return True


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
        signature = cyclopts.utils.signature(f)
        expected_bind = signature.bind(*args, **kwargs)
        actual_command, actual_bind = app.parse_args(cmd, print_error=False, exit_on_error=False)
        assert actual_command == f
        assert actual_bind == expected_bind

    return inner


@pytest.fixture
def assert_parse_args_partial(app):
    def inner(f, cmd: str, *args, **kwargs):
        signature = cyclopts.utils.signature(f)
        expected_bind = signature.bind_partial(*args, **kwargs)
        actual_command, actual_bind = app.parse_args(cmd, print_error=False, exit_on_error=False)
        assert actual_command == f
        assert actual_bind == expected_bind

    return inner


@pytest.fixture
def convert(app):
    """Function that performs a conversion for a given type/cmd pair.

    Goes through the whole app stack.
    Can only be called once per test.
    """
    n_times_called = 0

    def inner(type_, cmd):
        nonlocal n_times_called
        if n_times_called:
            raise pytest.UsageError("convert fixture can only be called once per test.")
        n_times_called += 1

        if isinstance(cmd, Path):
            cmd = cmd.as_posix()

        @app.default
        def target(arg1: type_):  # pyright: ignore
            return arg1

        return app(cmd, exit_on_error=False)

    return inner
