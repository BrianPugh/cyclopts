===========================
App Calling & Return Values
===========================
In this section, we'll take a closer look at the :meth:`.App.__call__` method.

-------------
Input Command
-------------
Typically, a Cyclopts app looks something like:

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.command
   def foo(a: int, b: int, c: int):
       print(a + b + c)

   app()

.. code-block:: console

   $ my-script 1 2 3
   6

:meth:`.App.__call__` takes in an optional input that it parses into an action.
If not specified, Cyclopts defaults to ``sys.argv[1:]``, i.e. the list of command line arguments.
An explicit string or list of strings can instead be passed in.

.. code-block:: python

   app("foo 1 2 3")
   # 6
   app(["foo", "1", "2", "3"])
   # 6

If a string is passed in, it will be internally converted into a list using `shlex.split <https://docs.python.org/3/library/shlex.html#shlex.split>`_.

------------
Return Value
------------
The ``app`` invocation returns the value of the called command.

.. code-block:: python

   from cyclopts import App

   app = App()

   @app.command
   def foo(a: int, b: int, c: int):
       return a + b + c

   return_value = app("foo 1 2 3")
   print(f"The return value was: {return_value}.")
   # The return value was: 6.

If you decide you want each command to return an exit code, you could invoke your app like:

.. code-block:: python

   if __name__ == "__main__":
       sys.exit(app())


------------------------------
Exception Handling and Exiting
------------------------------
For the most part, Cyclopts is **hands-off** when it comes to handling exceptions and exiting the application.
However, by default, if there is a **Cyclopts runtime error**, like :exc:`.CoercionError` or a :exc:`.ValidationError`, then Cyclopts will perform a ``sys.exit(1)``.
This is to avoid displaying the unformatted, uncaught exception to the CLI user.
This can be disabled by specifying ``exit_on_error=False`` when calling the app.
At the same time, you may want to set ``print_error=False`` to disable the printing
of the formatted exception.

.. code-block:: python

   app("this-is-not-a-registered-command")
   print("this will not be printed since cyclopts exited above.")
   # ╭─ Error ─────────────────────────────────────────────────────────────╮
   # │ Unknown command "this-is-not-a-registered-command".                 │
   # ╰─────────────────────────────────────────────────────────────────────╯

   app("this-is-not-a-registered-command", exit_on_error=False, print_error=False)
   # Traceback (most recent call last):
   #   File "/cyclopts/scratch.py", line 9, in <module>
   #     app("this-is-not-a-registered-command", exit_on_error=False, print_error=False)
   #   File "/cyclopts/cyclopts/core.py", line 1102, in __call__
   #     command, bound, _ = self.parse_args(
   #   File "/cyclopts/cyclopts/core.py", line 1037, in parse_args
   #     command, bound, unused_tokens, ignored, argument_collection = self._parse_known_args(
   #   File "/cyclopts/cyclopts/core.py", line 966, in _parse_known_args
   #     raise InvalidCommandError(unused_tokens=unused_tokens)
   # cyclopts.exceptions.InvalidCommandError: Unknown command "this-is-not-a-registered-command".

   try:
       app("this-is-not-a-registered-command", exit_on_error=False, print_error=False)
   except CycloptsError:
       pass
   print("Execution continues since we caught the exception.")

With ``exit_on_error=False``, the ``InvalidCommandError`` is raised the same as a normal python exception.
