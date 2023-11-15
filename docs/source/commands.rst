========
Commands
========

For a given cyclopts application, there are 2 primary registering actions:
1. ``@app.register`` registers
2. ``@app.default``


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

.. code-block:: console

   $ python scratch2.py foo bar 5
   BAR: 5
   $ python scratch2.py foo baz 5
   BAZ: 5


----------------
Register Default
----------------
You **cannot** register a subapp via ``default``.
The default ``default`` handler runs ``app.display_help()``.

--------------------------
Decorated Function Details
--------------------------
Cyclopts **does not modify the decorated function in any way**.
When decorated with ``@app.default`` or ``app.command``, the function is registered
to an internal dictionary, and **that is it**.
There is minimal overhead, and the function can be used exactly as if it were not decorated by Cyclopts.
