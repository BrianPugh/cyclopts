"""Tests for AST-based docstring extraction utilities."""

import sys
from textwrap import dedent

import pytest

from cyclopts.ast_utils import extract_docstring_from_import_path


@pytest.fixture
def importable_tmp_path(tmp_path):
    """Fixture that adds tmp_path to sys.path and cleans up after."""
    sys.path.insert(0, str(tmp_path))
    yield tmp_path
    sys.path.remove(str(tmp_path))
    # Clean up any modules that were imported from tmp_path
    to_remove = [
        name
        for name, mod in sys.modules.items()
        if hasattr(mod, "__file__") and mod.__file__ and str(tmp_path) in mod.__file__
    ]
    for name in to_remove:
        del sys.modules[name]


def test_extract_docstring_stdlib_function():
    docstring = extract_docstring_from_import_path("json:dumps")
    assert "Serialize" in docstring or "JSON" in docstring


def test_extract_docstring_invalid_format_no_colon():
    with pytest.raises(ValueError, match="Invalid import path format"):
        extract_docstring_from_import_path("invalid_path")


def test_extract_docstring_invalid_format_empty_module():
    with pytest.raises(ValueError, match="Invalid import path format"):
        extract_docstring_from_import_path(":func")


def test_extract_docstring_invalid_format_empty_attr():
    with pytest.raises(ValueError, match="Invalid import path format"):
        extract_docstring_from_import_path("module:")


def test_extract_docstring_nonexistent_module():
    with pytest.raises(ValueError, match="Cannot find source"):
        extract_docstring_from_import_path("nonexistent_module_12345:func")


def test_extract_docstring_nonexistent_attribute():
    with pytest.raises(ValueError, match="Cannot find"):
        extract_docstring_from_import_path("os:nonexistent_func_12345")


def test_extract_docstring_function_without_docstring(importable_tmp_path):
    module_path = importable_tmp_path / "test_module.py"
    module_path.write_text("def no_doc(): pass\n")
    docstring = extract_docstring_from_import_path("test_module:no_doc")
    assert docstring == ""


def test_extract_docstring_function_with_docstring(importable_tmp_path):
    module_path = importable_tmp_path / "test_module_doc.py"
    module_path.write_text(
        dedent('''\
        def documented_func():
            """This is a test function.

            It has a longer description too.
            """
    ''')
    )
    docstring = extract_docstring_from_import_path("test_module_doc:documented_func")
    assert "This is a test function." in docstring
    assert "longer description" in docstring


def test_extract_docstring_async_function(importable_tmp_path):
    module_path = importable_tmp_path / "test_async_func_module.py"
    module_path.write_text(
        dedent('''\
        async def async_func():
            """Async function docstring."""
    ''')
    )
    docstring = extract_docstring_from_import_path("test_async_func_module:async_func")
    assert docstring == "Async function docstring."


def test_extract_docstring_class_docstring(importable_tmp_path):
    module_path = importable_tmp_path / "test_class.py"
    module_path.write_text(
        dedent('''\
        class MyClass:
            """Class level docstring."""
    ''')
    )
    docstring = extract_docstring_from_import_path("test_class:MyClass")
    assert docstring == "Class level docstring."


def test_extract_docstring_decorated_function(importable_tmp_path):
    """Decorators should not affect docstring extraction."""
    module_path = importable_tmp_path / "test_decorated.py"
    module_path.write_text(
        dedent('''\
        def decorator(f):
            return f

        @decorator
        def decorated_func():
            """Decorated function docstring."""
    ''')
    )
    docstring = extract_docstring_from_import_path("test_decorated:decorated_func")
    assert docstring == "Decorated function docstring."


def test_extract_docstring_nested_class_method(importable_tmp_path):
    module_path = importable_tmp_path / "test_nested.py"
    module_path.write_text(
        dedent('''\
        class MyClass:
            def method(self):
                """Method docstring."""
    ''')
    )
    docstring = extract_docstring_from_import_path("test_nested:MyClass.method")
    assert docstring == "Method docstring."
