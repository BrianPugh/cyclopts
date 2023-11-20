========
Meta App
========
Typically, a Cyclopts application is launched by calling the :class:`App <cyclopts.App>` object:

.. code-block:: python

   from cyclopts import App

   app = App()
   # Register some commands here (not shown)
   app()  # Run the app

However, what if you also want to control how the commands are invoked?
For that, you can use the meta-app feature of Cyclopts.

.. code-block:: python

   from cyclopts import App

   app = App()


   @app.register
   def foo(loops: int):
       for i in range(loops):
           print(f"Looping! {i}")


   @app.meta.default
   def my_app_launcher(*tokens, user: str):
       print(f"Hello {user}")
       app(tokens)


   app.meta()

.. code-block:: console

   $ python my-script.py --user=Bob foo 3
   Hello Bob
   Looping! 0
   Looping! 1
   Looping! 2

The variable positional ``*tokens`` (with implicit type ``str``) will aggregate all remaining tokens.
We can then pass them along to the primary ``app``.
