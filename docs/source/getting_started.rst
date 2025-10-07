.. _Getting Started:

===============
Getting Started
===============

Cyclopts relies heavily on function parameter type hints.
If you are new to type hints or need a refresher, `checkout the mypy cheatsheet`_.

----------------------------
A Basic Cyclopts Application
----------------------------

The most basic Cyclopts application is as follows:

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.default
   def main():
       print("Hello World!")

   if __name__ == "__main__":
       app()

Save this as ``main.py`` and execute it to see:

.. code-block:: console

   $ python main.py
   Hello World!


The :class:`.App` class offers various configuration options that we'll explore in more detail later.
The ``app`` object has a decorator method, :meth:`default <cyclopts.App.default>`, which registers a function as the **default action**.
In this example, the ``main`` function is our default action, and is executed when no CLI command is provided.

------------------
Function Arguments
------------------
Let's add some arguments to make this program a little more interesting.

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.default
   def main(name):
       print(f"Hello {name}!")

   if __name__ == "__main__":
       app()

Executing the script with the argument ``Alice`` produces the following:

.. code-block:: console

   $ python main.py Alice
   Hello Alice!

Code explanation:

1. The function ``main()`` was registered to ``app`` as the **default** action.

2. Calling ``app()`` at the bottom triggers the app to begin parsing CLI inputs.

3. Cyclopts identifies ``"Alice"`` as a positional argument and matches it to the parameter ``name``.
   In the absence of an explicit type hint, Cyclopts defaults to parsing the value as a ``str``.

   .. note::
      Without a type annotation, Cyclopts will actually first attempt to use the **type** of
      the parameter's **default value**. If the parameter doesn't have a default value, it will
      then fallback to ``str``. See :ref:`Coercion Rules`.


4. Cyclopts calls the registered **default** function ``main("Alice")``, and the greeting is printed.


------------------
Multiple Arguments
------------------
Extending the example, lets add more arguments and type hints:

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.default
   def main(name: str, count: int, formal: bool = False):
       for _ in range(count):
          if formal:
             print(f"Hello {name}!")
          else:
             print(f"Hey {name}!")

   if __name__ == "__main__":
       app()

.. code-block:: console

   $ python main.py Alice 3
   Hey Alice!
   Hey Alice!
   Hey Alice!

   $ python main.py Alice 3 --formal
   Hello Alice!
   Hello Alice!
   Hello Alice!


The command line input ``"3"`` is converted to an integer because the parameter ``count`` has the type hint :obj:`int`.
Boolean parameters (e.g., ``--formal`` in this example) are interpreted as flags.
Cyclopts natively handles all python builtin types (:ref:`and more! <Coercion Rules>`).
Cyclopts adheres to Python's argument binding rules, allowing for both positional and keyword arguments.
All of the following CLI invocations are equivalent:

.. code-block:: console

   $ python main.py Alice 3                  # Supplying arguments positionally.
   $ python main.py --name Alice --count 3   # Supplying arguments via keywords.
   $ python main.py --name=Alice --count=3   # Using = for matching keywords to values is allowed.
   $ python main.py --count 3 --name=Alice   # Keyword order does not matter.
   $ python main.py Alice --count 3          # Positional followed by keyword
   $ python main.py --count 3 Alice          # Keywords can come before positional if the keyword is later in the function signature.
   $ python main.py --count 3 -- Alice       # Using the POSIX convention to indicate the end of keywords

Like calling functions in python, positional arguments cannot be specified after a **prior** argument in the function signature was specified via keyword.
For example, you cannot supply the count value ``"3"`` positionally while the value for ``name`` is specified via keyword:

.. code-block:: console

   # The following are NOT allowed.
   $ python main.py --name=Alice 3  # invalid python: main(name="Alice", 3)
   $ python main.py 3 --name=Alice  # invalid python: main(3, name="Alice")

------------------
Adding a Help Page
------------------
All CLI apps need to have a help page explaining how to use the application.
By default, Cyclopts adds the ``--help`` (and the shortform ``-h``) commands to your CLI.
We can add application-level help documentation when creating our ``app``:

.. code-block:: python

   from cyclopts import App

   app = App(help="Help string for this demo application.")

   @app.default
   def main(name: str, count: int):
       for _ in range(count):
           print(f"Hello {name}!")

   if __name__ == "__main__":
       app()

.. code-block:: console

   $ python main.py --help
   Usage: main COMMAND [ARGS] [OPTIONS]

   Help string for this demo application.

   ╭─ Commands ──────────────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                           │
   │ --version  Display application version.                             │
   ╰─────────────────────────────────────────────────────────────────────╯
   ╭─ Parameters ────────────────────────────────────────────────────────╮
   │ *  NAME --name    [required]                                        │
   │ *  COUNT --count  [required]                                        │
   ╰─────────────────────────────────────────────────────────────────────╯

.. note::
   Help flags can be changed with :attr:`~cyclopts.App.help_flags`.

Let's add some help documentation for our parameters.
Cyclopts uses the function's docstring and can interpret ReST, Google, Numpydoc-style and Epydoc docstrings (shoutout to `docstring_parser <https://github.com/rr-/docstring_parser>`_).

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.default
   def main(name: str, count: int):
       """Help string for this demo application.

       Parameters
       ----------
       name: str
           Name of the user to be greeted.
       count: int
           Number of times to greet.
       """
       for _ in range(count):
           print(f"Hello {name}!")

   if __name__ == "__main__":
       app()

.. code-block:: console

   $ python main.py --help
   Usage: main COMMAND [ARGS] [OPTIONS]

   Help string for this demo application.

   ╭─ Commands ──────────────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                           │
   │ --version  Display application version.                             │
   ╰─────────────────────────────────────────────────────────────────────╯
   ╭─ Parameters ────────────────────────────────────────────────────────╮
   │ *  NAME --name    Name of the user to be greeted. [required]        │
   │ *  COUNT --count  Number of times to greet. [required]              │
   ╰─────────────────────────────────────────────────────────────────────╯

.. note::
   If :attr:`.App.help` is not explicitly set, Cyclopts will fallback to the first line
   (short description) of the registered ``@app.default`` function's docstring.

---
Run
---
An alternative, terser API is available for simple applications with a single command.
The :func:`.run` function takes in a single callable (usually a function) and runs it
as a Cyclopts application.

.. code-block:: python

   import cyclopts

   def main(name: str, count: int):
       for _ in range(count):
           print(f"Hello {name}!")

   if __name__ == "__main__":
       cyclopts.run(main)

The :func:`.run` function is intentionally simple. If greater control is required, then use the
conventional :class:`.App` interface.

.. _checkout the mypy cheatsheet: https://mypy.readthedocs.io/en/latest/cheat_sheet_py3.html
