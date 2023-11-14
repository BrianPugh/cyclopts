========
Commands
========

For a given cyclopts application, there are 2 primary registering actions:
1. ``@app.register`` registers
2. ``@app.register_default``


--------
Register
--------
The ``register`` method adds a command to a Cyclopts application.
The registered command can either be a function, or another Cyclopts application.


.. code-block:: python

   from cyclopts import App

   app = App()
   sub_app = App(name="foo")
   app.register(sub_app)


   @sub_app.register
   def bar(n: int):
       print(f"BAR: {n}")


   @sub_app.register
   def baz(n: int):
       print(f"BAZ: {n}")


   app()

.. code-block:: bash

   $ python scratch2.py foo bar 5
   BAR: 5
   $ python scratch2.py foo baz 5
   BAZ: 5


----------------
Register Default
----------------
You **cannot** register a subapp via ``register_default``.
The default ``register_default`` handler runs ``app.display_help()``.
