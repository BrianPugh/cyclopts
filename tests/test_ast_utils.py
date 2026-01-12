"""Tests for AST-based docstring extraction utilities."""

import sys
from textwrap import dedent

import pytest

from cyclopts.ast_utils import (
    classify_type_for_negatives,
    extract_docstring_from_import_path,
    extract_signature_from_import_path,
)


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


# ============================================================================
# Type Classification Tests
# ============================================================================


class TestClassifyTypeForNegatives:
    """Tests for classify_type_for_negatives function."""

    def test_simple_bool(self):
        assert classify_type_for_negatives("bool") == "bool"
        # Case-sensitive: Bool (capitalized) is treated as a user-defined type, not the builtin
        assert classify_type_for_negatives("Bool") == "other"

    def test_simple_iterable(self):
        assert classify_type_for_negatives("list") == "iterable"
        assert classify_type_for_negatives("set") == "iterable"
        assert classify_type_for_negatives("tuple") == "iterable"
        assert classify_type_for_negatives("Sequence") == "iterable"

    def test_other_types(self):
        assert classify_type_for_negatives("str") == "other"
        assert classify_type_for_negatives("int") == "other"
        assert classify_type_for_negatives("MyClass") == "other"

    def test_optional_bool(self):
        assert classify_type_for_negatives("Optional[bool]") == "bool"
        assert classify_type_for_negatives("bool | None") == "bool"

    def test_optional_iterable(self):
        assert classify_type_for_negatives("Optional[list]") == "iterable"
        assert classify_type_for_negatives("list | None") == "iterable"

    def test_annotated_bool(self):
        assert classify_type_for_negatives("Annotated[bool, Parameter()]") == "bool"

    def test_annotated_iterable(self):
        assert classify_type_for_negatives("Annotated[list[str], Parameter()]") == "iterable"

    def test_list_of_bool(self):
        # list[bool] should use bool negatives (--no-flag adds False to list)
        assert classify_type_for_negatives("list[bool]") == "bool"
        assert classify_type_for_negatives("set[bool]") == "bool"

    def test_list_of_other(self):
        assert classify_type_for_negatives("list[str]") == "iterable"
        assert classify_type_for_negatives("list[int]") == "iterable"

    def test_nested_optional(self):
        assert classify_type_for_negatives("Optional[Optional[bool]]") == "bool"

    def test_union_with_none(self):
        assert classify_type_for_negatives("Union[bool, None]") == "bool"
        assert classify_type_for_negatives("Union[list, None]") == "iterable"

    def test_union_multiple_types(self):
        # Multiple non-None types -> "other"
        assert classify_type_for_negatives("Union[bool, str]") == "other"
        assert classify_type_for_negatives("bool | str") == "other"

    def test_empty_string(self):
        assert classify_type_for_negatives("") == "other"

    def test_invalid_syntax(self):
        assert classify_type_for_negatives("not valid python[") == "other"

    def test_forward_reference(self):
        # Forward references in quotes
        assert classify_type_for_negatives('"bool"') == "bool"
        assert classify_type_for_negatives("'list[str]'") == "iterable"

    def test_typing_module_prefix(self):
        assert classify_type_for_negatives("typing.List") == "iterable"
        assert classify_type_for_negatives("typing.Sequence") == "iterable"


# ============================================================================
# Type Alias Resolution Tests
# ============================================================================


class TestTypeAliasResolution:
    """Tests for type alias resolution across modules."""

    def test_same_file_alias(self, importable_tmp_path):
        """Test resolving a type alias defined in the same file."""
        source = dedent('''\
            from typing import Annotated
            from cyclopts import Parameter

            NoNegBool = Annotated[bool, Parameter(negative=())]

            def func(flag: NoNegBool = False):
                """Test function."""
                pass
            ''')
        module_path = importable_tmp_path / "same_file_alias.py"
        module_path.write_text(source)

        sig = extract_signature_from_import_path("same_file_alias:func")
        assert "flag" in sig.resolved_aliases
        assert sig.resolved_aliases["flag"].base_type_str == "bool"
        # Parameter should have empty negative tuple
        assert "flag" in sig.parameters
        assert sig.parameters["flag"].negative == ()

    def test_imported_alias(self, importable_tmp_path):
        """Test resolving a type alias imported from another module."""
        # Create the types module
        types_source = dedent("""\
            from typing import Annotated
            from cyclopts import Parameter

            NoNegBool = Annotated[bool, Parameter(negative=())]
            """)
        (importable_tmp_path / "my_types.py").write_text(types_source)

        # Create the module that imports the alias
        source = dedent('''\
            from my_types import NoNegBool

            def func(flag: NoNegBool = False):
                """Test function."""
                pass
            ''')
        (importable_tmp_path / "imported_alias.py").write_text(source)

        sig = extract_signature_from_import_path("imported_alias:func")
        assert "flag" in sig.resolved_aliases
        assert sig.resolved_aliases["flag"].base_type_str == "bool"

    def test_reexported_alias(self, importable_tmp_path):
        """Test resolving an alias re-exported through __init__.py."""
        # Create package structure
        pkg_dir = importable_tmp_path / "mypkg"
        pkg_dir.mkdir()

        # Base module with the actual definition
        base_source = dedent("""\
            from typing import Annotated
            from cyclopts import Parameter

            CustomBool = Annotated[bool, Parameter(help="Custom bool")]
            """)
        (pkg_dir / "base.py").write_text(base_source)

        # __init__.py re-exports the alias
        init_source = "from .base import CustomBool\n"
        (pkg_dir / "__init__.py").write_text(init_source)

        # Module that imports from the package
        source = dedent('''\
            from mypkg import CustomBool

            def func(flag: CustomBool = False):
                """Test function."""
                pass
            ''')
        (importable_tmp_path / "reexport_test.py").write_text(source)

        sig = extract_signature_from_import_path("reexport_test:func")
        assert "flag" in sig.resolved_aliases
        assert sig.resolved_aliases["flag"].base_type_str == "bool"


# ============================================================================
# Python 3.12+ Type Statement Tests
# ============================================================================


@pytest.mark.skipif(sys.version_info < (3, 12), reason="Requires Python 3.12+")
class TestPython312TypeStatement:
    """Tests for Python 3.12+ 'type X = ...' syntax."""

    def test_type_statement_alias(self, importable_tmp_path):
        """Test resolving a type alias using Python 3.12+ type statement."""
        source = dedent('''\
            from typing import Annotated
            from cyclopts import Parameter

            type NoNegBool = Annotated[bool, Parameter(negative=())]

            def func(flag: NoNegBool = False):
                """Test function."""
                pass
            ''')
        module_path = importable_tmp_path / "type_statement_test.py"
        module_path.write_text(source)

        sig = extract_signature_from_import_path("type_statement_test:func")
        assert "flag" in sig.resolved_aliases
        assert sig.resolved_aliases["flag"].base_type_str == "bool"
        assert "flag" in sig.parameters
        assert sig.parameters["flag"].negative == ()

    def test_type_statement_simple_alias(self, importable_tmp_path):
        """Test simple type alias without Annotated."""
        source = dedent('''\
            type IntList = list[int]

            def func(items: IntList):
                """Test function."""
                pass
            ''')
        module_path = importable_tmp_path / "simple_type_statement.py"
        module_path.write_text(source)

        sig = extract_signature_from_import_path("simple_type_statement:func")
        assert "items" in sig.resolved_aliases
        assert "list" in sig.resolved_aliases["items"].base_type_str.lower()


# ============================================================================
# Signature Extraction Tests
# ============================================================================


class TestSignatureExtraction:
    """Tests for extract_signature_from_import_path."""

    def test_basic_signature(self, importable_tmp_path):
        """Test extracting a basic function signature."""
        source = dedent('''\
            def func(name: str, count: int = 10):
                """A test function.

                Parameters
                ----------
                name
                    The name parameter.
                count
                    The count parameter.
                """
                pass
            ''')
        (importable_tmp_path / "basic_sig.py").write_text(source)

        sig = extract_signature_from_import_path("basic_sig:func")
        assert "A test function" in sig.docstring
        assert "name" in sig.fields
        assert "count" in sig.fields
        assert sig.fields["name"].required is True
        assert sig.fields["count"].required is False
        assert sig.fields["count"].default == 10

    def test_keyword_only_args(self, importable_tmp_path):
        """Test extracting keyword-only arguments."""
        source = dedent('''\
            def func(pos: str, *, kw_only: int = 5):
                """Test function."""
                pass
            ''')
        (importable_tmp_path / "kw_only_sig.py").write_text(source)

        sig = extract_signature_from_import_path("kw_only_sig:func")
        assert sig.fields["pos"].is_positional is True
        assert sig.fields["kw_only"].is_positional is False

    def test_var_positional_and_keyword(self, importable_tmp_path):
        """Test extracting *args and **kwargs."""
        source = dedent('''\
            def func(*args: str, **kwargs: int):
                """Test function."""
                pass
            ''')
        (importable_tmp_path / "var_args_sig.py").write_text(source)

        sig = extract_signature_from_import_path("var_args_sig:func")
        assert "args" in sig.fields
        assert "kwargs" in sig.fields

    def test_docstring_parameter_help(self, importable_tmp_path):
        """Test that parameter help is extracted from docstring."""
        source = dedent('''\
            def func(name: str):
                """A test function.

                Parameters
                ----------
                name
                    The name of the user.
                """
                pass
            ''')
        (importable_tmp_path / "docstring_help.py").write_text(source)

        sig = extract_signature_from_import_path("docstring_help:func")
        assert sig.fields["name"].help == "The name of the user."

    def test_unevaluable_default(self, importable_tmp_path):
        """Test that unevaluable defaults are wrapped in UnevaluableDefault."""
        from cyclopts.ast_utils import UnevaluableDefault

        source = dedent('''\
            def get_default():
                return 42

            def func(value: int = get_default()):
                """Test function."""
                pass
            ''')
        (importable_tmp_path / "unevaluable_default.py").write_text(source)

        sig = extract_signature_from_import_path("unevaluable_default:func")
        default = sig.fields["value"].default
        assert isinstance(default, UnevaluableDefault)
        assert str(default) == "get_default()"
        assert repr(default) == "UnevaluableDefault('get_default()')"

    def test_stringified_annotation_pep563(self, importable_tmp_path):
        """Test that stringified annotations (PEP 563) are properly parsed."""
        source = dedent('''\
            from __future__ import annotations
            from typing import Annotated
            from cyclopts import Parameter

            def func(flag: Annotated[bool, Parameter(negative=())]):
                """Test function."""
                pass
            ''')
        (importable_tmp_path / "pep563_test.py").write_text(source)

        sig = extract_signature_from_import_path("pep563_test:func")
        assert "flag" in sig.resolved_aliases
        assert sig.resolved_aliases["flag"].base_type_str == "bool"
        assert "flag" in sig.parameters
        assert sig.parameters["flag"].negative == ()


class TestDeepReexportResolution:
    """Tests for deep re-export chains (MAX_ALIAS_RESOLUTION_DEPTH = 5)."""

    def test_deep_reexport_chain(self, importable_tmp_path):
        """Test resolving aliases through multiple levels of re-exports."""
        # Create a deep package structure:
        # app/cli/commands.py -> app/types/__init__.py -> app/types/aliases.py
        #   -> shared/types/__init__.py -> shared/types/base.py

        # shared/types/base.py - actual definition
        shared_types = importable_tmp_path / "shared" / "types"
        shared_types.mkdir(parents=True)
        (shared_types / "base.py").write_text(
            dedent("""\
            from typing import Annotated
            from cyclopts import Parameter

            DeepBool = Annotated[bool, Parameter(help="Deep bool")]
            """)
        )

        # shared/types/__init__.py - re-export
        (shared_types / "__init__.py").write_text("from .base import DeepBool\n")

        # shared/__init__.py
        (importable_tmp_path / "shared" / "__init__.py").write_text("")

        # app/types/aliases.py - import from shared
        app_types = importable_tmp_path / "app" / "types"
        app_types.mkdir(parents=True)
        (app_types / "aliases.py").write_text("from shared.types import DeepBool\n")

        # app/types/__init__.py - re-export
        (app_types / "__init__.py").write_text("from .aliases import DeepBool\n")

        # app/__init__.py
        (importable_tmp_path / "app" / "__init__.py").write_text("")

        # app/cli/commands.py - use the alias
        app_cli = importable_tmp_path / "app" / "cli"
        app_cli.mkdir(parents=True)
        (app_cli / "__init__.py").write_text("")
        (app_cli / "commands.py").write_text(
            dedent('''\
            from app.types import DeepBool

            def func(flag: DeepBool = False):
                """Test function."""
                pass
            ''')
        )

        sig = extract_signature_from_import_path("app.cli.commands:func")
        assert "flag" in sig.resolved_aliases
        assert sig.resolved_aliases["flag"].base_type_str == "bool"


class TestUnevaluableDefaultEquality:
    """Tests for UnevaluableDefault equality and hashing."""

    def test_equality(self):
        from cyclopts.ast_utils import UnevaluableDefault

        a = UnevaluableDefault("get_default()")
        b = UnevaluableDefault("get_default()")
        c = UnevaluableDefault("other_func()")

        assert a == b
        assert a != c
        assert a != "get_default()"  # Not equal to string

    def test_hashable(self):
        from cyclopts.ast_utils import UnevaluableDefault

        a = UnevaluableDefault("get_default()")
        b = UnevaluableDefault("get_default()")

        # Should be usable in sets/dicts
        s = {a, b}
        assert len(s) == 1
