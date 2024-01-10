========
Pydantic
========
Suppose you want to use pydantic to manage your validation logic instead of Cyclopts.
Pydantic offers a :func:`~pydantic.validate_call_decorator.validate_call` decorator that performs validation checks on invocation.

.. code-block:: python

   from cyclopts import App
   from pydantic import validate_call, PositiveInt

   app = App()


   @app.command
   @validate_call
   def foo(value: PositiveInt):
       print(value)


   app()

.. code-block:: console

   $ python my-script.py foo 10
   10
   $ python my-script.py foo -1
   ╭─ Error ────────────────────────────────────────────────────────────╮
   │ 1 validation error for foo                                         │
   │ 0                                                                  │
   │   Input should be greater than 0 [type=greater_than,               │
   │ input_value=-1, input_type=int]                                    │
   │     For further information visit                                  │
   │ https://errors.pydantic.dev/2.5/v/greater_than                     │
   ╰────────────────────────────────────────────────────────────────────╯

A benefit of this approach is that calling your decorated function from python code will still perform these validation checks.
`Pydantic's types`_ are aliases for ``Annotated[python_type, additional_metadata]``, so they are naturally compatible with Cyclopts.

.. _validate_call: https://docs.pydantic.dev/latest/concepts/validation_decorator/
.. _Pydantic's types: https://docs.pydantic.dev/latest/api/types/
