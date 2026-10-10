import json
import os
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


def test_config_json_default_encoding_reads_non_ascii(tmp_path):
    """Non-ASCII content round-trips through the default encoding.

    Written and read with the same (default) encoding, so this is
    platform-independent -- the default is the locale encoding on Python <3.15
    (e.g. cp1252 on Windows) and UTF-8 on Python >=3.15 per PEP 686.
    """
    fn = tmp_path / "test.json"
    fn.write_text('{"name": "café"}')
    config = Json(fn)
    assert config.config == {"name": "café"}


def test_config_json_explicit_encoding(tmp_path):
    """An explicit ``encoding`` reads a file written in that (non-UTF-8) encoding."""
    fn = tmp_path / "test.json"
    fn.write_text('{"name": "café"}', encoding="latin-1")
    config = Json(fn, encoding="latin-1")
    assert config.config == {"name": "café"}


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


def test_config_empty_json(tmp_path, console):
    """An empty config file reports the decode error rather than raising out of the error panel."""
    Path("config.json").write_text("")

    with pytest.raises(CycloptsError), console.capture() as capture:
        app("create", error_console=console, exit_on_error=False)

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ JSONDecodeError:                                                   │
        │                                                                    │
        │     ^                                                              │
        │ Expecting value: line 1 column 1 (char 0)                          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


@pytest.mark.parametrize("same_named_neighbor", [True, False])
def test_config_json_symlink_uses_target_contents(app, tmp_path, same_named_neighbor):
    """Symlinked configs supply CLI defaults and still reload after the target changes."""
    target = tmp_path / "settings" / "stored-settings.json"
    target.parent.mkdir()
    target.write_text('{"port": 8123}')
    config_path = tmp_path / "config.json"
    if same_named_neighbor:
        (target.parent / config_path.name).write_text('{"port": 9000}')
    try:
        config_path.symlink_to(target)
    except OSError:
        pytest.skip("Creating symlinks is not supported on this platform")
    app.config = Json(config_path)

    @app.default
    def main(port: int = 1234):
        return port

    assert app([]) == 8123
    assert app([]) == 8123  # Cached contents still come from the symlink target.
    target.write_text('{"port": 12345}')
    assert app([]) == 12345


def test_config_json_symlink_retarget_invalidates_cache(tmp_path):
    """Retargeting a config symlink invalidates equal-size, equal-mtime cached data."""
    targets = [tmp_path / name / "config.json" for name in ("first", "second")]
    for target, port in zip(targets, (8123, 9000), strict=True):
        target.parent.mkdir()
        target.write_text(json.dumps({"port": port}))
    stat = targets[0].stat()
    os.utime(targets[1], ns=(stat.st_atime_ns, stat.st_mtime_ns))
    config_path = tmp_path / "config.json"
    try:
        config_path.symlink_to(targets[0])
    except OSError:
        pytest.skip("Creating symlinks is not supported on this platform")
    config = Json(config_path)

    assert config.config == {"port": 8123}
    config_path.unlink()
    config_path.symlink_to(targets[1])
    assert config.config == {"port": 9000}
