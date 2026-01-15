"""Tests for StdioPath, a Path subclass that treats "-" as stdin/stdout."""

import sys
from io import BytesIO, StringIO
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter
from cyclopts.types import StdioPath


# Basic StdioPath construction and properties


def test_stdio_path_dash_is_stdio():
    p = StdioPath("-")
    assert p.is_stdio is True


def test_stdio_path_regular_is_not_stdio():
    p = StdioPath("/tmp/test.txt")
    assert p.is_stdio is False


def test_stdio_path_isinstance_path():
    p = StdioPath("-")
    assert isinstance(p, Path)


def test_stdio_path_str_dash():
    p = StdioPath("-")
    assert str(p) == "-"


def test_stdio_path_str_regular():
    path_str = "/tmp/test.txt"
    p = StdioPath(path_str)
    # Path normalizes separators on different platforms
    assert str(p) == str(Path(path_str))


def test_stdio_path_repr_dash():
    p = StdioPath("-")
    assert repr(p) == "StdioPath('-')"


def test_stdio_path_repr_regular():
    path_str = "/tmp/test.txt"
    p = StdioPath(path_str)
    # Path normalizes separators on different platforms
    assert repr(p) == f"StdioPath({str(Path(path_str))!r})"


def test_stdio_path_fspath_dash():
    import os

    p = StdioPath("-")
    assert os.fspath(p) == "-"


def test_stdio_path_fspath_regular():
    import os

    path_str = "/tmp/test.txt"
    p = StdioPath(path_str)
    # Path normalizes separators on different platforms
    assert os.fspath(p) == os.fspath(Path(path_str))


# exists() behavior


def test_stdio_path_exists_always_true_for_dash():
    p = StdioPath("-")
    assert p.exists() is True


def test_stdio_path_exists_false_for_nonexistent(tmp_path):
    p = StdioPath(tmp_path / "nonexistent.txt")
    assert p.exists() is False


def test_stdio_path_exists_true_for_existing(tmp_path):
    f = tmp_path / "existing.txt"
    f.touch()
    p = StdioPath(f)
    assert p.exists() is True


# open() behavior


def test_stdio_path_open_read_text_from_stdin(monkeypatch):
    p = StdioPath("-")
    monkeypatch.setattr(sys, "stdin", StringIO("hello world"))
    with p.open("r") as f:
        assert f.read() == "hello world"


def test_stdio_path_open_write_text_to_stdout(capsys):
    p = StdioPath("-")
    with p.open("w") as f:
        f.write("hello world")
    assert capsys.readouterr().out == "hello world"


def test_stdio_path_open_read_binary_from_stdin(monkeypatch):
    p = StdioPath("-")
    fake_stdin = type("FakeStdin", (), {"buffer": BytesIO(b"binary data")})()
    monkeypatch.setattr(sys, "stdin", fake_stdin)
    with p.open("rb") as f:
        assert f.read() == b"binary data"


def test_stdio_path_open_write_binary_to_stdout(capfdbinary):
    p = StdioPath("-")
    with p.open("wb") as f:
        f.write(b"binary data")
    assert capfdbinary.readouterr().out == b"binary data"


def test_stdio_path_open_regular_file_read(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("file content")
    p = StdioPath(f)
    with p.open("r") as fh:
        assert fh.read() == "file content"


def test_stdio_path_open_regular_file_write(tmp_path):
    f = tmp_path / "test.txt"
    p = StdioPath(f)
    with p.open("w") as fh:
        fh.write("new content")
    assert f.read_text() == "new content"


# read_text, read_bytes, write_text, write_bytes


def test_stdio_path_read_text_from_stdin(monkeypatch):
    p = StdioPath("-")
    fake_stdin = type("FakeStdin", (), {"buffer": BytesIO(b"hello world")})()
    monkeypatch.setattr(sys, "stdin", fake_stdin)
    assert p.read_text() == "hello world"


def test_stdio_path_read_text_from_stdin_with_encoding(monkeypatch):
    p = StdioPath("-")
    fake_stdin = type("FakeStdin", (), {"buffer": BytesIO("café".encode("latin-1"))})()
    monkeypatch.setattr(sys, "stdin", fake_stdin)
    assert p.read_text(encoding="latin-1") == "café"


def test_stdio_path_read_bytes_from_stdin(monkeypatch):
    p = StdioPath("-")
    fake_stdin = type("FakeStdin", (), {"buffer": BytesIO(b"binary data")})()
    monkeypatch.setattr(sys, "stdin", fake_stdin)
    assert p.read_bytes() == b"binary data"


def test_stdio_path_write_text_to_stdout(capfdbinary):
    p = StdioPath("-")
    p.write_text("hello world")
    assert capfdbinary.readouterr().out == b"hello world"


def test_stdio_path_write_text_to_stdout_with_encoding(capfdbinary):
    p = StdioPath("-")
    p.write_text("café", encoding="latin-1")
    assert capfdbinary.readouterr().out == "café".encode("latin-1")


def test_stdio_path_write_bytes_to_stdout(capfdbinary):
    p = StdioPath("-")
    p.write_bytes(b"binary data")
    assert capfdbinary.readouterr().out == b"binary data"


def test_stdio_path_read_text_regular_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("file content")
    p = StdioPath(f)
    assert p.read_text() == "file content"


def test_stdio_path_read_bytes_regular_file(tmp_path):
    f = tmp_path / "test.bin"
    f.write_bytes(b"binary content")
    p = StdioPath(f)
    assert p.read_bytes() == b"binary content"


def test_stdio_path_write_text_regular_file(tmp_path):
    f = tmp_path / "test.txt"
    p = StdioPath(f)
    p.write_text("new content")
    assert f.read_text() == "new content"


def test_stdio_path_write_bytes_regular_file(tmp_path):
    f = tmp_path / "test.bin"
    p = StdioPath(f)
    p.write_bytes(b"binary content")
    assert f.read_bytes() == b"binary content"


# StdioPath integration with cyclopts


def test_stdio_path_allow_leading_hyphen(app, assert_parse_args):
    """StdioPath should accept '-' as a positional argument."""

    @app.default
    def main(path: StdioPath):
        pass

    assert_parse_args(main, "-", StdioPath("-"))


def test_stdio_path_regular_path(app, assert_parse_args, tmp_path):
    """StdioPath should accept regular paths."""
    f = tmp_path / "test.txt"

    @app.default
    def main(path: StdioPath):
        pass

    assert_parse_args(main, str(f), StdioPath(f))


def test_stdio_path_with_annotated(app, assert_parse_args):
    """StdioPath should work when wrapped in Annotated."""

    @app.default
    def main(path: Annotated[StdioPath, Parameter(help="Input path")]):
        pass

    assert_parse_args(main, "-", StdioPath("-"))


def test_stdio_path_multiple_args(app, assert_parse_args, tmp_path):
    """Multiple StdioPath arguments should work."""
    f = tmp_path / "out.txt"

    @app.default
    def main(
        input_path: Annotated[StdioPath, Parameter(help="Input")],
        output_path: Annotated[StdioPath, Parameter(help="Output")],
    ):
        pass

    assert_parse_args(main, f"- {f}", StdioPath("-"), StdioPath(f))
