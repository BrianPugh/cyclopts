# Cyclopts Demo

Demo CLI application for testing and demonstrating Cyclopts features.

## Purpose

This app is designed for:

- Manual testing of shell completion
- Testing edge cases that are hard to unit test
- Demonstrating Cyclopts features in documentation
- Serving as a reference implementation

## Quick Start

### Run the CLI

```bash
cd tests/apps/cyclopts-demo

# Show help
python cyclopts_demo.py --help

# Try commands
python cyclopts_demo.py files ls --help
python cyclopts_demo.py database migrate --help
```

### Build and View MkDocs Documentation

```bash
# Build the documentation
uv run mkdocs build

# Serve the documentation locally
uv run mkdocs serve
# Opens http://127.0.0.1:8000
```
