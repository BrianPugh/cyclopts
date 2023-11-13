========
Meta App
========
Typically, a Cyclopts application is launched by calling the ``App`` object:

.. code-block:: python

   from cyclopts import App

   app = App()
   # Register some commands here (not shown)
   app()  # Run the app

However, what if you also want to control how the commands are invoked?
For that, you can use the meta-app feature of Cyclopts.

.. code-block:: python

   from cyclopts import App, UnknownTokens

   app = App()


   @app.register
   def foo(loops: int):
       for i in range(loops):
           print(f"Looping! {i}")


   @app.meta.register_default
   def my_app_launcher(tokens: UnknownTokens, *, user: str):
       print(f"Hello {user}")
       app(tokens)


   app.meta()

.. code-block:: bash

   $ python my-script.py --user=Bob foo 3
   Hello Bob
   Looping! 0
   Looping! 1
   Looping! 2

By annotating a parameter with the ``UnknownTokens`` type hint, cyclopts will pass along all unknown tokens as a list.
