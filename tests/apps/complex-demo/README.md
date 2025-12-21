# Complex Demo Application

A comprehensive test application for cyclopts documentation plugins. This application
covers all known edge cases for documentation generation with both MkDocs and Sphinx.

## Features Tested

### Type System
- **Dataclass parameter flattening** - `@Parameter(name="*")` with frozen and mutable dataclasses
- **Nested dataclasses** - Dataclass containing other dataclasses
- **Pydantic models** - BaseModel subclasses (if pydantic installed)
- **attrs classes** - @attrs.define classes (if attrs installed)
- **Complex union types** - `int | Literal["auto"]`, `int | Literal["high", "medium", "low"]`
- **Enums and Flags** - Standard enum.Enum and enum.Flag types
- **Optional types** - `Path | None = None`
- **List types** - `list[str]`, `list[Path]`, `list[OutputFormat]`

### Command Structure
- **4-level nested apps** - `admin → users → permissions → roles`
- **Custom groups** - `Group.create_ordered()` for organized help
- **Hidden commands** - Commands with `show=False`
- **Hidden parameters** - Parameters with `show=False`
- **meta.default pattern** - Global option interceptor

### Parameter Features
- **Count parameters** - `-v`, `-vv`, `-vvv`
- **parse=False parameters** - Config file paths not parsed from CLI
- **allow_leading_hyphen** - Token forwarding
- **Validators** - `validators.Number()`, `validators.Path()`
- **Positional-only** - `/,` separator
- **Keyword-only** - `*,` separator
- **Aliases** - `-f`/`--force` style aliases

### Docstring Formats
- NumPy style (default)
- Google style
- Sphinx/reST style

## Directory Structure

```
complex-demo/
├── complex_app.py          # Main application with all edge cases
├── mkdocs.yml              # MkDocs configuration
├── mkdocs_docs/            # MkDocs documentation source
│   ├── index.md
│   └── cli/
│       ├── index.md        # Full reference with TOC
│       ├── admin.md        # Nested commands, filtering
│       ├── data.md         # Dataclass flattening
│       ├── server.md       # Pydantic models
│       ├── utilities.md    # Various features
│       └── full.md         # Flattened + hidden commands
├── docs/source/            # Sphinx documentation source
│   ├── conf.py
│   ├── index.rst
│   └── cli/
│       ├── index.rst
│       ├── admin.rst
│       ├── data.rst
│       ├── server.rst
│       ├── utilities.rst
│       └── full.rst
└── pyproject.toml
```

## Building Documentation

### MkDocs

```bash
cd tests/apps/complex-demo
mkdocs build
mkdocs serve  # For development
```

### Sphinx

```bash
cd tests/apps/complex-demo
sphinx-build -b html docs/source docs/build/html
```

## Running Tests

The e2e tests in `tests/test_docs_e2e.py` exercise this demo application:

```bash
# Run all e2e documentation tests
uv run pytest tests/test_docs_e2e.py -v

# Run just MkDocs tests
uv run pytest tests/test_docs_e2e.py::TestMkDocsBuild -v

# Run just Sphinx tests
uv run pytest tests/test_docs_e2e.py::TestSphinxBuild -v
```

## Comparison with darts-nextgen

This demo replicates patterns found in darts-nextgen:

| Pattern | darts-nextgen | complex-demo |
|---------|---------------|--------------|
| `@Parameter(name="*")` on dataclass | ✅ | ✅ |
| Frozen dataclasses | ✅ | ✅ |
| Nested dataclasses | ✅ | ✅ |
| `Group.create_ordered()` | ✅ | ✅ |
| `meta.default` interceptor | ✅ | ✅ |
| Count parameters (`-v`, `-vv`) | ✅ | ✅ |
| `parse=False` parameters | ✅ | ✅ |
| 3+ level nesting | ✅ | ✅ (4 levels) |
| Complex Literal unions | ✅ | ✅ |
| Multiple doc sections with filters | ✅ | ✅ |

Additional patterns in complex-demo:
- Pydantic model support
- attrs class support
- enum.Flag types
- Multiple docstring format examples
- Hidden command/parameter testing
