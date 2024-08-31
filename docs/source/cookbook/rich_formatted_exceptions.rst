=========================
Rich Formatted Exceptions
=========================
Tracebacks of uncaught exceptions provide valuable feedback for debugging. This guide demonstrates how to enhance your error messages using rich formatting.

-------------------------
Standard Python Traceback
-------------------------
Consider the following example:

.. code-block:: python

    from cyclopts import App

    app = App()


    @app.default
    def main(name: str):
        print(name + 3)


    if __name__ == "__main__":
        app()

Running this script will produce a standard Python traceback:

.. code-block:: console

   $ python my-script.py foo
   Traceback (most recent call last):
     File "/cyclopts/my-script.py", line 12, in <module>
       app()
     File "/cyclopts/cyclopts/core.py", line 903, in __call__
       return command(*bound.args, **bound.kwargs)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
     File "/cyclopts/my-script.py", line 8, in main
       print(name + 3)
             ~~~~~^~~
   TypeError: can only concatenate str (not "int") to str

------------------------
Rich Formatted Traceback
------------------------
To create a more visually appealing and informative traceback, you can use the `Rich library's traceback handler`_. Here's how to modify your script:

.. code-block:: python

    from cyclopts import App
    from rich.console import Console

    console = Console()
    app = App(console=console)  # Use same Console object for Cyclopts operations.


    @app.default
    def main(name: str):
        print(name + 3)


    if __name__ == "__main__":
        try:
            app()
        except Exception:
            console.print_exception()

Now, running the updated script will display a rich-formatted traceback:

.. code-block:: console

   $ python my-script.py foo
   ╭──────────────── Traceback (most recent call last) ─────────────────╮
   │ /cyclopts/my-script.py:16 in <module>                              │
   │                                                                    │
   │   13                                                               │
   │   14 if __name__ == "__main__":                                    │
   │   15 │   try:                                                      │
   │ ❱ 16 │   │   app()                                                 │
   │   17 │   except Exception:                                         │
   │   18 │   │   console.print_exception(width=70)                     │
   │   19                                                               │
   │                                                                    │
   │ /cyclopts/cyclopts/core.py:903 in __call__                         │
   │                                                                    │
   │    900 │   │   │   │                                               │
   │    901 │   │   │   │   return asyncio.run(command(*bound.args, **b │
   │    902 │   │   │   else:                                           │
   │ ❱  903 │   │   │   │   return command(*bound.args, **bound.kwargs) │
   │    904 │   │   except Exception as e:                              │
   │    905 │   │   │   try:                                            │
   │    906 │   │   │   │   from pydantic import ValidationError as Pyd │
   │                                                                    │
   │ /cyclopts/my-script.py:11 in main                                  │
   │                                                                    │
   │    8                                                               │
   │    9 @app.default                                                  │
   │   10 def main(name: str):                                          │
   │ ❱ 11 │   print(name + 3)                                           │
   │   12                                                               │
   │   13                                                               │
   │   14 if __name__ == "__main__":                                    │
   ╰────────────────────────────────────────────────────────────────────╯

This rich-formatted traceback provides a more readable and visually appealing representation of the error, but may make copy/pasting for sharing a bit more cumbersome.

.. _Rich library's traceback handler: https://rich.readthedocs.io/en/stable/traceback.html#printing-tracebacks
