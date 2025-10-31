"""Tests for App result_action parameter with explicit naming."""

from contextlib import redirect_stdout
from io import StringIO
from typing import Annotated

import pytest

from cyclopts import App, Parameter

# ==============================================================================
# return_value tests
# ==============================================================================


def test_result_action_return_value_with_string():
    """return_value: returns string unchanged."""
    app = App(result_action="return_value")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    result = app(["greet", "Alice"])
    assert result == "Hello Alice!"


def test_result_action_return_value_with_int():
    """return_value: returns int unchanged."""
    app = App(result_action="return_value")

    @app.command
    def double(number: int) -> int:
        return number * 2

    result = app(["double", "5"])
    assert result == 10


def test_result_action_return_value_with_none():
    """return_value: returns None unchanged."""
    app = App(result_action="return_value")

    @app.command
    def do_nothing() -> None:
        pass

    result = app(["do-nothing"])
    assert result is None


# ==============================================================================
# print_non_int_return_int_as_exit_code tests
# ==============================================================================


def test_result_action_print_non_int_return_int_as_exit_code_with_string():
    """print_non_int_return_int_as_exit_code: prints string and returns 0."""
    app = App(result_action="print_non_int_return_int_as_exit_code")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Bob"])

    assert result == 0
    assert buf.getvalue() == "Hello Bob!\n"


def test_result_action_print_non_int_return_int_as_exit_code_with_int():
    """print_non_int_return_int_as_exit_code: returns int as exit code, no print."""
    app = App(result_action="print_non_int_return_int_as_exit_code")

    @app.command
    def get_exit_code(code: int) -> int:
        return code

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-exit-code", "5"])

    assert result == 5
    assert buf.getvalue() == ""


def test_result_action_print_non_int_return_int_as_exit_code_with_none():
    """print_non_int_return_int_as_exit_code: returns 0 for None without printing."""
    app = App(result_action="print_non_int_return_int_as_exit_code")

    @app.command
    def do_nothing() -> None:
        pass

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["do-nothing"])

    assert result == 0
    assert buf.getvalue() == ""


def test_result_action_print_non_int_return_int_as_exit_code_with_list():
    """print_non_int_return_int_as_exit_code: prints list and returns 0."""
    app = App(result_action="print_non_int_return_int_as_exit_code")

    @app.command
    def get_list() -> list:
        return [1, 2, 3]

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-list"])

    assert result == 0
    assert buf.getvalue() == "[1, 2, 3]\n"


def test_result_action_print_non_int_return_int_as_exit_code_with_true():
    """print_non_int_return_int_as_exit_code: True returns 0."""
    app = App(result_action="print_non_int_return_int_as_exit_code")

    @app.command
    def check() -> bool:
        return True

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["check"])

    assert result == 0
    assert buf.getvalue() == ""


def test_result_action_print_non_int_return_int_as_exit_code_with_false():
    """print_non_int_return_int_as_exit_code: False returns 1."""
    app = App(result_action="print_non_int_return_int_as_exit_code")

    @app.command
    def check() -> bool:
        return False

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["check"])

    assert result == 1
    assert buf.getvalue() == ""


# ==============================================================================
# print_str_return_int_as_exit_code tests
# ==============================================================================


def test_result_action_print_str_return_int_as_exit_code_with_string():
    """print_str_return_int_as_exit_code: prints string and returns 0."""
    app = App(result_action="print_str_return_int_as_exit_code")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Alice"])

    assert result == 0
    assert buf.getvalue() == "Hello Alice!\n"


def test_result_action_print_str_return_int_as_exit_code_with_int():
    """print_str_return_int_as_exit_code: returns int as exit code, no print."""
    app = App(result_action="print_str_return_int_as_exit_code")

    @app.command
    def get_exit_code(code: int) -> int:
        return code

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-exit-code", "5"])

    assert result == 5
    assert buf.getvalue() == ""


def test_result_action_print_str_return_int_as_exit_code_with_list():
    """print_str_return_int_as_exit_code: doesn't print non-string objects, returns 0."""
    app = App(result_action="print_str_return_int_as_exit_code")

    @app.command
    def get_list() -> list:
        return [1, 2, 3]

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-list"])

    assert result == 0
    assert buf.getvalue() == ""


def test_result_action_print_str_return_int_as_exit_code_with_true():
    """print_str_return_int_as_exit_code: True returns 0."""
    app = App(result_action="print_str_return_int_as_exit_code")

    @app.command
    def check() -> bool:
        return True

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["check"])

    assert result == 0
    assert buf.getvalue() == ""


def test_result_action_print_str_return_int_as_exit_code_with_false():
    """print_str_return_int_as_exit_code: False returns 1."""
    app = App(result_action="print_str_return_int_as_exit_code")

    @app.command
    def check() -> bool:
        return False

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["check"])

    assert result == 1
    assert buf.getvalue() == ""


# ==============================================================================
# print_str_return_zero tests
# ==============================================================================


def test_result_action_print_str_return_zero_with_string():
    """print_str_return_zero: prints string and returns 0."""
    app = App(result_action="print_str_return_zero")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Alice"])

    assert result == 0
    assert buf.getvalue() == "Hello Alice!\n"


def test_result_action_print_str_return_zero_with_int():
    """print_str_return_zero: doesn't print int, returns 0."""
    app = App(result_action="print_str_return_zero")

    @app.command
    def get_number() -> int:
        return 42

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-number"])

    assert result == 0
    assert buf.getvalue() == ""


# ==============================================================================
# print_non_none_return_int_as_exit_code tests
# ==============================================================================


def test_result_action_print_non_none_return_int_as_exit_code_with_string():
    """print_non_none_return_int_as_exit_code: prints string and returns 0."""
    app = App(result_action="print_non_none_return_int_as_exit_code")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Alice"])

    assert result == 0
    assert buf.getvalue() == "Hello Alice!\n"


def test_result_action_print_non_none_return_int_as_exit_code_with_int():
    """print_non_none_return_int_as_exit_code: prints int but returns it as exit code."""
    app = App(result_action="print_non_none_return_int_as_exit_code")

    @app.command
    def get_number() -> int:
        return 42

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-number"])

    assert result == 42
    assert buf.getvalue() == "42\n"


def test_result_action_print_non_none_return_int_as_exit_code_with_true():
    """print_non_none_return_int_as_exit_code: prints True and returns 0."""
    app = App(result_action="print_non_none_return_int_as_exit_code")

    @app.command
    def check() -> bool:
        return True

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["check"])

    assert result == 0
    assert buf.getvalue() == "True\n"


def test_result_action_print_non_none_return_int_as_exit_code_with_false():
    """print_non_none_return_int_as_exit_code: prints False and returns 1."""
    app = App(result_action="print_non_none_return_int_as_exit_code")

    @app.command
    def check() -> bool:
        return False

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["check"])

    assert result == 1
    assert buf.getvalue() == "False\n"


# ==============================================================================
# print_non_none_return_zero tests
# ==============================================================================


def test_result_action_print_non_none_return_zero_with_string():
    """print_non_none_return_zero: prints string and returns 0."""
    app = App(result_action="print_non_none_return_zero")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Alice"])

    assert result == 0
    assert buf.getvalue() == "Hello Alice!\n"


def test_result_action_print_non_none_return_zero_with_int():
    """print_non_none_return_zero: prints int but returns 0."""
    app = App(result_action="print_non_none_return_zero")

    @app.command
    def get_number() -> int:
        return 42

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-number"])

    assert result == 0
    assert buf.getvalue() == "42\n"


# ==============================================================================
# return_int_as_exit_code_else_zero tests
# ==============================================================================


def test_result_action_return_int_as_exit_code_else_zero_with_string():
    """return_int_as_exit_code_else_zero: doesn't print string, returns 0."""
    app = App(result_action="return_int_as_exit_code_else_zero")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Bob"])

    assert result == 0
    assert buf.getvalue() == ""


def test_result_action_return_int_as_exit_code_else_zero_with_int():
    """return_int_as_exit_code_else_zero: returns int as exit code, no print."""
    app = App(result_action="return_int_as_exit_code_else_zero")

    @app.command
    def get_exit_code(code: int) -> int:
        return code

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-exit-code", "3"])

    assert result == 3
    assert buf.getvalue() == ""


def test_result_action_return_int_as_exit_code_else_zero_with_true():
    """return_int_as_exit_code_else_zero: True returns 0."""
    app = App(result_action="return_int_as_exit_code_else_zero")

    @app.command
    def check() -> bool:
        return True

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["check"])

    assert result == 0
    assert buf.getvalue() == ""


def test_result_action_return_int_as_exit_code_else_zero_with_false():
    """return_int_as_exit_code_else_zero: False returns 1."""
    app = App(result_action="return_int_as_exit_code_else_zero")

    @app.command
    def check() -> bool:
        return False

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["check"])

    assert result == 1
    assert buf.getvalue() == ""


# ==============================================================================
# print_non_int_sys_exit tests
# ==============================================================================


def test_result_action_print_non_int_sys_exit_with_string(monkeypatch):
    """print_non_int_sys_exit: prints and calls sys.exit(0)."""
    app = App(result_action="print_non_int_sys_exit")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["greet", "Alice"])

    assert exit_code == 0
    assert buf.getvalue() == "Hello Alice!\n"


def test_result_action_print_non_int_sys_exit_with_int(monkeypatch):
    """print_non_int_sys_exit: calls sys.exit with int value."""
    app = App(result_action="print_non_int_sys_exit")

    @app.command
    def get_exit_code(code: int) -> int:
        return code

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["get-exit-code", "5"])

    assert exit_code == 5
    assert buf.getvalue() == ""


def test_result_action_print_non_int_sys_exit_with_true(monkeypatch):
    """print_non_int_sys_exit: True calls sys.exit(0)."""
    app = App(result_action="print_non_int_sys_exit")

    @app.command
    def check() -> bool:
        return True

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["check"])

    assert exit_code == 0
    assert buf.getvalue() == ""


def test_result_action_print_non_int_sys_exit_with_false(monkeypatch):
    """print_non_int_sys_exit: False calls sys.exit(1)."""
    app = App(result_action="print_non_int_sys_exit")

    @app.command
    def check() -> bool:
        return False

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["check"])

    assert exit_code == 1
    assert buf.getvalue() == ""


# ==============================================================================
# sys_exit tests
# ==============================================================================


def test_result_action_sys_exit_with_string(monkeypatch):
    """sys_exit: string returns sys.exit(0) without printing."""
    app = App(result_action="sys_exit")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["greet", "Alice"])

    assert exit_code == 0
    assert buf.getvalue() == ""  # Should NOT print


def test_result_action_sys_exit_with_int(monkeypatch):
    """sys_exit: calls sys.exit with int value."""
    app = App(result_action="sys_exit")

    @app.command
    def get_exit_code(code: int) -> int:
        return code

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["get-exit-code", "5"])

    assert exit_code == 5
    assert buf.getvalue() == ""


def test_result_action_sys_exit_with_true(monkeypatch):
    """sys_exit: True calls sys.exit(0)."""
    app = App(result_action="sys_exit")

    @app.command
    def check() -> bool:
        return True

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["check"])

    assert exit_code == 0
    assert buf.getvalue() == ""


def test_result_action_sys_exit_with_false(monkeypatch):
    """sys_exit: False calls sys.exit(1)."""
    app = App(result_action="sys_exit")

    @app.command
    def check() -> bool:
        return False

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["check"])

    assert exit_code == 1
    assert buf.getvalue() == ""


def test_result_action_sys_exit_with_none(monkeypatch):
    """sys_exit: None calls sys.exit(0)."""
    app = App(result_action="sys_exit")

    @app.command
    def do_nothing() -> None:
        pass

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["do-nothing"])

    assert exit_code == 0
    assert buf.getvalue() == ""


# ==============================================================================
# Default and inheritance tests
# ==============================================================================


def test_result_action_default_is_print_non_int_sys_exit():
    """Default result_action should be 'print_non_int_sys_exit'."""
    app = App()

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    # Default mode should print strings and call sys.exit(0)
    buf = StringIO()
    with redirect_stdout(buf):
        with pytest.raises(SystemExit) as exc_info:
            app(["greet", "Charlie"])
    assert exc_info.value.code == 0
    assert buf.getvalue() == "Hello Charlie!\n"


def test_result_action_override_in_call():
    """result_action can be overridden in __call__."""
    app = App(result_action="return_value")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    # Default behavior from App
    result = app(["greet", "Alice"])
    assert result == "Hello Alice!"

    # Override to print_non_int_return_int_as_exit_code
    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Bob"], result_action="print_non_int_return_int_as_exit_code")
    assert result == 0
    assert buf.getvalue() == "Hello Bob!\n"

    # Override to return_int_as_exit_code_else_zero
    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Charlie"], result_action="return_int_as_exit_code_else_zero")
    assert result == 0
    assert buf.getvalue() == ""


def test_result_action_inheritance():
    """result_action inherits from parent app when None and called through parent."""
    parent_app = App(result_action="return_value")

    child_app = App(name="child")  # result_action=None, should inherit
    parent_app.command(child_app)

    @child_app.default
    def greet(name: str) -> str:
        return f"Hello {name}!"

    # Child should inherit parent's return_value mode when called through parent
    result = parent_app(["child", "Alice"])
    assert result == "Hello Alice!"

    # Test with different parent mode
    parent_app2 = App(result_action="return_int_as_exit_code_else_zero")
    child_app2 = App(name="child2")  # result_action=None
    parent_app2.command(child_app2)

    @child_app2.default
    def greet2(name: str) -> str:
        return f"Hello {name}!"

    # Child should inherit parent's silent mode when called through parent
    buf = StringIO()
    with redirect_stdout(buf):
        result = parent_app2(["child2", "Bob"])
    assert result == 0
    assert buf.getvalue() == ""


def test_result_action_none_defaults_to_print_non_int_sys_exit():
    """result_action=None defaults to print_non_int_sys_exit when called standalone."""
    app = App()  # result_action=None

    @app.default
    def greet(name: str) -> str:
        return f"Hello {name}!"

    # Should use default fallback: print_non_int_sys_exit
    buf = StringIO()
    with redirect_stdout(buf):
        with pytest.raises(SystemExit) as exc_info:
            app(["Alice"])
    assert exc_info.value.code == 0
    assert buf.getvalue() == "Hello Alice!\n"


# ==============================================================================
# Meta app tests
# ==============================================================================


def test_result_action_with_meta_app_exit_mode(monkeypatch):
    """result_action with meta app: exit modes should apply at meta level, not inner level."""
    app = App(result_action="print_non_int_sys_exit")

    @app.meta.default
    def meta(*tokens: Annotated[str, Parameter(allow_leading_hyphen=True)]):
        # Inner call should return value, not exit
        result = app(tokens)
        # This should execute (meta function should complete)
        return f"Meta wrapper: {result}"

    @app.default
    def command() -> str:
        return "Hello from command"

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app.meta([])

    # Should print "Meta wrapper: Hello from command"
    assert buf.getvalue() == "Meta wrapper: Hello from command\n"
    # Should call sys.exit at meta level
    assert exit_code == 0


def test_result_action_with_meta_app_return_mode():
    """result_action with meta app: non-exit modes should work correctly."""
    app = App(result_action="print_non_int_return_int_as_exit_code")

    @app.meta.default
    def meta(*tokens: Annotated[str, Parameter(allow_leading_hyphen=True)]):
        # Inner call should return value
        result = app(tokens)
        # This should execute (meta function should complete)
        return f"Meta: {result}"

    @app.default
    def command() -> str:
        return "Hello"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app.meta([])

    # Inner command returns "Hello", meta wraps it as "Meta: Hello"
    assert result == 0
    assert buf.getvalue() == "Meta: Hello\n"


# ==============================================================================
# Callable result_action tests
# ==============================================================================


def test_result_action_callable_basic():
    """Callable result_action: can use custom function."""

    def custom_handler(result):
        return f"CUSTOM: {result}"

    app = App(result_action=custom_handler)

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    result = app(["greet", "Alice"])
    assert result == "CUSTOM: Hello Alice!"


def test_result_action_callable_with_print():
    """Callable result_action: can print and return exit code."""

    def custom_handler(result):
        if result:
            print(f"SUCCESS: {result}")
            return 0
        else:
            print("FAILED")
            return 1

    app = App(result_action=custom_handler)

    @app.command
    def process() -> str:
        return "Done"

    buf = StringIO()
    with redirect_stdout(buf):
        exit_code = app(["process"])

    assert exit_code == 0
    assert buf.getvalue() == "SUCCESS: Done\n"


def test_result_action_callable_transforms_result():
    """Callable result_action: can transform result before returning."""

    def uppercase_handler(result):
        if isinstance(result, str):
            return result.upper()
        return result

    app = App(result_action=uppercase_handler)

    @app.command
    def greet() -> str:
        return "hello world"

    result = app(["greet"])
    assert result == "HELLO WORLD"


def test_result_action_callable_handles_none():
    """Callable result_action: handles None results."""

    def none_handler(result):
        return result if result is not None else "DEFAULT"

    app = App(result_action=none_handler)

    @app.command
    def no_return() -> None:
        pass

    result = app(["no-return"])
    assert result == "DEFAULT"


def test_result_action_callable_override_in_call():
    """Callable result_action: can be overridden in __call__."""

    def handler1(result):
        return f"HANDLER1: {result}"

    def handler2(result):
        return f"HANDLER2: {result}"

    app = App(result_action=handler1)

    @app.command
    def cmd() -> str:
        return "test"

    result1 = app(["cmd"])
    assert result1 == "HANDLER1: test"

    result2 = app(["cmd"], result_action=handler2)
    assert result2 == "HANDLER2: test"


def test_result_action_callable_with_lambda():
    """Callable result_action: works with lambda functions."""
    app = App(result_action=lambda x: x * 2 if isinstance(x, int) else x)

    @app.command
    def double(n: int) -> int:
        return n

    result = app(["double", "5"])
    assert result == 10


# ==============================================================================
# return_none tests
# ==============================================================================


def test_result_action_return_none_with_string():
    """return_none: returns None regardless of result."""
    app = App(result_action="return_none")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Alice"])

    assert result is None
    assert buf.getvalue() == ""


def test_result_action_return_none_with_int():
    """return_none: returns None regardless of result."""
    app = App(result_action="return_none")

    @app.command
    def get_number() -> int:
        return 42

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-number"])

    assert result is None
    assert buf.getvalue() == ""


# ==============================================================================
# return_zero tests
# ==============================================================================


def test_result_action_return_zero_with_string():
    """return_zero: returns 0 regardless of result."""
    app = App(result_action="return_zero")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Alice"])

    assert result == 0
    assert buf.getvalue() == ""


def test_result_action_return_zero_with_int():
    """return_zero: returns 0 regardless of result."""
    app = App(result_action="return_zero")

    @app.command
    def get_number() -> int:
        return 42

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-number"])

    assert result == 0
    assert buf.getvalue() == ""


# ==============================================================================
# print_return_zero tests
# ==============================================================================


def test_result_action_print_return_zero_with_string():
    """print_return_zero: prints result and returns 0."""
    app = App(result_action="print_return_zero")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Alice"])

    assert result == 0
    assert buf.getvalue() == "Hello Alice!\n"


def test_result_action_print_return_zero_with_int():
    """print_return_zero: prints result and returns 0."""
    app = App(result_action="print_return_zero")

    @app.command
    def get_number() -> int:
        return 42

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-number"])

    assert result == 0
    assert buf.getvalue() == "42\n"


def test_result_action_print_return_zero_with_none():
    """print_return_zero: prints None and returns 0."""
    app = App(result_action="print_return_zero")

    @app.command
    def do_nothing() -> None:
        pass

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["do-nothing"])

    assert result == 0
    assert buf.getvalue() == "None\n"


# ==============================================================================
# sys_exit_zero tests
# ==============================================================================


def test_result_action_sys_exit_zero_with_string(monkeypatch):
    """sys_exit_zero: calls sys.exit(0) regardless of result."""
    app = App(result_action="sys_exit_zero")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["greet", "Alice"])

    assert exit_code == 0
    assert buf.getvalue() == ""


def test_result_action_sys_exit_zero_with_int(monkeypatch):
    """sys_exit_zero: calls sys.exit(0) even with int result."""
    app = App(result_action="sys_exit_zero")

    @app.command
    def get_number() -> int:
        return 42

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["get-number"])

    assert exit_code == 0
    assert buf.getvalue() == ""


# ==============================================================================
# print_sys_exit_zero tests
# ==============================================================================


def test_result_action_print_sys_exit_zero_with_string(monkeypatch):
    """print_sys_exit_zero: prints result and calls sys.exit(0)."""
    app = App(result_action="print_sys_exit_zero")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["greet", "Alice"])

    assert exit_code == 0
    assert buf.getvalue() == "Hello Alice!\n"


def test_result_action_print_sys_exit_zero_with_int(monkeypatch):
    """print_sys_exit_zero: prints result and calls sys.exit(0)."""
    app = App(result_action="print_sys_exit_zero")

    @app.command
    def get_number() -> int:
        return 42

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["get-number"])

    assert exit_code == 0
    assert buf.getvalue() == "42\n"


# ==============================================================================
# call_if_callable tests
# ==============================================================================


def test_result_action_call_if_callable_with_callable():
    """call_if_callable: calls the result if it's callable."""
    app = App(result_action="call_if_callable")

    @app.command
    def get_greeter(name: str):
        def greeter():
            return f"Hello {name}!"

        return greeter

    result = app(["get-greeter", "Alice"])
    assert result == "Hello Alice!"


def test_result_action_call_if_callable_with_non_callable():
    """call_if_callable: returns non-callable result as-is."""
    app = App(result_action="call_if_callable")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    result = app(["greet", "Bob"])
    assert result == "Hello Bob!"


def test_result_action_call_if_callable_with_none():
    """call_if_callable: returns None as-is."""
    app = App(result_action="call_if_callable")

    @app.command
    def do_nothing() -> None:
        pass

    result = app(["do-nothing"])
    assert result is None


def test_result_action_call_if_callable_with_dataclass():
    """call_if_callable: works with dataclass __call__ pattern."""
    import dataclasses as dc

    app = App(result_action="call_if_callable")

    @app.command
    @dc.dataclass
    class Hello:
        """Say hello."""

        name: str = "World"
        _: dc.KW_ONLY
        formal: bool = False

        def __call__(self):
            return f"{'Hello' if self.formal else 'Hey'} {self.name}."

    result = app(["hello", "Jude"])
    assert result == "Hey Jude."

    result = app(["hello", "Sir", "--formal"])
    assert result == "Hello Sir."


# ==============================================================================
# Sequence result_action tests
# ==============================================================================


def test_result_action_sequence_single_element():
    """Sequence with single element should work like single value."""
    app = App(result_action=["return_value"])

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    result = app(["greet", "Alice"])
    assert result == "Hello Alice!"


def test_result_action_sequence_multiple_callables():
    """Sequence with multiple callables should chain results."""
    call_order = []

    def handler1(result):
        call_order.append("handler1")
        return f"[1:{result}]"

    def handler2(result):
        call_order.append("handler2")
        return f"[2:{result}]"

    app = App(result_action=[handler1, handler2])

    @app.command
    def cmd() -> str:
        return "test"

    result = app(["cmd"])
    assert result == "[2:[1:test]]"
    assert call_order == ["handler1", "handler2"]


def test_result_action_empty_sequence_raises_error():
    """Empty sequence should raise ValueError."""
    with pytest.raises(ValueError, match="result_action cannot be an empty sequence"):
        App(result_action=[])


def test_result_action_call_if_callable_composition(monkeypatch):
    """Composition: call_if_callable with print_non_int_sys_exit for dataclass pattern."""
    import dataclasses as dc

    app = App(result_action=["call_if_callable", "print_non_int_sys_exit"])

    @app.command
    @dc.dataclass
    class Hello:
        """Say hello."""

        name: str = "World"
        _: dc.KW_ONLY
        formal: bool = False

        def __call__(self):
            return f"{'Hello' if self.formal else 'Hey'} {self.name}."

    exit_code = None

    def mock_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr("sys.exit", mock_exit)

    buf = StringIO()
    with redirect_stdout(buf):
        app(["hello", "Jude"])

    assert buf.getvalue() == "Hey Jude.\n"
    assert exit_code == 0
