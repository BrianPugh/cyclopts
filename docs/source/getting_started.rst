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


   @app.register_default
   def main():
       print("Hello World!")


   if __name__ == "__main__":
       app()

If we save this code to ``main.py`` and run it, we get the following:

.. code-block:: bash

   $ python main.py
   Hello World!


Lets look at this line-by-line.

All Cyclopts applications start with the ``cyclopts.App`` object.

.. code-block:: python

   app = cyclopts.App()

Cyclopts behavior can be configured through the ``App`` class, but that will be explored in later documentation.
The ``app`` object has a ``register_default`` method that can be used to decorate objects.
All Cyclopts applications have a single default function that gets executed when no command is specified at execution.


------------------
Function Arguments
------------------
Let's add some arguments to make this program a little more exciting.

.. code-block:: python

   import cyclopts

   app = cyclopts.App()


   @app.register_default
   def main(name):
       print(f"Hello {name}!")


   if __name__ == "__main__":
       app()

Running it:

.. code-block:: bash

   $ python main.py Alice
   Hello Alice!

Breaking down what happened here:

1. We created a function, ``main``, and registered it to ``app`` as the default function.

2. We then called ``app()``, this invokes Cyclopts to start parsing the command-line inputs.

3. Cyclopts sees that we called the script with a single positional argument with value ``"Alice"``.
   Cyclopts checks the type hint of the first positional argument in ``main``.
   Because we did not provide a type hint for the ``name`` parameter, cyclopts will default to assuming type ``str``.
   Cyclopts casts the input ``Alice`` to a string; since it's already inherently a string this doesn't really do anything.

4. After parsing the arguments, Cyclopts finally executes ``main("Alice")``.


^^^^^^^^^^^^^^^^^^
Multiple Arguments
^^^^^^^^^^^^^^^^^^
To further drive the point home, lets add more arguments:

.. code-block:: python

   import cyclopts

   app = cyclopts.App()


   @app.register_default
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

Here, the CLI provided ``"3"`` gets appropriately cast to an int and used in the ``main`` function.
Cyclopts follows all the same variable binding rules the python function would have if being called directly from python.
Specifically, we can specify arguments not just positionally, but also via keywords.
For this program, all of the following CLI invocations would execute the same thing:

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
