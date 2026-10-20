import ast
from pathlib import Path

PACKAGE = Path(__file__).parent.parent / "cyclopts"


def _public_names() -> set[str]:
    module = ast.parse((PACKAGE / "__init__.py").read_text())
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            return set(ast.literal_eval(node.value))
    raise AssertionError("cyclopts/__init__.py defines no __all__")


def _stub_names() -> set[str]:
    stub = ast.parse((PACKAGE / "__init__.pyi").read_text())
    names: set[str] = set()
    for node in stub.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.Assign):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return names


def test_stub_declares_every_public_name():
    """Type checkers read ``__init__.pyi`` instead of ``__init__.py``; a name missing there is unimportable for them."""
    assert _public_names() - _stub_names() == set()
