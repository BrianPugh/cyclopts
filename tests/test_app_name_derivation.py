import sys
import types

import pytest

from cyclopts import App


@pytest.fixture
def mock_get_root_module_name(mocker):
    return mocker.patch("cyclopts.core._get_root_module_name", return_value="mock_module_name")


def test_app_name_derivation_main_module(mocker, mock_get_root_module_name):
    mocker.patch("cyclopts.core.sys.argv", ["__main__.py"])
    app = App()

    assert app.name == ("mock_module_name",)
    mock_get_root_module_name.assert_called()


def test_app_name_derivation_not_main_module(mocker):
    mocker.patch("cyclopts.core.sys.argv", ["my-script.py"])
    app = App()

    assert app.name == ("my-script.py",)


def _mock_main_spec(mocker, spec_name, origin):
    """Pretend the interpreter was started with ``python -m <spec_name>``."""
    main = types.ModuleType("__main__")
    main.__spec__ = types.SimpleNamespace(name=spec_name, origin=origin)  # pyright: ignore[reportAttributeAccessIssue]
    mocker.patch.dict(sys.modules, {"__main__": main})
    mocker.patch("cyclopts.core.sys.executable", "/usr/bin/python3")


@pytest.mark.parametrize(
    "argv0, spec_name, expected",
    [
        ("/src/mymodule.py", "mymodule", "python3 -m mymodule"),
        ("/src/mypkg/__main__.py", "mypkg.__main__", "python3 -m mypkg"),
        ("/src/mypkg/run.py", "mypkg.run", "python3 -m mypkg.run"),
    ],
)
def test_app_name_derivation_python_m(mocker, argv0, spec_name, expected):
    mocker.patch("cyclopts.core.sys.argv", [argv0])
    _mock_main_spec(mocker, spec_name, argv0)

    assert App().name == (expected,)


def test_app_name_derivation_python_m_wrapper(mocker):
    """``python -m cProfile script.py`` names the app after the script."""
    mocker.patch("cyclopts.core.sys.argv", ["script.py"])
    _mock_main_spec(mocker, "cProfile", "/usr/lib/python3/cProfile.py")

    assert App().name == ("script.py",)


def test_app_name_derivation_python_m_usage(mocker, console):
    """The usage line of an app with a default command also shows ``python -m``."""
    mocker.patch("cyclopts.core.sys.argv", ["/src/mypkg/__main__.py"])
    _mock_main_spec(mocker, "mypkg.__main__", "/src/mypkg/__main__.py")
    app = App(result_action="return_value")

    @app.default
    def main(value: int = 1):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    assert capture.get().splitlines()[0] == "Usage: python3 -m mypkg [ARGS]"
