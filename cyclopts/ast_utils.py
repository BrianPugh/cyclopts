"""AST utilities for extracting information without importing modules.

This module provides functions to extract docstrings, function signatures, and
Parameter/Group metadata from Python source files using the AST module, avoiding
the need to import potentially heavy dependencies. This is used for lazy-loaded
commands to generate help text without triggering imports.

Key Capabilities
----------------
- Extract docstrings from functions/classes without importing
- Extract function signatures (parameter names, types, defaults)
- Resolve type aliases across modules (with depth limit for re-exports)
- Extract ``Parameter(...)`` metadata from ``Annotated[T, Parameter(...)]``
- Classify types for negative flag generation (bool vs iterable vs other)

Type Alias Resolution
---------------------
The module handles common type alias patterns:

1. Same-file: ``NoNegBool = Annotated[bool, Parameter(negative=())]``
2. Imported: ``from myapp.types import NoNegBool``
3. Re-exported: Import chains through ``__init__.py`` files
4. Python 3.12+ type statements: ``type NoNegBool = Annotated[bool, ...]``

Resolution depth is limited to prevent infinite loops in pathological cases.
When resolution fails, the code gracefully falls back to string representation
and defers full type handling to runtime.

Limitations
-----------
The following patterns are NOT supported by AST-based extraction:

- **Star imports**: ``from module import *`` - cannot determine what names are imported
- **Conditional imports**: ``if TYPE_CHECKING: import X`` - conditions not evaluated
- **Dynamic imports**: ``importlib.import_module(name)`` - cannot evaluate at parse time
- **Runtime-computed defaults**: ``def f(x=some_func())`` - functions not called
- **Complex Parameter kwargs**: ``Parameter(converter=my_func)`` - functions skipped
- **Protocol/ABC types**: Cannot determine if a class is bool-like or iterable-like
- **Generic type variables**: ``T = TypeVar('T')`` - not resolved to concrete types

When these patterns are encountered, the code gracefully degrades:

- For type aliases: Falls back to string representation
- For Parameter extraction: Uses default Parameter values
- For type classification: Returns "other" (no negatives generated)

Caching
-------
Module ASTs are cached using ``functools.lru_cache`` with a limit of 128 entries.
Resolved type aliases are cached using a bounded LRU cache with a limit of 512 entries.

Usage
-----
Primary entry points:

- :func:`extract_docstring_from_import_path`: Get docstring without importing
- :func:`extract_signature_from_import_path`: Get full signature info
- :func:`classify_type_for_negatives`: Classify type for negative flag behavior
"""

import ast
import importlib.util
import inspect
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cyclopts.field_info import FieldInfo
from cyclopts.utils import LRUCache

if TYPE_CHECKING:
    from cyclopts.group import Group
    from cyclopts.parameter import Parameter

# Safety limit to prevent runaway recursion in pathological cases.
# Depth of 5 covers complex package structures with multiple levels of re-exports:
#   app/cli/commands.py → app/types/__init__.py → app/types/aliases.py
#   → shared/types/__init__.py → shared/types/base.py
# This handles the common pattern and provides buffer for deeper nesting.
MAX_ALIAS_RESOLUTION_DEPTH = 5

# Recognized type names that don't need resolution (case-sensitive).
# Split into categories to distinguish true Python builtins from typing/stdlib imports.
#
# True Python builtins - always available without import:
_TRUE_PYTHON_BUILTINS = frozenset(
    {
        "bool",
        "int",
        "float",
        "str",
        "bytes",
        "bytearray",
        "list",
        "dict",
        "set",
        "frozenset",
        "tuple",
        "type",
        "object",
    }
)

# typing module types - require `from typing import X`:
_TYPING_MODULE_TYPES = frozenset(
    {
        # Core typing constructs
        "Any",
        "Optional",
        "Union",
        "Literal",
        "Annotated",
        # Old-style generic aliases (typing.List, typing.Dict, etc.)
        "List",
        "Dict",
        "Set",
        "FrozenSet",
        "Tuple",
        "Type",
        # Abstract types
        "Sequence",
        "Iterable",
        "Collection",
        "Mapping",
        "Callable",
    }
)

# Other stdlib types:
_STDLIB_TYPES = frozenset(
    {
        "None",  # Special None type
        "NoneType",  # types.NoneType
        "Path",  # pathlib.Path
    }
)

# Combined set of all recognized type names (case-sensitive)
_RECOGNIZED_TYPE_NAMES = _TRUE_PYTHON_BUILTINS | _TYPING_MODULE_TYPES | _STDLIB_TYPES

# Cache size limits for lru_cache decorators
_MODULE_AST_CACHE_SIZE = 128
_ALIAS_CACHE_SIZE = 512

# LRU cache for resolved aliases (keyed by (module_path, name))
_alias_cache: LRUCache[tuple[str, str], "ResolvedAlias"] = LRUCache(_ALIAS_CACHE_SIZE)

# Type names that indicate bool-like behavior (case-sensitive).
# Only the lowercase Python builtin is recognized.
_BOOL_TYPE_NAMES = frozenset({"bool"})

# Type names that indicate iterable behavior (case-sensitive).
# Includes both Python builtins (lowercase) and typing module types (capitalized).
_ITERABLE_TYPE_NAMES = frozenset(
    {
        # Python builtins (lowercase)
        "list",
        "set",
        "tuple",
        "frozenset",
        # typing module types (capitalized)
        "List",
        "Set",
        "Tuple",
        "FrozenSet",
        "Sequence",
        "Iterable",
        "Collection",
    }
)

# Parameter kwargs that can be safely skipped during AST extraction.
# These only affect runtime behavior (parsing, conversion, validation)
# and do not influence help text generation.
_PARAMETER_KWARGS_SAFE_TO_SKIP = frozenset(
    {
        "converter",  # Runtime type conversion function
        "validator",  # Runtime validation function
        "alias",  # Alternative CLI names (not displayed in help)
        "allow_leading_hyphen",  # Parsing behavior only
        "env_var_split",  # Runtime env var parsing function
        "accepts_keys",  # Parsing behavior for dict-like types
        "consume_multiple",  # Parsing behavior
        "json_dict",  # Parsing behavior
        "json_list",  # Parsing behavior
        "n_tokens",  # Parsing behavior
        "name_transform",  # Usually a function; default works for help
    }
)


class UnresolvableTypeAliasError(Exception):
    """Raised when a type alias cannot be resolved via AST."""


class UnevaluableDefault:
    """Sentinel for default values that cannot be evaluated at AST parse time.

    When a function parameter has a default value that involves function calls
    or other runtime expressions (e.g., ``def f(x=get_default())``), we cannot
    evaluate it statically. This class wraps the source representation so that:

    1. It can be distinguished from actual string defaults via ``isinstance()``
    2. ``str(default)`` still shows something meaningful in help text
    3. Code checking ``default is inspect.Parameter.empty`` works correctly

    Parameters
    ----------
    source
        The source code representation of the default value (e.g., "get_default()").
    """

    __slots__ = ("source",)

    def __init__(self, source: str):
        self.source = source

    def __str__(self) -> str:
        return self.source

    def __repr__(self) -> str:
        return f"UnevaluableDefault({self.source!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnevaluableDefault):
            return self.source == other.source
        return False

    def __hash__(self) -> int:
        return hash((UnevaluableDefault, self.source))


@dataclass
class ResolvedAlias:
    """Result of resolving a type annotation via AST."""

    base_type_str: str
    """The base type as a string (e.g., "bool", "list[str]")."""

    parameter: "Parameter | None" = None
    """Extracted Parameter from Annotated, if any."""


@dataclass
class ASTSignature:
    """Complete signature info extracted from AST."""

    docstring: str
    """Function/class docstring."""

    fields: dict[str, FieldInfo] = field(default_factory=dict)
    """Field info for each parameter, keyed by parameter name."""

    parameters: dict[str, "Parameter"] = field(default_factory=dict)
    """Extracted Parameter objects, keyed by parameter name."""

    resolved_aliases: dict[str, ResolvedAlias] = field(default_factory=dict)
    """Resolved type aliases, keyed by parameter name."""


def _get_module_source_path(module_path: str) -> Path | None:
    """Get the source file path for a module without importing it.

    Uses importlib.util.find_spec() which locates modules without executing them.
    Falls back to searching sys.path if find_spec fails (e.g., module already
    loaded with a sentinel).
    """
    try:
        spec = importlib.util.find_spec(module_path)
        if spec is not None and spec.origin is not None:
            origin = Path(spec.origin)
            if origin.suffix == ".py":
                return origin
    except (ImportError, ModuleNotFoundError, ValueError):
        pass

    # Fallback: search sys.path for the module source file
    # This handles cases where a sentinel module is in sys.modules
    module_parts = module_path.split(".")
    for search_path in sys.path:
        if not search_path:
            continue
        search_dir = Path(search_path)
        if not search_dir.is_dir():
            continue

        # Try as a package (__init__.py)
        potential_package = search_dir.joinpath(*module_parts, "__init__.py")
        if potential_package.is_file():
            return potential_package

        # Try as a module (.py file)
        if len(module_parts) > 1:
            potential_module = search_dir.joinpath(*module_parts[:-1], f"{module_parts[-1]}.py")
        else:
            potential_module = search_dir / f"{module_parts[0]}.py"
        if potential_module.is_file():
            return potential_module

    return None


def _parse_module_ast(source_path: Path) -> ast.Module | None:
    """Parse a Python source file into an AST."""
    try:
        source = source_path.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(source_path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None


def _find_node_by_name(
    tree: ast.Module | ast.ClassDef,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | None:
    """Find a function or class by name in immediate children of an AST node.

    Returns
    -------
    ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | None
        The found node, or None if not found.
    """
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == name:
                return node
    return None


def _resolve_attribute_path(
    tree: ast.Module, attr_path: str
) -> ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | None:
    """Resolve a dotted attribute path in an AST.

    Handles paths like "MyClass.my_method" by traversing the AST.
    """
    parts = attr_path.split(".")
    current: ast.Module | ast.ClassDef = tree

    for i, part in enumerate(parts):
        node = _find_node_by_name(current, part)
        if node is None:
            return None
        if isinstance(node, ast.ClassDef) and i < len(parts) - 1:
            # Continue traversing into the class
            current = node
        else:
            return node

    return None


def _parse_and_find_node(
    import_path: str,
) -> tuple[ast.Module, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef, str]:
    """Parse an import path and find the target AST node.

    Parameters
    ----------
    import_path
        Import path in format "module.path:attribute" or "module.path:Class.method".

    Returns
    -------
    tuple[ast.Module, ast.AST, str]
        (module_ast, target_node, module_path)

    Raises
    ------
    ValueError
        If the import path is invalid, module source can't be found,
        source can't be parsed, or attribute can't be found in AST.
    """
    module_path, _, attr_path = import_path.rpartition(":")
    if not module_path or not attr_path:
        raise ValueError(f"Invalid import path format: {import_path!r}")

    source_path = _get_module_source_path(module_path)
    if source_path is None:
        raise ValueError(f"Cannot find source for module: {module_path!r}")

    tree = _parse_module_ast(source_path)
    if tree is None:
        raise ValueError(f"Cannot parse source file: {source_path}")

    node = _resolve_attribute_path(tree, attr_path)
    if node is None:
        raise ValueError(f"Cannot find {attr_path!r} in AST")

    return tree, node, module_path


def extract_docstring_from_import_path(import_path: str) -> str:
    """Extract a docstring from an import path without importing.

    Parameters
    ----------
    import_path : str
        Import path in format "module.path:attribute" or "module.path:Class.method".

    Returns
    -------
    str
        The docstring, or empty string if no docstring found.

    Raises
    ------
    ValueError
        If the import path is invalid, module source can't be found,
        source can't be parsed, or attribute can't be found in AST.
    """
    _tree, node, _module_path = _parse_and_find_node(import_path)
    return ast.get_docstring(node) or ""


@lru_cache(maxsize=_MODULE_AST_CACHE_SIZE)
def _get_cached_module_ast(module_path: str) -> ast.Module:
    """Get or parse module AST with caching.

    Uses functools.lru_cache for automatic LRU eviction.

    Raises
    ------
    UnresolvableTypeAliasError
        If module source cannot be found or parsed.
    """
    source_path = _get_module_source_path(module_path)
    if source_path is None:
        raise UnresolvableTypeAliasError(f"Cannot find source for module: {module_path!r}")

    tree = _parse_module_ast(source_path)
    if tree is None:
        raise UnresolvableTypeAliasError(f"Cannot parse source file for module: {module_path!r}")

    return tree


def _safe_eval_ast_node(node: ast.expr) -> Any:
    """Safely evaluate an AST node to a Python value.

    Only handles literals and simple constructs that don't require imports.

    Parameters
    ----------
    node
        AST expression node to evaluate.

    Returns
    -------
    Any
        The evaluated Python value.

    Raises
    ------
    UnresolvableTypeAliasError
        If the node cannot be safely evaluated.
    """
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        # Handle True, False, None
        if node.id == "True":
            return True
        if node.id == "False":
            return False
        if node.id == "None":
            return None
        raise UnresolvableTypeAliasError(f"Cannot evaluate name: {node.id}")

    if isinstance(node, ast.List):
        return [_safe_eval_ast_node(elt) for elt in node.elts]

    if isinstance(node, ast.Tuple):
        return tuple(_safe_eval_ast_node(elt) for elt in node.elts)

    if isinstance(node, ast.Set):
        return {_safe_eval_ast_node(elt) for elt in node.elts}

    if isinstance(node, ast.Dict):
        keys = [_safe_eval_ast_node(k) if k is not None else None for k in node.keys]
        values = [_safe_eval_ast_node(v) for v in node.values]
        return dict(zip(keys, values, strict=False))

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            operand = _safe_eval_ast_node(node.operand)
            return -operand
        if isinstance(node.op, ast.UAdd):
            return _safe_eval_ast_node(node.operand)
        if isinstance(node.op, ast.Not):
            return not _safe_eval_ast_node(node.operand)

    if isinstance(node, ast.BinOp):
        # Handle simple binary operations (e.g., for tuple concatenation)
        left = _safe_eval_ast_node(node.left)
        right = _safe_eval_ast_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Mult):
            return left * right

    if isinstance(node, ast.Call):
        # Handle Group(...) and Parameter(...) calls
        return _extract_cyclopts_object_from_call(node)

    raise UnresolvableTypeAliasError(f"Cannot safely evaluate AST node type: {type(node).__name__}")


def _extract_cyclopts_object_from_call(call_node: ast.Call) -> Any:
    """Extract Parameter or Group from an AST Call node.

    Parameters
    ----------
    call_node
        AST Call node representing Parameter(...) or Group(...).

    Returns
    -------
    Parameter | Group
        The instantiated cyclopts object.

    Raises
    ------
    UnresolvableTypeAliasError
        If the call is not a recognized cyclopts object or has unevaluable arguments.
    """
    # Get the function name
    func_name = None
    if isinstance(call_node.func, ast.Name):
        func_name = call_node.func.id
    elif isinstance(call_node.func, ast.Attribute):
        func_name = call_node.func.attr

    if func_name == "Parameter":
        return _extract_parameter_from_call(call_node)
    elif func_name == "Group":
        return _extract_group_from_call(call_node)
    else:
        raise UnresolvableTypeAliasError(f"Unrecognized call: {func_name}")


def _extract_parameter_from_call(call_node: ast.Call) -> "Parameter":
    """Extract Parameter kwargs from AST and instantiate a real Parameter.

    Parameters
    ----------
    call_node
        AST Call node for Parameter(...).

    Returns
    -------
    Parameter
        The instantiated Parameter object.

    Raises
    ------
    UnresolvableTypeAliasError
        If any help-relevant argument cannot be safely evaluated.
    """
    from cyclopts.parameter import Parameter

    kwargs: dict[str, Any] = {}

    # Handle positional arguments (Parameter has `name` as first positional)
    for i, arg in enumerate(call_node.args):
        if i == 0:
            kwargs["name"] = _safe_eval_ast_node(arg)
        else:
            raise UnresolvableTypeAliasError(f"Unexpected positional argument at index {i}")

    # Handle keyword arguments
    for keyword in call_node.keywords:
        if keyword.arg is None:
            # **kwargs expansion - can't handle
            raise UnresolvableTypeAliasError("Cannot handle **kwargs in Parameter call")
        try:
            kwargs[keyword.arg] = _safe_eval_ast_node(keyword.value)
        except UnresolvableTypeAliasError:
            # Only skip kwargs that don't affect help generation.
            # These are runtime-only concerns (parsing, conversion, validation).
            if keyword.arg in _PARAMETER_KWARGS_SAFE_TO_SKIP:
                pass
            else:
                raise

    return Parameter(**kwargs)


def _extract_group_from_call(call_node: ast.Call) -> "Group":
    """Extract Group kwargs from AST and instantiate a real Group.

    Parameters
    ----------
    call_node
        AST Call node for Group(...).

    Returns
    -------
    Group
        The instantiated Group object.

    Raises
    ------
    UnresolvableTypeAliasError
        If any help-relevant argument cannot be safely evaluated.
    """
    from cyclopts.group import Group

    kwargs: dict[str, Any] = {}

    # Handle positional arguments (Group has `name` and `help` as positional)
    for i, arg in enumerate(call_node.args):
        if i == 0:
            kwargs["name"] = _safe_eval_ast_node(arg)
        elif i == 1:
            kwargs["help"] = _safe_eval_ast_node(arg)
        else:
            raise UnresolvableTypeAliasError(f"Unexpected positional argument at index {i}")

    # Handle keyword arguments
    for keyword in call_node.keywords:
        if keyword.arg is None:
            raise UnresolvableTypeAliasError("Cannot handle **kwargs in Group call")
        try:
            kwargs[keyword.arg] = _safe_eval_ast_node(keyword.value)
        except UnresolvableTypeAliasError:
            # Only skip kwargs that don't affect help generation.
            if keyword.arg in _GROUP_KWARGS_SAFE_TO_SKIP:
                pass
            else:
                raise

    return Group(**kwargs)


# Group kwargs that can be safely skipped during AST extraction.
# These only affect runtime behavior and do not influence help text generation.
_GROUP_KWARGS_SAFE_TO_SKIP = frozenset(
    {
        "validator",  # Runtime validation function
    }
)


def _ast_node_to_string(node: ast.expr) -> str:
    """Convert an AST node to its string representation.

    Used for getting the string form of type annotations.
    """
    return ast.unparse(node)


def _find_import_source(
    name: str,
    module_ast: ast.Module,
    module_path: str,
) -> tuple[str, str] | None:
    """Find where a name is imported from.

    Parameters
    ----------
    name
        The name to find the import source for.
    module_ast
        AST of the module where the name is used.
    module_path
        Dotted module path for resolving relative imports.

    Returns
    -------
    tuple[str, str] | None
        (source_module_path, original_name) if found, None otherwise.
    """
    for node in ast.iter_child_nodes(module_ast):
        if isinstance(node, ast.ImportFrom):
            # from x import y, from x import y as z, from .x import y
            for alias in node.names:
                # alias.name is the original name, alias.asname is the alias (if any)
                imported_as = alias.asname if alias.asname else alias.name
                if imported_as == name:
                    # Resolve relative import using Python's import machinery
                    if node.level > 0:
                        # Build the relative import name (e.g., ".foo", "..bar")
                        relative_name = "." * node.level + (node.module or "")
                        try:
                            source_module = importlib.util.resolve_name(relative_name, module_path)
                        except (ValueError, ImportError):
                            # Invalid relative import (e.g., level exceeds module depth)
                            continue
                    else:
                        source_module = node.module or ""

                    # Skip if we couldn't resolve to a valid module path
                    if not source_module:
                        continue

                    return (source_module, alias.name)

        elif isinstance(node, ast.Import):
            # import x, import x as y
            for alias in node.names:
                imported_as = alias.asname if alias.asname else alias.name
                if imported_as == name or name.startswith(f"{imported_as}."):
                    # For `import x` and usage `x.Foo`, return the module
                    return (alias.name, name.split(".", 1)[-1] if "." in name else name)

    return None


def _find_assignment_in_module(
    name: str,
    module_ast: ast.Module,
) -> ast.expr | None:
    """Find `name = <expr>` assignment in a module and return the RHS.

    Handles multiple assignment forms:

    - Regular assignment: ``X = Annotated[bool, ...]``
    - Annotated assignment: ``X: TypeAlias = Annotated[bool, ...]``
    - Python 3.12+ type statement: ``type X = Annotated[bool, ...]``

    Parameters
    ----------
    name
        The name to find the assignment for.
    module_ast
        AST of the module to search.

    Returns
    -------
    ast.expr | None
        The RHS expression if found, None otherwise.
    """
    for node in ast.iter_child_nodes(module_ast):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                if node.value is not None:
                    return node.value
                # For type alias like `X: TypeAlias = ...`, the annotation might be what we want
                # But typically type aliases use regular assignment
        # Python 3.12+ type alias statement: `type X = ...`
        elif hasattr(ast, "TypeAlias") and isinstance(node, ast.TypeAlias):
            if isinstance(node.name, ast.Name) and node.name.id == name:
                return node.value
    return None


def _extract_from_annotation_node(
    node: ast.expr,
    module_ast: ast.Module,
    module_path: str,
    depth: int = 0,
) -> ResolvedAlias:
    """Extract base type and Parameter from an annotation AST node.

    Handles various annotation forms:

    - Simple names: ``bool``, ``str``, ``MyAlias``
    - Subscripts: ``list[str]``, ``Annotated[T, Parameter(...)]``, ``Optional[T]``
    - Union syntax: ``str | None``
    - Attributes: ``typing.Optional``
    - Forward references: ``"MyClass"`` (string annotations)

    This function works together with :func:`_resolve_type_alias` in mutual
    recursion: when a simple name is encountered that isn't a builtin type,
    ``_resolve_type_alias`` is called to find its definition, which may then
    call back to this function to extract the actual type.

    Parameters
    ----------
    node
        AST node representing the type annotation.
    module_ast
        AST of the module containing the annotation.
    module_path
        Dotted module path for resolving imports.
    depth
        Current recursion depth (shared with _resolve_type_alias).

    Returns
    -------
    ResolvedAlias
        The resolved type with base_type_str and optional Parameter.

    Raises
    ------
    UnresolvableTypeAliasError
        If the annotation cannot be resolved within the depth limit.
    """
    if depth > MAX_ALIAS_RESOLUTION_DEPTH:
        raise UnresolvableTypeAliasError(f"Type alias chain too deep (>{MAX_ALIAS_RESOLUTION_DEPTH})")

    # Case 1: Simple name (e.g., `bool`, `str`, or a type alias)
    if isinstance(node, ast.Name):
        name = node.id
        if name in _RECOGNIZED_TYPE_NAMES:
            return ResolvedAlias(base_type_str=name)

        # Try to resolve as type alias
        return _resolve_type_alias(name, module_ast, module_path, depth)

    # Case 2: Subscript (e.g., `list[str]`, `Annotated[T, Parameter(...)]`)
    if isinstance(node, ast.Subscript):
        base_name = _get_type_base_name(node.value)
        if base_name is None:
            # Complex subscript base - just stringify
            return ResolvedAlias(base_type_str=_ast_node_to_string(node))

        # Check for Annotated
        if base_name == "Annotated":
            return _extract_from_annotated(node, module_ast, module_path, depth)

        # Check for Optional (equivalent to Union[T, None])
        if base_name == "Optional":
            inner = _get_subscript_args(node)
            if inner:
                inner_str = _ast_node_to_string(inner[0])
                return ResolvedAlias(base_type_str=f"{inner_str} | None")

        # Check for Union
        if base_name == "Union":
            args = _get_subscript_args(node)
            if args:
                args_str = " | ".join(_ast_node_to_string(arg) for arg in args)
                return ResolvedAlias(base_type_str=args_str)

        # Other subscripts (list[str], dict[str, int], etc.) - just stringify
        return ResolvedAlias(base_type_str=_ast_node_to_string(node))

    # Case 3: BinOp for union syntax (e.g., `str | None`)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return ResolvedAlias(base_type_str=_ast_node_to_string(node))

    # Case 4: Attribute (e.g., `typing.Optional`)
    if isinstance(node, ast.Attribute):
        return ResolvedAlias(base_type_str=node.attr)

    # Case 5: Constant (for string annotations like `"MyClass"` or PEP 563 stringified types)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        # Try to parse the string as a Python expression (handles PEP 563 mode
        # where all annotations are stringified, e.g., "Annotated[bool, Parameter(...)]")
        try:
            inner_tree = ast.parse(node.value, mode="eval")
            return _extract_from_annotation_node(inner_tree.body, module_ast, module_path, depth + 1)
        except SyntaxError:
            # Not valid Python syntax - return the string as-is for display in help
            pass
        # Forward reference or unparsable - return the string as-is
        return ResolvedAlias(base_type_str=node.value)

    # Fallback: stringify the node
    return ResolvedAlias(base_type_str=_ast_node_to_string(node))


def _get_subscript_args(subscript: ast.Subscript) -> list[ast.expr]:
    """Get the arguments from a subscript node (e.g., `list[str]` -> [str])."""
    slice_node = subscript.slice
    if isinstance(slice_node, ast.Tuple):
        return list(slice_node.elts)
    else:
        return [slice_node]


def _extract_from_annotated(
    node: ast.Subscript,
    module_ast: ast.Module,
    module_path: str,
    depth: int,
) -> ResolvedAlias:
    """Extract type and Parameter from Annotated[T, Parameter(...)].

    Parameters
    ----------
    node
        AST Subscript node for Annotated[...].
    module_ast
        AST of the module.
    module_path
        Module path for import resolution.
    depth
        Current recursion depth.

    Returns
    -------
    ResolvedAlias
        The resolved type with Parameter if found.
    """
    args = _get_subscript_args(node)
    if not args:
        raise UnresolvableTypeAliasError("Empty Annotated[]")

    # First arg is the actual type
    base_type_node = args[0]

    # Recursively resolve the base type (in case it's also an alias)
    try:
        base_resolved = _extract_from_annotation_node(base_type_node, module_ast, module_path, depth + 1)
        base_type_str = base_resolved.base_type_str
        # If the base type had a Parameter, we'll override it with any Parameter in this Annotated
        inherited_param = base_resolved.parameter
    except UnresolvableTypeAliasError:
        base_type_str = _ast_node_to_string(base_type_node)
        inherited_param = None

    # Look for Parameter in the metadata args
    parameter = inherited_param
    for arg in args[1:]:
        if isinstance(arg, ast.Call):
            func_name = None
            if isinstance(arg.func, ast.Name):
                func_name = arg.func.id
            elif isinstance(arg.func, ast.Attribute):
                func_name = arg.func.attr

            if func_name == "Parameter":
                try:
                    parameter = _extract_parameter_from_call(arg)
                except UnresolvableTypeAliasError:
                    # If we can't extract this Parameter, keep any inherited one
                    pass

    return ResolvedAlias(base_type_str=base_type_str, parameter=parameter)


def _resolve_type_alias(
    name: str,
    module_ast: ast.Module,
    module_path: str,
    depth: int = 0,
) -> ResolvedAlias:
    """Resolve a type alias to its base type and Parameter.

    This function handles the common patterns for type alias usage:

    1. **Same-file definition**: ``NoNegBool = Annotated[bool, ...]`` in the same file
    2. **Direct import**: ``from myapp.types import NoNegBool``
    3. **Re-export via __init__.py**::

           # myapp/types/base.py
           NoNegBool = Annotated[bool, ...]

           # myapp/types/__init__.py
           from .base import NoNegBool  # re-export

           # myapp/commands.py
           from myapp.types import NoNegBool  # uses re-export

    Parameters
    ----------
    name
        The alias name to resolve (e.g., "NoNegBool").
    module_ast
        AST of the module where the alias is used.
    module_path
        Dotted module path for resolving relative imports.
    depth
        Current recursion depth (limited by MAX_ALIAS_RESOLUTION_DEPTH).

    Returns
    -------
    ResolvedAlias
        The resolved type information.

    Raises
    ------
    UnresolvableTypeAliasError
        If the alias cannot be resolved within the depth limit.
    """
    if depth > MAX_ALIAS_RESOLUTION_DEPTH:
        raise UnresolvableTypeAliasError(f"Type alias chain too deep (>{MAX_ALIAS_RESOLUTION_DEPTH}): {name}")

    cache_key = (module_path, name)
    if cache_key in _alias_cache:
        return _alias_cache[cache_key]

    # Step 1: Check if defined in this module (e.g., NoNegBool = Annotated[bool, ...])
    assignment = _find_assignment_in_module(name, module_ast)
    if assignment is not None:
        try:
            result = _extract_from_annotation_node(assignment, module_ast, module_path, depth + 1)
            _alias_cache[cache_key] = result
            return result
        except UnresolvableTypeAliasError:
            pass  # Fall through to try import resolution

    # Step 2: Find where it's imported from (e.g., from myapp.types import NoNegBool)
    import_source = _find_import_source(name, module_ast, module_path)
    if import_source is None:
        raise UnresolvableTypeAliasError(f"Cannot find definition or import for: {name}")

    source_module, original_name = import_source

    try:
        source_ast = _get_cached_module_ast(source_module)
    except UnresolvableTypeAliasError as e:
        raise UnresolvableTypeAliasError(f"Cannot resolve import source for {name}: {source_module}") from e

    # Step 3: Look for assignment in the source module
    assignment = _find_assignment_in_module(original_name, source_ast)
    if assignment is not None:
        result = _extract_from_annotation_node(assignment, source_ast, source_module, depth + 1)
        _alias_cache[cache_key] = result
        return result

    # Step 4: Handle re-exports (e.g., __init__.py that imports from a submodule)
    # The name is imported but not assigned, so follow the import chain
    try:
        result = _resolve_type_alias(original_name, source_ast, source_module, depth + 1)
        _alias_cache[cache_key] = result
        return result
    except UnresolvableTypeAliasError:
        pass

    raise UnresolvableTypeAliasError(f"Cannot resolve type alias: {name}")


def _extract_function_signature(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    module_ast: ast.Module,
    module_path: str,
) -> dict[str, FieldInfo]:
    """Extract parameter info from a function AST node.

    Parameters
    ----------
    func_node
        AST node for the function.
    module_ast
        AST of the containing module.
    module_path
        Module path for import resolution.

    Returns
    -------
    dict[str, FieldInfo]
        Field info for each parameter, keyed by name.
    """
    args = func_node.args
    fields: dict[str, FieldInfo] = {}

    # Calculate default value offsets
    # For regular args, defaults are right-aligned
    num_regular_args = len(args.posonlyargs) + len(args.args)
    num_defaults = len(args.defaults)
    default_offset = num_regular_args - num_defaults

    # Process positional-only args
    for i, arg in enumerate(args.posonlyargs):
        default_idx = i - default_offset
        default_node = args.defaults[default_idx] if default_idx >= 0 and default_idx < len(args.defaults) else None
        default = _safe_eval_default(default_node)
        fields[arg.arg] = FieldInfo(
            names=(arg.arg,),
            kind=inspect.Parameter.POSITIONAL_ONLY,
            required=default is inspect.Parameter.empty,
            default=default,
            annotation=_ast_node_to_string(arg.annotation) if arg.annotation else inspect.Parameter.empty,
        )

    # Process regular positional-or-keyword args
    posonly_count = len(args.posonlyargs)
    for i, arg in enumerate(args.args):
        default_idx = posonly_count + i - default_offset
        default_node = args.defaults[default_idx] if default_idx >= 0 and default_idx < len(args.defaults) else None
        default = _safe_eval_default(default_node)
        fields[arg.arg] = FieldInfo(
            names=(arg.arg,),
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            required=default is inspect.Parameter.empty,
            default=default,
            annotation=_ast_node_to_string(arg.annotation) if arg.annotation else inspect.Parameter.empty,
        )

    # Process *args
    if args.vararg:
        fields[args.vararg.arg] = FieldInfo(
            names=(args.vararg.arg,),
            kind=inspect.Parameter.VAR_POSITIONAL,
            required=False,
            annotation=_ast_node_to_string(args.vararg.annotation)
            if args.vararg.annotation
            else inspect.Parameter.empty,
        )

    # Process keyword-only args
    for i, arg in enumerate(args.kwonlyargs):
        default_node = args.kw_defaults[i] if i < len(args.kw_defaults) and args.kw_defaults[i] is not None else None
        default = _safe_eval_default(default_node)
        fields[arg.arg] = FieldInfo(
            names=(arg.arg,),
            kind=inspect.Parameter.KEYWORD_ONLY,
            required=default is inspect.Parameter.empty,
            default=default,
            annotation=_ast_node_to_string(arg.annotation) if arg.annotation else inspect.Parameter.empty,
        )

    # Process **kwargs
    if args.kwarg:
        fields[args.kwarg.arg] = FieldInfo(
            names=(args.kwarg.arg,),
            kind=inspect.Parameter.VAR_KEYWORD,
            required=False,
            annotation=_ast_node_to_string(args.kwarg.annotation) if args.kwarg.annotation else inspect.Parameter.empty,
        )

    return fields


def _safe_eval_default(node: ast.expr | None) -> Any:
    """Safely evaluate a default value AST node.

    Returns
    -------
    Any
        The evaluated default value, ``inspect.Parameter.empty`` if no default,
        or an :class:`UnevaluableDefault` if the default cannot be statically evaluated.
    """
    if node is None:
        return inspect.Parameter.empty
    try:
        return _safe_eval_ast_node(node)
    except UnresolvableTypeAliasError:
        # For complex defaults (e.g., function calls), wrap in UnevaluableDefault
        # so it can be distinguished from actual string defaults while still
        # showing something meaningful in help text via str()
        return UnevaluableDefault(_ast_node_to_string(node))


def extract_signature_from_import_path(import_path: str) -> ASTSignature:
    """Extract complete signature info from an import path without importing.

    Parameters
    ----------
    import_path
        Import path in format "module.path:function_name".

    Returns
    -------
    ASTSignature
        Complete signature information including docstring, fields, and Parameters.

    Raises
    ------
    ValueError
        If the import path is invalid or the target cannot be found.
    TypeError
        If the target is not a function.
    UnresolvableTypeAliasError
        If type aliases cannot be resolved (caller should handle fallback).
    """
    tree, node, module_path = _parse_and_find_node(import_path)

    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise TypeError(f"Expected function, got {type(node).__name__}")

    # Extract docstring
    docstring = ast.get_docstring(node) or ""

    # Extract function signature
    fields = _extract_function_signature(node, tree, module_path)

    # Extract Parameters from annotations and resolve type aliases
    parameters: dict[str, Parameter] = {}
    resolved_aliases: dict[str, ResolvedAlias] = {}

    for name, field_info in fields.items():
        if field_info.annotation is inspect.Parameter.empty:
            continue

        # Find the annotation node for this parameter
        annotation_node = _find_param_annotation_node(node, name)
        if annotation_node is None:
            continue

        try:
            resolved = _extract_from_annotation_node(annotation_node, tree, module_path)
            resolved_aliases[name] = resolved
            if resolved.parameter is not None:
                parameters[name] = resolved.parameter
        except UnresolvableTypeAliasError:
            # If we can't resolve, just skip - help will use defaults
            pass

    # Parse docstring for parameter help text
    _populate_help_from_docstring(docstring, fields)

    return ASTSignature(
        docstring=docstring,
        fields=fields,
        parameters=parameters,
        resolved_aliases=resolved_aliases,
    )


def _find_param_annotation_node(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    param_name: str,
) -> ast.expr | None:
    """Find the annotation AST node for a parameter."""
    args = func_node.args

    # Check all parameter lists
    for arg in args.posonlyargs + args.args + args.kwonlyargs:
        if arg.arg == param_name:
            return arg.annotation

    if args.vararg and args.vararg.arg == param_name:
        return args.vararg.annotation

    if args.kwarg and args.kwarg.arg == param_name:
        return args.kwarg.annotation

    return None


def _populate_help_from_docstring(docstring: str, fields: dict[str, FieldInfo]) -> None:
    """Populate field help text from parsed docstring.

    Modifies fields in-place.
    """
    if not docstring:
        return

    try:
        import docstring_parser

        parsed = docstring_parser.parse(docstring)
        for param in parsed.params:
            if param.arg_name in fields:
                fields[param.arg_name].help = param.description
    except ImportError:
        # docstring_parser not available - skip
        pass
    except Exception:
        # Parsing failed - skip
        pass


@lru_cache(maxsize=256)
def classify_type_for_negatives(type_str: str) -> str:
    """Classify a type string for determining negative flag behavior.

    Uses AST parsing for robust structural analysis of type annotations.
    Handles complex cases like nested generics, Optional, Union, Annotated,
    and forward references.

    Parameters
    ----------
    type_str
        The type annotation as a string (e.g., "bool", "list[str]").

    Returns
    -------
    str
        One of:
        - "bool": Use negative_bool prefix (e.g., "no-")
        - "iterable": Use negative_iterable prefix (e.g., "empty-")
        - "other": No negatives (handled at runtime if needed)
    """
    if not type_str:
        return "other"

    try:
        tree = ast.parse(type_str, mode="eval")
        return _classify_type_node(tree.body)
    except SyntaxError:
        return "other"


def _classify_type_node(node: ast.expr) -> str:
    """Recursively classify an AST node for negative flag behavior.

    Uses case-sensitive matching to correctly distinguish user-defined types
    (e.g., ``Bool``) from Python builtins (e.g., ``bool``).
    """
    # Case 1: Simple name - bool, list, MyType, etc.
    if isinstance(node, ast.Name):
        name = node.id
        if name in _BOOL_TYPE_NAMES:
            return "bool"
        if name in _ITERABLE_TYPE_NAMES:
            return "iterable"
        return "other"

    # Case 2: Attribute access - typing.List, collections.abc.Sequence
    if isinstance(node, ast.Attribute):
        name = node.attr
        if name in _BOOL_TYPE_NAMES:
            return "bool"
        if name in _ITERABLE_TYPE_NAMES:
            return "iterable"
        return "other"

    # Case 3: Subscript - list[bool], Optional[int], Annotated[T, ...]
    if isinstance(node, ast.Subscript):
        base_name = _get_type_base_name(node.value)
        if base_name is None:
            return "other"

        args = _get_subscript_args(node)

        # Annotated[T, ...] - classify the first arg (the actual type)
        if base_name == "Annotated" and args:
            return _classify_type_node(args[0])

        # Optional[T] - classify the inner type
        if base_name == "Optional" and args:
            return _classify_type_node(args[0])

        # Union[T1, T2, ...] - if only one non-None type, classify it
        if base_name == "Union" and args:
            non_none = [a for a in args if not _is_none_type_node(a)]
            if len(non_none) == 1:
                return _classify_type_node(non_none[0])
            return "other"

        # Iterable types: list[X], set[X], tuple[X, ...], etc.
        if base_name in _ITERABLE_TYPE_NAMES:
            if args:
                # list[bool], set[bool] → use bool negatives
                inner_class = _classify_type_node(args[0])
                if inner_class == "bool":
                    return "bool"
            return "iterable"

        return "other"

    # Case 4: Union syntax - X | Y | Z
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        parts = _collect_union_parts(node)
        non_none = [p for p in parts if not _is_none_type_node(p)]
        if len(non_none) == 1:
            return _classify_type_node(non_none[0])
        return "other"

    # Case 5: String literal (forward reference) - "bool", "list[int]"
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return classify_type_for_negatives(node.value)

    return "other"


def _get_type_base_name(node: ast.expr) -> str | None:
    """Extract the base name from a type expression (e.g., 'List' from typing.List)."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_none_type_node(node: ast.expr) -> bool:
    """Check if a node represents None/NoneType."""
    if isinstance(node, ast.Constant) and node.value is None:
        return True
    if isinstance(node, ast.Name) and node.id in ("None", "NoneType"):
        return True
    return False


def _collect_union_parts(node: ast.BinOp) -> list[ast.expr]:
    """Collect all parts of a chained X | Y | Z union expression."""
    parts: list[ast.expr] = []
    if isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.BitOr):
        parts.extend(_collect_union_parts(node.left))
    else:
        parts.append(node.left)
    parts.append(node.right)
    return parts
