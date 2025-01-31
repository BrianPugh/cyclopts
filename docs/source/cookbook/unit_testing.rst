============
Unit Testing
============
It is important to have unit-tests to verify that your CLI is behaving correctly.
For unit-testing, we will be using the defacto-standard python unit-testing library, pytest_.
This section demonstrates some common scenarios you may encounter when unit-testing your CLI app.

Lets make a small application that checks PyPI_ if a library name is available:

.. code-block:: python

   # pypi_checker.py
   import sys
   import urllib.error
   import urllib.request
   import cyclopts

   def _check_pypi_name_available(name):
       try:
           urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json")
       except urllib.error.HTTPError as e:
           if e.code == 404:
               return True  # Package does not exist (name is available)
       return False  # Package exists (name is not available)

   app = cyclopts.App(
         config=[
            cyclopts.config.Env("PYPI_CHECKER_"),
            cyclopts.config.Json("config.json"),
         ],
   )

   @app.default
   def pypi_checker(name: str, *, silent: bool = False):
       """Check if a package name is available on PyPI.

       Exit code 0 on success; non-zero otherwise.

       Parameters
       ----------
       name: str
           Name of the package to check.
       silent: bool
           Do not print anything to stdout.
       """
       is_available = _check_pypi_name_available(name)
       if not silent:
           if is_available:
               print(f"{name} is available.")
           else:
               print(f"{name} is not available.")
      sys.exit(not is_available)

   if __name__ == "__main__":
       app()

Running the app from the console:

.. code-block:: console

   $ python pypi_checker.py --help
   Usage: pypi_checker COMMAND [ARGS] [OPTIONS]

   Check if a package name is available on PyPI.

   Exit code 0 on success; non-zero otherwise.

   ╭─ Commands ────────────────────────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                                     │
   │ --version  Display application version.                                       │
   ╰───────────────────────────────────────────────────────────────────────────────╯
   ╭─ Parameters ──────────────────────────────────────────────────────────────────╮
   │ *  NAME --name           Name of the package to check. [required]             │
   │    --silent --no-silent  Do not print anything to stdout. [default: False]    │
   ╰───────────────────────────────────────────────────────────────────────────────╯

   $ python pypi_checker.py cyclopts
   cyclopts is not available.

   $ python pypi_checker.py cyclopts --silent
   $ echo $?  # Check the exit code of the previous command.
   1

   $ python pypi_checker.py the-next-big-project
   the-next-big-project is available.
   $ echo $?  # Check the exit code of the previous command.
   0

We will slowly introduce unit-testing concepts and build up a fairly comprehensive set of unit-tests for this application.

-------
Mocking
-------
First off, it's good code-hygiene to separate "business logic" from "user interface."
In this example, that means putting all the actual logic of determining whether or not a package name is available into the ``_check_pypi_name_available`` function, and putting all of the CLI logic (like printing to ``stdout`` and exit-codes) in the Cyclopts-decorated function ``pypi_checker``.
This makes it easier to unit-test the app because it allows us to `mock <https://docs.python.org/3/library/unittest.mock.html>`_ out portions of our app, allowing us to isolate our CLI unit-tests to just the CLI components.

We can use `pytest-mock`_ to simplify mocking ``_check_pypi_name_available``. Let's define a `fixture`_ that declares this mock.

.. code-block:: python

   # test.py
   import pytest
   from pypi_checker import app

   @pytest.fixture
   def mock_check_pypi_name_available(mocker):
       return mocker.patch("pypi_checker._check_pypi_name_available")

Unit tests that use this fixture can define it's return value, as well as check the arguments it was called with.
This will be demonstrated in the next section.

----------
Exit Codes
----------
Our app directly calls :func:`sys.exit`.
Internal to python, this causes the :exc:`SystemExit` exception to be raised.
We can catch this with the :func:`pytest.raises` context manager, and check the resulting error-code.

.. code-block:: python

   def test_unavailable_name(mock_check_pypi_name_available):
       mock_check_pypi_name_available.return_value = False
       with pytest.raises(SystemExit) as e:
           app("foo")  # Invoke our app, passing in package-name "foo"
       mock_check_pypi_name_available.assert_called_once_with("foo")  # assert that our mock was called.
       assert e.value.code != 0  # assert the exit code is non-zero (i.e. not successful)

We can then run pytest on this file:

.. code-block:: console

   $ pytest test.py
   ============================== test session starts ==============================
   platform darwin -- Python 3.13.0, pytest-8.3.4, pluggy-1.5.0
   rootdir: /cyclopts-demo
   configfile: pyproject.toml
   plugins: cov-6.0.0, anyio-4.8.0, mock-3.14.0
   collected 1 item

   test.py .                                                                 [100%]

   =============================== 1 passed in 0.05s ===============================

.. note::
   Alternatively, we could have avoided using :func:`sys.exit` within our commands, and have our commands instead return an integer error-code.

   .. code-block:: python

      # pypi_checker.py

      @app.default
      def pypi_checker(name: str, *, silent: bool = False):
         ...
         return not is_available

      if __name__ == "__main__":
          sys.exit(app())

   With this setup, our unit-test would just have to check:

   .. code-block:: python

      # test.py
      assert app("foo") != 0


---------------
Checking stdout
---------------
We also want to make sure that our message is displayed to the user.
The built-in `capsys`_ fixture gives us access to our application's ``stdout``.
We can use this to confirm our app prints the correct statement.

.. code-block:: python

   # test.py - continued from "Mocking"
   def test_unavailable_name(capsys, mock_check_pypi_name_available):
       mock_check_pypi_name_available.return_value = False
       with pytest.raises(SystemExit) as e:
           app("foo")  # Invoke our app, passing in package-name "foo"
       mock_check_pypi_name_available.assert_called_once_with("foo")  # assert that our mock was called.
       assert e.value.code != 0  # assert the exit code is non-zero (i.e. not successful)
       assert capsys.readouterr().out == "foo is not available.\n"


---------------------
Environment Variables
---------------------
Because we configured our :class:`.App` with :class:`cyclopts.config.Env`, we can pass arguments into our application via environment variables.
The `pytest monkeypatch fixture`_ allows us to modify environment variables within the context of a unit-test.

In this test, we only want to test if our environment variable is being passed in correctly.
We will use :meth:`.App.parse_args`, which performs all the parsing, but doesn't actually invoke the command.

.. code-block:: python

   # test.py
   def test_name_env_var(monkeypatch):
       from pypi_checker import pypi_checker
       monkeypatch.setenv("PYPI_CHECKER_NAME", "foo")
       command, bound, _ = app.parse_args([])  # An empty list - no CLI arguments passed in.
       assert command == pypi_checker
       assert bound.arguments['name'] == "foo"

.. warning::

   A common mistake is accidentally calling ``app()`` or ``app.parse_args()`` with the **intent of providing no arguments**.
   Calling these methods with no arguments will read from :obj:`sys.argv`, the same as in a typical application.
   This is rarely the intention in a unit-test, and Cyclopts **will produce a warning.**
   For example, this code in a unit test:

   .. code-block:: python

      app()  # Wrong: will produce a warning

   Will generate this warning:

   .. code-block:: text

      =============================== warnings summary ================================
      test.py::test_no_args
        /my_project/test.py:64: UserWarning: Cyclopts application invoked without tokens
        under unit-test framework "pytest". Did you mean "app([])"?
          app()

   The proper way to specify no CLI arguments is to provide an empty string or list:

   .. code-block:: python

      app([])

-----------
File Config
-----------
To explicitly test that configurations from the :ref:`Cyclopts configuration system <Config Files>` are loading properly, we can create a configuration file in a temporary directory and change our current-working-directory (cwd) to that temporary directory. The pytest built-in ``tmp_path`` fixture gives us a temporary directory, and the ``monkeypatch`` fixture allows us to change the cwd. We have to change the cwd because typically configuration files are discovered relative to the directory where the CLI was invoked. If your CLI searches other locations (such as the home directory), you will need to modify this example appropriately.

.. code-block:: python

   # test.py
   import json

   @pytest.fixture(autouse=True)
   def chdir_to_tmp_path(tmp_path, monkeypatch):
       "Automatically change current directory to tmp_path"
       monkeypatch.chdir(tmp_path)

   @pytest.fixture
   def config_path(tmp_path):
       "Path to JSON configuration file in tmp_path"
       return tmp_path / "config.json"  # same name that was provided to cyclopts.config.Json

   def test_config(config_path):
       with config_path.open("w") as f:
          json.dump({"name": "bar"}, f)
       command, bound, _ = app.parse_args([])  # An empty list - no CLI arguments passed in.
       assert command == pypi_checker
       assert bound.arguments['name'] == "foo"

---------
Help Page
---------
Cyclopts uses Rich_ to pretty-print messages to the console.
Rich interprets the console environment, and can change how it displays text depending on the terminal's capabilities.
For unit testing, we will explicitly set a lot of these parameters in a pytest fixture to make it easier to compare against known good values:

.. code-block:: python

   @pytest.fixture
   def console():
       from rich.console import Console
       return Console(width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False)

Since the help-page is just printed to ``stdout``, we will be using the `capsys`_ fixture again.

.. code-block:: python

   from textwrap import dedent

   def test_help_page(capsys, console):
       app("--help", console=console)
       actual = capsys.readouterr().out
       assert actual == dedent(
           """\
           Usage: pypi-checker COMMAND [ARGS] [OPTIONS]

           Check if a package name is available on PyPI.

           Exit code 0 on success; non-zero otherwise.

           ╭─ Commands ─────────────────────────────────────────────────────────╮
           │ --help -h  Display this message and exit.                          │
           │ --version  Display application version.                            │
           ╰────────────────────────────────────────────────────────────────────╯
           ╭─ Parameters ───────────────────────────────────────────────────────╮
           │ *  NAME --name           Name of the package to check. [required]  │
           │    --silent --no-silent  Do not print anything to stdout.          │
           │                          [default: False]                          │
           ╰────────────────────────────────────────────────────────────────────╯
           """
       )

The :func:`textwrap.dedent` function allows us to have our expected-help-string nicely indented within our code.
Alternatively, we could have used the :meth:`rich.console.Console.capture` context manager to directly capture the :class:`rich.console.Console` output.

.. note::
   Unit-testing the help-page is probably overkill for most projects (and may get in the way more often than it helps!).

.. _PyPI: https://pypi.org
.. _pytest: https://docs.pytest.org/en/stable/
.. _pytest-mock: https://pytest-mock.readthedocs.io/en/latest/
.. _fixture: https://docs.pytest.org/en/stable/explanation/fixtures.html
.. _capsys: https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html#accessing-captured-output-from-a-test-function
.. _pytest monkeypatch fixture: https://docs.pytest.org/en/stable/how-to/monkeypatch.html
.. _Rich: https://rich.readthedocs.io/en/stable/
