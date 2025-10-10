import json
from pathlib import Path
from textwrap import dedent

import pytest

from cyclopts import App, CycloptsError
from cyclopts.config._json import Json


def test_config_json(tmp_path):
    fn = tmp_path / "test.yaml"
    fn.write_text(
        dedent(
            """\
            {
                "foo": {
                    "key1": "foo1",
                    "key2": "foo2",
                    "function1": {
                        "key1": "bar1",
                        "key2": "bar2"
                    }
                }
            }
            """
        )
    )
    config = Json(fn)
    assert config.config == {
        "foo": {
            "key1": "foo1",
            "key2": "foo2",
            "function1": {
                "key1": "bar1",
                "key2": "bar2",
            },
        }
    }


"""
Test file-caching and chdir after app has been instantiated. See discussion:
    https://github.com/BrianPugh/cyclopts/issues/309
"""

app = App(config=Json("config.json"), result_action="return_value")


@app.command
def create(name: str, age: int):
    print(f"{name} is {age} years old.")


@pytest.fixture(autouse=True)
def chdir_to_tmp_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def config_path(tmp_path):
    return tmp_path / "config.json"


def test_config_1(config_path, capsys, mocker):
    with config_path.open("w") as f:
        json.dump({"create": {"name": "Alice", "age": 30}}, f)

    json_config = app.config[0]
    spy_load_config = mocker.patch.object(json_config, "_load_config", wraps=json_config._load_config)  # pyright: ignore[reportAttributeAccessIssue]
    app("create")
    assert capsys.readouterr().out == "Alice is 30 years old.\n"
    assert spy_load_config.call_count == 1

    # Ensure that it doesn't get called again because the file hasn't changed.
    app("create")
    assert capsys.readouterr().out == "Alice is 30 years old.\n"
    assert spy_load_config.call_count == 1

    # If we modify the file, then it should get loaded again.
    with config_path.open("w") as f:
        json.dump({"create": {"name": "Bob", "age": 40}}, f)

    app("create")
    assert capsys.readouterr().out == "Bob is 40 years old.\n"
    assert spy_load_config.call_count == 2


def test_config_2(config_path, capsys):
    with config_path.open("w") as f:
        json.dump({"create": {"name": "Bob", "age": 40}}, f)

    app("create")
    assert capsys.readouterr().out == "Bob is 40 years old.\n"


def test_config_invalid_json(tmp_path, console):
    Path("config.json").write_text('{"this is": broken}')

    with pytest.raises(CycloptsError), console.capture() as capture:
        app("create", error_console=console, exit_on_error=False)

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ JSONDecodeError:                                                   │
        │     {"this is": broken}                                            │
        │                 ^                                                  │
        │ Expecting value: line 1 column 13 (char 12)                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected
