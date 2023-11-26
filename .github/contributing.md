## Environment Setup

1. We use [Poetry](https://python-poetry.org/docs/#installation) for managing virtual environments and dependencies.
   Once Poetry is installed, run `poetry install` in this repo to get started.
2. For managing linters, static-analysis, and other tools, we use [pre-commit](https://pre-commit.com/#installation).
   Once Pre-commit is installed, run `pre-commit install` in this repo to install the hooks.
   Using pre-commit ensures PRs match the linting requirements of the codebase.

## Documentation
Whenever possible, please add docstrings to your code!
We use [numpy-style napoleon docstrings](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/#google-vs-numpy).
To confirm docstrings are valid, build the docs by running `poetry run make html` in the `docs/` folder.

I typically write dosctrings first, it will act as a guide to limit scope and encourage unit-testable code.
Good docstrings include information like:

1. If not immediately obvious, what is the intended use-case? When should this function be used?
2. What happens during errors/edge-cases.
3. When dealing with physical values, include units.

## Unit Tests
We use the [pytest](https://docs.pytest.org/) framework for unit testing. Ideally, all new code is partners with
new unit tests to exercise that code. If fixing a bug, consider writing the test first to confirm the existence of the
bug, and to confirm that the new code fixes it.

Unit tests should only test a single concise body of code. If this is hard to do, there are two solutions that can help:
1. Restructure the code. Keep inputs/outputs to be simple variables. Avoid complicated interactions with state.
2. Use [pytest-mock](https://pytest-mock.readthedocs.io/en/latest/) to mock out external interactions.

## Coding Style
In an attempt to keep consistency and maintainability in the code-base, here are some high-level guidelines for code that might not be enforced by linters.

* Use f-strings.
* Keep/cast path variables as `pathlib.Path` objects.
  Do not use `os.path`.
  For public-facing functions, cast path arguments immediately to `Path`.
* Use magic-methods when appropriate. It might be better to implement ``MyClass.__call__()`` instead of ``MyClass.run()``.
* Do not return sentinel values for error-states like `-1` or `None`. Instead, raise an exception.
* Avoid deeply nested code. Techniques like returning early and breaking up a complicated function into multiple functions results in easier to read and test code.
* Consider if you are double-name-spacing and how modules are meant to be imported.
  E.g. it might be better to name a function `read` instead of `image_read` in the module `my_package/image.py`.
  Consider the module name-space and whether or not it's flattened in `__init__.py`.
* Only use multiple-inheritance if using a mixin. Mixin classes should end in `"Mixin"`.
