import inspect
import sys
from pathlib import Path

import pytest
from rich.console import Console
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode

import cyclopts
from cyclopts import Group, Parameter


def pytest_addoption(parser):
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests (e.g., documentation build tests)",
    )


def pytest_configure(config):
    # If --run-slow is passed, remove the default "-m 'not slow'" filter
    if config.getoption("--run-slow"):
        # Override the marker expression to include all tests
        config.option.markexpr = ""


class MarkdownSnapshotExtension(SingleFileSnapshotExtension):
    _write_mode = WriteMode.TEXT
    file_extension = "md"


class RstSnapshotExtension(SingleFileSnapshotExtension):
    _write_mode = WriteMode.TEXT
    file_extension = "rst"


@pytest.fixture
def md_snapshot(snapshot):
    return snapshot.use_extension(MarkdownSnapshotExtension)


@pytest.fixture
def rst_snapshot(snapshot):
    return snapshot.use_extension(RstSnapshotExtension)


def pytest_ignore_collect(collection_path):
    for minor in range(8, 20):
        if sys.version_info < (3, minor) and collection_path.stem.startswith(f"test_py3{minor}_"):
            return True

    # Ignore py312/ directory on Python < 3.12
    if sys.version_info < (3, 12) and "py312" in collection_path.parts:
        return True


@pytest.fixture(autouse=True)
def patch_sys_argv(request, monkeypatch):
    """Ensure consistent sys.argv[0] regardless of how pytest is invoked.

    When tests run, cyclopts derives app names from sys.argv[0].
    This can vary based on how pytest is invoked:
    - `pytest`: sys.argv[0] is the pytest executable path
    - `python -m pytest`: sys.argv[0] is the pytest module's __main__.py

    We patch it to always be the test module's __main__.py to trigger
    consistent stack-based name derivation.
    """
    monkeypatch.setattr(sys, "argv", ["__main__.py"] + sys.argv[1:])


@pytest.fixture(autouse=True)
def chdir_to_tmp_path(tmp_path, monkeypatch):
    """Automatically change current directory to tmp_path"""
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def app():
    return cyclopts.App(result_action="return_value")


@pytest.fixture
def console():
    return Console(width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False)


@pytest.fixture
def normalize_trailing_whitespace():
    """Remove trailing whitespace from each line while preserving line breaks.

    Useful for comparing console output where text wrapping may add trailing spaces.
    """

    def _normalize(text: str) -> str:
        return "\n".join(line.rstrip() for line in text.split("\n"))

    return _normalize


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
        app = cyclopts.App(result_action="return_value")

        if isinstance(cmd, Path):
            cmd = cmd.as_posix()

        @app.default
        def target(arg1: type_):  # pyright: ignore
            return arg1

        return app(cmd, exit_on_error=False)

    return inner
