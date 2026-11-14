"""Each loaded script must retain its own module globals."""

import sys
from pathlib import Path

import pytest

from cyclopts import App
from cyclopts.loader import load_app_from_script


@pytest.fixture(autouse=True)
def cleanup_loaded_modules():
    before = {name: value for name, value in sys.modules.items() if name.startswith("__cyclopts_doc_module")}
    yield
    for name in list(sys.modules):
        if name.startswith("__cyclopts_doc_module"):
            sys.modules.pop(name)
    sys.modules.update(before)


def write_app(path: Path, value_type: str, version: str) -> None:
    path.write_text(
        "from __future__ import annotations\n"
        "from dataclasses import dataclass\n"
        "from cyclopts import App\n"
        f"Value = {value_type}\n"
        f"__version__ = {version!r}\n"
        "@dataclass\n"
        "class Config:\n"
        "    value: Value\n"
        "app = App(result_action='return_value', print_error=False, exit_on_error=False)\n"
        "@app.default\n"
        "def main(config: Config):\n"
        "    return config.value\n"
    )


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("explicit", [False, True])
def test_loaded_apps_keep_forward_reference_globals(tmp_path, reverse, explicit):
    first_path, second_path = tmp_path / "first.py", tmp_path / "second.py"
    write_app(first_path, "int", "1.0")
    write_app(second_path, "str", "2.0")
    paths = [first_path, second_path]
    if reverse:
        paths.reverse()
    apps = {path.name: load_app_from_script(f"{path}:app" if explicit else path)[0] for path in paths}
    first, second = apps["first.py"], apps["second.py"]
    first_value = first(["--config.value", "7"])
    assert type(first_value) is int
    assert first_value == 7
    assert second(["--config.value", "7"]) == "7"


def test_loaded_apps_keep_version_globals(tmp_path):
    first_path, second_path = tmp_path / "first.py", tmp_path / "second.py"
    write_app(first_path, "int", "1.0")
    write_app(second_path, "str", "2.0")
    first = load_app_from_script(first_path)[0]
    second = load_app_from_script(second_path)[0]
    assert first._get_fallback_version_string() == "1.0"
    assert second._get_fallback_version_string() == "2.0"
    assert first._instantiating_module is not second._instantiating_module


def test_reload_same_script_keeps_prior_app_globals(tmp_path):
    script = tmp_path / "app.py"
    write_app(script, "int", "first")
    first = load_app_from_script(script)[0]
    # Use a different source length so this is not a same-mtime/size .pyc test.
    write_app(script, "str", "second-version")
    second = load_app_from_script(script)[0]
    assert type(first(["--config.value", "7"])) is int
    assert second(["--config.value", "7"]) == "7"
    assert first._get_fallback_version_string() == "first"
    assert second._get_fallback_version_string() == "second-version"


@pytest.mark.parametrize("failure", ["RuntimeError", "SystemExit", "KeyboardInterrupt"])
def test_failed_script_load_removes_partial_module(tmp_path, failure):
    script = tmp_path / "broken.py"
    script.write_text(f"raise {failure}('failed load')\n")
    modules_before = set(sys.modules)
    original_call = App.__call__
    with pytest.raises(getattr(__import__("builtins"), failure), match="failed load"):
        load_app_from_script(script)
    assert not any(
        name not in modules_before and getattr(module, "__file__", None) == str(script)
        for name, module in sys.modules.items()
    )
    assert App.__call__ is original_call


def test_single_load_control(tmp_path):
    script = tmp_path / "app.py"
    write_app(script, "int", "1.0")
    app = load_app_from_script(script)[0]
    assert app(["--config.value", "7"]) == 7
    assert app._get_fallback_version_string() == "1.0"
