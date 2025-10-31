.. _Dataclass Commands:

==================
Dataclass Commands
==================

An alternative command syntax is to use dataclasses with a ``__call__`` method.
To support this pattern, Cyclopts provides the ``"call_if_callable"`` result action,
which can be composed with other result actions.

Basic Example
=============

Here's a simple example using the dataclass command pattern:

.. code-block:: python

   # greeter.py
   from dataclasses import dataclass, KW_ONLY
   from cyclopts import App

   app = App(result_action=["call_if_callable", "print_non_int_sys_exit"])

   @app.command
   @dataclass
   class Greet:
       """Greet someone with a message."""

       name: str = "World"
       _: KW_ONLY
       formal: bool = False

       def __call__(self):
           greeting = "Hello" if self.formal else "Hey"
           return f"{greeting} {self.name}."

   if __name__ == "__main__":
       app()

Running this application:

.. code-block:: console

   $ python greeter.py greet
   Hey World.

   $ python greeter.py greet Alice
   Hey Alice.

   $ python greeter.py greet Bob --formal
   Hello Bob.

How It Works
============

The ``result_action=["call_if_callable", "print_non_int_sys_exit"]`` creates a pipeline:

1. **call_if_callable**: After parsing, Cyclopts creates an instance of the ``Greet`` dataclass.
   This action checks if the result is callable (it is, because of ``__call__``), and calls it with no arguments.

2. **print_non_int_sys_exit**: Takes the string returned by ``__call__`` and prints it, then exits.

Without ``"call_if_callable"``, the app would try to print the dataclass instance itself
instead of calling it and printing the result.
