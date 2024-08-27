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
