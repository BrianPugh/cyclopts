"""AST utilities for extracting docstrings without importing modules.

This module provides functions to extract docstrings from Python source files
using the ast module, avoiding the need to import potentially heavy dependencies.
This is used for lazy-loaded commands to generate help text without triggering imports.
"""

import ast
import importlib.util
from pathlib import Path


def _get_module_source_path(module_path: str) -> Path | None:
    """Get the source file path for a module without importing it.

    Uses importlib.util.find_spec() which locates modules without executing them.
    """
    try:
        spec = importlib.util.find_spec(module_path)
        if spec is None or spec.origin is None:
            return None

        origin = Path(spec.origin)
        if origin.suffix != ".py":
            return None

        return origin
    except (ImportError, ModuleNotFoundError, ValueError):
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
    # Parse import path
    module_path, _, attr_path = import_path.rpartition(":")
    if not module_path or not attr_path:
        raise ValueError(f"Invalid import path format: {import_path!r}")

    # Find source file
    source_path = _get_module_source_path(module_path)
    if source_path is None:
        raise ValueError(f"Cannot find source for module: {module_path!r}")

    # Parse AST
    tree = _parse_module_ast(source_path)
    if tree is None:
        raise ValueError(f"Cannot parse source file: {source_path}")

    # Find the target node
    node = _resolve_attribute_path(tree, attr_path)
    if node is None:
        raise ValueError(f"Cannot find {attr_path!r} in AST")

    return ast.get_docstring(node) or ""
