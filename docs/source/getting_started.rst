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
The ``app`` object has a decorator method, :meth:`default <cyclopts.App.default>`, which registers a function as the default action.
In this example, the ``main`` function is our default, and is executed when no CLI command is provided.
An :class:`.App` can have only a single default action.

------------------
Function Arguments
------------------
Let's add some arguments to make this program a little more exciting.

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.default
   def main(name):
       print(f"Hello {name}!")

   if __name__ == "__main__":
       app()

Execute the script with an argument:

.. code-block:: console

   $ python main.py Alice
   Hello Alice!

Here's what's happening:

1. The function ``main`` was registered to ``app`` as the default action.

2. Calling ``app()`` triggers Cyclopts to parse CLI inputs.

3. Cyclopts identifies ``"Alice"`` as a positional argument, matching it to the parameter ``name``.
   In the absence of an explicit type hint, Cyclopts defaults to parsing the value as a ``str``.

4. Cyclopts calls the registered default ``main("Alice")``, and the greeting is printed.


------------------
Multiple Arguments
------------------
Extending the example, lets add more arguments and type hints:

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.default
   def main(name: str, count: int):
       for _ in range(count):
           print(f"Hello {name}!")

   if __name__ == "__main__":
       app()

.. code-block:: console

   $ python main.py Alice 3
   Hello Alice!
   Hello Alice!
   Hello Alice!

The command line input ``"3"`` is converted to an integer because of ``count``'s type hint ``int``.
Cyclopts natively handles all python builtin types, see :ref:`Coercion Rules` for more details.
Cyclopts adheres to Python's argument binding rules, allowing both positional and keyword arguments.
Therefore, all these commands are equivalent:

.. code-block:: console

   $ python main.py Alice 3
   $ python main.py --name Alice --count 3
   $ python main.py --name=Alice --count=3
   $ python main.py --count 3 --name=Alice
   $ python main.py Alice --count 3
   $ python main.py --count 3 Alice

Same as in python, you cannot specify positional arguments after a prior argument was specified via keyword.
For example, you cannot supply the count value ``"3"`` positionally while the value for ``name`` is specified via keyword:

.. code-block:: bash

   # The following are NOT allowed.
   $ python main.py --name=Alice 3
   $ python main.py 3 --name=Alice

Cyclopts parses keyword arguments, then positional arguments.

-----------
Adding Help
-----------
By default, Cyclopts adds the ``--help`` commands to your CLI.
We can add application-level help documentation when creating our ``app``:

.. code-block:: python

   from cyclopts import App
   app = App(help="Help string for this demo application.")

   if __name__ == "__main__":
       app()

.. code-block:: console

   $ my-script --help
   Usage: my-script COMMAND

   Help string for this demo application.

   ╭─ Commands ──────────────────────────────────────────────────────────╮
   │ --help,-h  Display this message and exit.                           │
   │ --version  Display application version.                             │
   ╰─────────────────────────────────────────────────────────────────────╯

If :attr:`.App.help` is not explicitly set, Cyclopts will fallback to the first line
(short description) of the registered ``@app.default`` function's docstring.

.. _checkout the mypy cheatsheet: https://mypy.readthedocs.io/en/latest/cheat_sheet_py3.html
