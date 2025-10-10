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
If not specified, Cyclopts defaults to :data:`sys.argv[1:] <sys.argv>`, i.e. the list of command line arguments.
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
The ``app`` invocation processes the command's return value based on :attr:`.App.result_action`. By default, Cyclopts calls :func:`sys.exit` with an appropriate exit code:

.. code-block:: python

   from cyclopts import App

   app = App()  # Default result_action="print_non_int_sys_exit"

   @app.command
   def success():
       return 0  # Exit code for success

   @app.command
   def greet(name: str) -> str:
       return f"Hello {name}!"  # Prints and exits with 0

   if __name__ == "__main__":
       app()  # Will call sys.exit with the returned 0 error code (success).

`Installed scripts  <https://packaging.python.org/en/latest/specifications/entry-points/#use-for-scripts>`_ call :func:`sys.exit` with the returned value of the entry point. So the default Cyclopts :attr:`.App.result_action` will have consistent behavior for standalone scripts and installed apps.

For embedding Cyclopts in other Python code or testing, use ``result_action="return_value"`` to get the raw command return value without calling :func:`sys.exit`:

.. code-block:: python

   from cyclopts import App

   app = App(result_action="return_value")

   @app.command
   def foo(a: int, b: int, c: int):
       return a + b + c

   return_value = app("foo 1 2 3")  # no longer exits!
   print(f"The return value was: {return_value}.")
   # The return value was: 6.

See :ref:`Result Action` for all available modes and detailed behavior.


------------------------------
Exception Handling and Exiting
------------------------------
For the most part, Cyclopts is **hands-off** when it comes to handling exceptions and exiting the application.
However, by default, if there is a **Cyclopts runtime error**, like :exc:`.CoercionError` or a :exc:`.ValidationError`, then Cyclopts will perform a :func:`sys.exit(1) <sys.exit>`.
This is to avoid displaying the unformatted, uncaught exception to the CLI user.

These behaviors can be controlled via :class:`.App` attributes or method parameters:

- :attr:`.App.exit_on_error` - Calls :func:`sys.exit(1) <sys.exit>` on errors (defaults to :obj:`True`)
- :attr:`.App.print_error` - Formatted errors are printed (defaults to :obj:`True`)
- :attr:`.App.help_on_error` - The help-page is printed before errors (defaults to :obj:`False`)
- :attr:`.App.verbose` - Include verbose error information that might be useful for **developers** using Cyclopts (defaults to :obj:`False`)

These attributes are inherited by child apps and can be overridden by providing parameters to method calls.

.. note::
   Cyclopts separates normal output from error messages using two different consoles:

   - :attr:`App.console` - Used for normal output like help messages and version information (defaults to stdout)
   - :attr:`App.error_console` - Used for error messages like parsing errors and exceptions (defaults to stderr)


**Setting at App Level:**

.. code-block:: python

   # Configure error handling at the app level
   app = App(
       exit_on_error=False,  # Don't exit on errors
       print_error=False,    # Don't print formatted errors
   )

   # Child apps inherit these settings
   child_app = App(name="child")
   app.command(child_app)

**Method-Level Override:**

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
   #     raise UnknownCommandError(unused_tokens=unused_tokens)
   # cyclopts.exceptions.UnknownCommandError: Unknown command "this-is-not-a-registered-command".

   try:
       app("this-is-not-a-registered-command", exit_on_error=False, print_error=False)
   except CycloptsError:
       pass
   print("Execution continues since we caught the exception.")

With ``exit_on_error=False``, the ``UnknownCommandError`` is raised the same as a normal python exception.
