===============
Getting Started
===============

Cyclopts heavily relies on function parameter type hints.
If you are new to type hints or need a refresher, `checkout the mypy cheatsheet`_.

----------
Bare Bones
----------

The most bare-bones Cyclopts application is as follows:

.. code-block:: python

   import cyclopts

   app = cyclopts.App()


   @app.default
   def main():
       print("Hello World!")


   if __name__ == "__main__":
       app()

Save this as ``main.py`` and execute it to see:

.. code-block:: bash

   $ python main.py
   Hello World!


Let's dissect it step-by-step.

All Cyclopts applications start with the ``cyclopts.App`` object.

.. code-block:: python

   app = cyclopts.App()

While the ``App`` class offers various configuration options, we'll delve into those in the advanced guides.
The key method here is ``default``, which registers a function as the default action.
In this example, the ``main`` function is our default, and is executed when no command is provided.

------------------
Function Arguments
------------------
Let's add some arguments to make this program a little more exciting.

.. code-block:: python

   import cyclopts

   app = cyclopts.App()


   @app.default
   def main(name):
       print(f"Hello {name}!")


   if __name__ == "__main__":
       app()

Execute it with an argument:

.. code-block:: bash

   $ python main.py Alice
   Hello Alice!

Here's what's happening:

1. We created a function, ``main``, and registered it to ``app`` as the default
   function.

2. Invoking ``app()`` triggers Cyclopts to parse CLI inputs.

3. Cyclopts identifies ``"Alice"`` as a positional argument and, in the absence
   of an explicit type hint for ``name``, defaults to treating it as a string.

4. Cyclopts calls the registered default ``main("Alice")``, and the greeting is printed.


^^^^^^^^^^^^^^^^^^
Multiple Arguments
^^^^^^^^^^^^^^^^^^
Extending the example, lets add more arguments:

.. code-block:: python

   import cyclopts

   app = cyclopts.App()


   @app.default
   def main(name: str, count: int):
       for _ in range(count):
           print(f"Hello {name}!")


   if __name__ == "__main__":
       app()

Running it:

.. code-block:: bash

   $ python main.py Alice 3
   Hello Alice!
   Hello Alice!
   Hello Alice!

The command line input ``"3"`` is automatically converted to an integer.
Cyclopts adheres to Python's argument binding rules, allowing both positional and keyword arguments.
Therefore, all these commands are equivalent:

.. code-block: bash

   $ python main.py Alice 3
   $ python main.py --name Alice --count 3
   $ python main.py --name=Alice --count=3
   $ python main.py --count 3 --name=Alice
   $ python main.py Alice --count 3
   $ python main.py --count 3 Alice
   $ python main.py --name=Alice 3
   $ python main.py 3 --name=Alice

Cyclopts parses keyword arguments first, then fills in the gaps with positional arguments.

.. _checkout the mypy cheatsheet: https://mypy.readthedocs.io/en/latest/cheat_sheet_py3.html
