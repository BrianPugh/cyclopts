# Contributing to Cyclopts

Thank you for your interest in contributing to Cyclopts! This guide will help you get started.

## Code of Conduct

Please be respectful and constructive in all interactions. We are committed to providing a welcoming and inclusive experience for everyone.

## Where to Start

Looking for something to work on? Check out issues labeled [`good first issue`](https://github.com/BrianPugh/cyclopts/labels/good%20first%20issue) on GitHub. These are curated to be approachable for new contributors.

If you're exploring the codebase, these are good entry points:

- `cyclopts/core.py` — the main `App` class and CLI lifecycle
- `cyclopts/bind.py` — token-to-parameter binding
- `cyclopts/_convert.py` — type conversion logic
- `cyclopts/parameter.py` — parameter configuration API

## Getting Started

### Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) (recommended package manager)

### Setting Up Your Development Environment

1. Fork and clone the repository:

   ```bash
   # Replace with your fork URL, if appropriate
   git clone https://github.com/BrianPugh/cyclopts.git
   cd cyclopts
   ```

2. Install dependencies (including dev extras):

   ```bash
   uv sync --all-extras
   ```

3. Install pre-commit hooks:

   ```bash
   uv run pre-commit install
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run all tests with coverage
uv run pytest --cov=cyclopts --cov-config=pyproject.toml --cov-report term

# Run a specific test file
uv run pytest tests/test_core.py

# Run a specific test function
uv run pytest tests/test_core.py::test_function_name
```

Tests automatically run in isolated temporary directories. Python 3.12+ specific tests live in `tests/py312/` and are skipped on older versions.

### Linting and Formatting

Pre-commit hooks run automatically on `git commit`. You can also run them manually:

```bash
# Run all checks
uv run pre-commit run --all-files

# Run individual tools
uv run ruff check --fix   # Linting
uv run ruff format         # Formatting
uv run pyright             # Type checking
```

### Code Style

- **Line length:** 120 characters
- **Docstrings:** NumPy-style convention
- **Type hints:** Pyright strict mode
- **Target Python:** 3.10+ (do not use syntax or features exclusive to newer versions without version guards)

### Building Documentation

```bash
cd docs
make html
```

## Submitting Changes

### Pull Requests

1. Create a feature branch from `main`.
2. Make your changes, adding tests for new functionality.
3. Ensure all checks pass:
   ```bash
   uv run pre-commit run --all-files
   uv run pytest
   ```
4. Push your branch and open a pull request against `main`.

### Commit Messages and PR Descriptions

- Write clear, concise commit messages describing *what* changed and *why*.
- Reference related issues in your PR description (e.g., `Fixes #123`).
- There is no changelog to update — that is handled by the maintainers.

## Testing a Pull Request

If a PR has been opened to fix an issue you reported, you can test it by installing Cyclopts directly from the PR branch:

```bash
pip install git+https://github.com/BrianPugh/cyclopts.git@branch-name
```

Or with uv:

```bash
uv pip install git+https://github.com/BrianPugh/cyclopts.git@branch-name
```

Replace `branch-name` with the branch listed on the PR.

Alternatively, you can clone the repo and install in editable mode into your project's virtual environment:

```bash
git clone https://github.com/BrianPugh/cyclopts.git
cd cyclopts
git checkout branch-name

# Activate your project's virtual environment, then:
pip install -e .
```

Verify the fix against your original reproducer and report back on the PR.

## Reporting Issues

Open an issue on [GitHub](https://github.com/BrianPugh/cyclopts/issues) with:

- A minimal reproducible example.
- Your Python version and Cyclopts version (`python -c "import cyclopts; print(cyclopts.__version__)"`).
- The expected vs. actual behavior.

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
