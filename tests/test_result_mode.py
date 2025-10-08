"""Tests for App result_mode parameter with explicit naming.

Result Mode Behavior Table:
========================================================================================
Mode                           | str result  | int result | None | bool result | other
----------------------------------------------------------------------------------------
return_value                   | return str  | return int | None | return bool | return
print_non_int_return_exit_code | print → 0   | return int | 0    | print → 0   | print → 0
print_str_return_exit_code     | print → 0   | return int | 0    | 0 (silent)  | 0 (silent)
print_str_return_zero          | print → 0   | 0 (silent) | 0    | 0 (silent)  | 0 (silent)
print_non_none_return_exit_code| print → 0   | print & int| 0    | print → 0   | print → 0
print_non_none_return_zero     | print → 0   | print → 0  | 0    | print → 0   | print → 0
return_exit_code        | 0 (silent)  | return int | 0    | 0 (silent)  | 0 (silent)
print_non_int_call_sys_exit    | print exit  | sys.exit   | exit | print exit  | print exit
return_bool_as_exit_code       | print → 0   | return int | 0    | T→0 / F→1   | print → 0
========================================================================================
"""

from contextlib import redirect_stdout
from io import StringIO

from cyclopts import App

# ==============================================================================
# return_value tests
# ==============================================================================


def test_result_mode_return_value_with_string():
    """return_value: returns string unchanged."""
    app = App(result_mode="return_value")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    result = app(["greet", "Alice"])
    assert result == "Hello Alice!"


def test_result_mode_return_value_with_int():
    """return_value: returns int unchanged."""
    app = App(result_mode="return_value")

    @app.command
    def double(number: int) -> int:
        return number * 2

    result = app(["double", "5"])
    assert result == 10


def test_result_mode_return_value_with_none():
    """return_value: returns None unchanged."""
    app = App(result_mode="return_value")

    @app.command
    def do_nothing() -> None:
        pass

    result = app(["do-nothing"])
    assert result is None


# ==============================================================================
# print_non_int_return_exit_code tests
# ==============================================================================


def test_result_mode_print_non_int_return_exit_code_with_string():
    """print_non_int_return_exit_code: prints string and returns 0."""
    app = App(result_mode="print_non_int_return_exit_code")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Bob"])

    assert result == 0
    assert buf.getvalue() == "Hello Bob!\n"


def test_result_mode_print_non_int_return_exit_code_with_int():
    """print_non_int_return_exit_code: returns int as exit code, no print."""
    app = App(result_mode="print_non_int_return_exit_code")

    @app.command
    def get_exit_code(code: int) -> int:
        return code

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-exit-code", "5"])

    assert result == 5
    assert buf.getvalue() == ""


def test_result_mode_print_non_int_return_exit_code_with_none():
    """print_non_int_return_exit_code: returns 0 for None without printing."""
    app = App(result_mode="print_non_int_return_exit_code")

    @app.command
    def do_nothing() -> None:
        pass

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["do-nothing"])

    assert result == 0
    assert buf.getvalue() == ""


def test_result_mode_print_non_int_return_exit_code_with_list():
    """print_non_int_return_exit_code: prints list and returns 0."""
    app = App(result_mode="print_non_int_return_exit_code")

    @app.command
    def get_list() -> list:
        return [1, 2, 3]

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-list"])

    assert result == 0
    assert buf.getvalue() == "[1, 2, 3]\n"


# ==============================================================================
# print_str_return_exit_code tests
# ==============================================================================


def test_result_mode_print_str_return_exit_code_with_string():
    """print_str_return_exit_code: prints string and returns 0."""
    app = App(result_mode="print_str_return_exit_code")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Alice"])

    assert result == 0
    assert buf.getvalue() == "Hello Alice!\n"


def test_result_mode_print_str_return_exit_code_with_int():
    """print_str_return_exit_code: returns int as exit code, no print."""
    app = App(result_mode="print_str_return_exit_code")

    @app.command
    def get_exit_code(code: int) -> int:
        return code

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-exit-code", "5"])

    assert result == 5
    assert buf.getvalue() == ""


def test_result_mode_print_str_return_exit_code_with_list():
    """print_str_return_exit_code: doesn't print non-string objects, returns 0."""
    app = App(result_mode="print_str_return_exit_code")

    @app.command
    def get_list() -> list:
        return [1, 2, 3]

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-list"])

    assert result == 0
    assert buf.getvalue() == ""


# ==============================================================================
# print_str_return_zero tests
# ==============================================================================


def test_result_mode_print_str_return_zero_with_string():
    """print_str_return_zero: prints string and returns 0."""
    app = App(result_mode="print_str_return_zero")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Alice"])

    assert result == 0
    assert buf.getvalue() == "Hello Alice!\n"


def test_result_mode_print_str_return_zero_with_int():
    """print_str_return_zero: doesn't print int, returns 0."""
    app = App(result_mode="print_str_return_zero")

    @app.command
    def get_number() -> int:
        return 42

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-number"])

    assert result == 0
    assert buf.getvalue() == ""


# ==============================================================================
# print_non_none_return_exit_code tests
# ==============================================================================


def test_result_mode_print_non_none_return_exit_code_with_string():
    """print_non_none_return_exit_code: prints string and returns 0."""
    app = App(result_mode="print_non_none_return_exit_code")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Alice"])

    assert result == 0
    assert buf.getvalue() == "Hello Alice!\n"


def test_result_mode_print_non_none_return_exit_code_with_int():
    """print_non_none_return_exit_code: prints int but returns it as exit code."""
    app = App(result_mode="print_non_none_return_exit_code")

    @app.command
    def get_number() -> int:
        return 42

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-number"])

    assert result == 42
    assert buf.getvalue() == "42\n"


# ==============================================================================
# print_non_none_return_zero tests
# ==============================================================================


def test_result_mode_print_non_none_return_zero_with_string():
    """print_non_none_return_zero: prints string and returns 0."""
    app = App(result_mode="print_non_none_return_zero")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Alice"])

    assert result == 0
    assert buf.getvalue() == "Hello Alice!\n"


def test_result_mode_print_non_none_return_zero_with_int():
    """print_non_none_return_zero: prints int but returns 0."""
    app = App(result_mode="print_non_none_return_zero")

    @app.command
    def get_number() -> int:
        return 42

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-number"])

    assert result == 0
    assert buf.getvalue() == "42\n"


# ==============================================================================
# return_exit_code tests
# ==============================================================================


def test_result_mode_return_exit_code_with_string():
    """return_exit_code: doesn't print string, returns 0."""
    app = App(result_mode="return_exit_code")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Bob"])

    assert result == 0
    assert buf.getvalue() == ""


def test_result_mode_return_exit_code_with_int():
    """return_exit_code: returns int as exit code, no print."""
    app = App(result_mode="return_exit_code")

    @app.command
    def get_exit_code(code: int) -> int:
        return code

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-exit-code", "3"])

    assert result == 3
    assert buf.getvalue() == ""


# ==============================================================================
# print_non_int_call_sys_exit tests
# ==============================================================================


def test_result_mode_print_non_int_call_sys_exit_with_string(monkeypatch):
    """print_non_int_call_sys_exit: prints and calls sys.exit(0)."""
    app = App(result_mode="print_non_int_call_sys_exit")

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


def test_result_mode_print_non_int_call_sys_exit_with_int(monkeypatch):
    """print_non_int_call_sys_exit: calls sys.exit with int value."""
    app = App(result_mode="print_non_int_call_sys_exit")

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


def test_result_mode_default_is_print_non_int_return_exit_code():
    """Default result_mode should be 'print_non_int_return_exit_code'."""
    app = App()

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    # Default mode should print strings and return 0
    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Charlie"])
    assert result == 0
    assert buf.getvalue() == "Hello Charlie!\n"


def test_result_mode_override_in_call():
    """result_mode can be overridden in __call__."""
    app = App(result_mode="return_value")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    # Default behavior from App
    result = app(["greet", "Alice"])
    assert result == "Hello Alice!"

    # Override to print_non_int_return_exit_code
    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Bob"], result_mode="print_non_int_return_exit_code")
    assert result == 0
    assert buf.getvalue() == "Hello Bob!\n"

    # Override to return_exit_code
    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Charlie"], result_mode="return_exit_code")
    assert result == 0
    assert buf.getvalue() == ""


def test_result_mode_inheritance():
    """result_mode inherits from parent app when None and called through parent."""
    parent_app = App(result_mode="return_value")

    child_app = App(name="child")  # result_mode=None, should inherit
    parent_app.command(child_app)

    @child_app.default
    def greet(name: str) -> str:
        return f"Hello {name}!"

    # Child should inherit parent's return_value mode when called through parent
    result = parent_app(["child", "Alice"])
    assert result == "Hello Alice!"

    # Test with different parent mode
    parent_app2 = App(result_mode="return_exit_code")
    child_app2 = App(name="child2")  # result_mode=None
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


def test_result_mode_none_defaults_to_print_non_int():
    """result_mode=None defaults to print_non_int_return_exit_code when called standalone."""
    app = App()  # result_mode=None

    @app.default
    def greet(name: str) -> str:
        return f"Hello {name}!"

    # Should use default fallback: print_non_int_return_exit_code
    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["Alice"])
    assert result == 0
    assert buf.getvalue() == "Hello Alice!\n"


# ==============================================================================
# return_bool_as_exit_code tests
# ==============================================================================


def test_result_mode_return_bool_as_exit_code_with_true():
    """return_bool_as_exit_code: True returns 0."""
    app = App(result_mode="return_bool_as_exit_code")

    @app.command
    def check() -> bool:
        return True

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["check"])

    assert result == 0
    assert buf.getvalue() == ""


def test_result_mode_return_bool_as_exit_code_with_false():
    """return_bool_as_exit_code: False returns 1."""
    app = App(result_mode="return_bool_as_exit_code")

    @app.command
    def check() -> bool:
        return False

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["check"])

    assert result == 1
    assert buf.getvalue() == ""


def test_result_mode_return_bool_as_exit_code_with_int():
    """return_bool_as_exit_code: int returns as exit code, no print."""
    app = App(result_mode="return_bool_as_exit_code")

    @app.command
    def get_exit_code(code: int) -> int:
        return code

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["get-exit-code", "42"])

    assert result == 42
    assert buf.getvalue() == ""


def test_result_mode_return_bool_as_exit_code_with_none():
    """return_bool_as_exit_code: None returns 0, no print."""
    app = App(result_mode="return_bool_as_exit_code")

    @app.command
    def do_nothing() -> None:
        pass

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["do-nothing"])

    assert result == 0
    assert buf.getvalue() == ""


def test_result_mode_return_bool_as_exit_code_with_string():
    """return_bool_as_exit_code: string prints and returns 0."""
    app = App(result_mode="return_bool_as_exit_code")

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    buf = StringIO()
    with redirect_stdout(buf):
        result = app(["greet", "Alice"])

    assert result == 0
    assert buf.getvalue() == "Hello Alice!\n"
