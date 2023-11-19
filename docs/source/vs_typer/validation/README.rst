==========
Validation
==========
Typer has builtin validation for certain types.


.. code-block:: python

   typer_app = typer.Typer()


   @typer_app.command()
   def foo(age: Annotated[int, typer.Argument(min=0)]):
       pass

This works for a select few builtins, but the Typer solution doesn't abstract out validation properly.
Why does the generic ``typer.Argument`` have fields that only have meaning if the annotated type is a number?
The ``typer.Argument`` class also has a bunch of fields that only apply for the ``pathlib.Path`` class, such as ``file_okay=True``.

Cyclopts has an explicit ``validator`` field that accepts a function:

.. code-block:: python

   cyclopts_app = cyclopts.App()


   def age_validator(type_, value: int):
       if value < 0:
           raise ValueError


   @cyclopts_app.command()
   def foo(age: Annotated[int, Parameter(validator=age_validator)]):
       pass

This solution is similar to how other libraries, like Attrs_ or Pydantic_, perform validation.

Cyclopts has builtin validators for common use-cases.

.. code-block:: python

   # Typer
   typer.Argument(file_okay=True, exists=True)

   # Cyclopts
   cyclopts.Parameter(validator=cyclopts.validators.Path(file_okay=True, exists=True))


.. _Attrs: https://www.attrs.org/en/stable/examples.html#validators
.. _Pydantic: https://docs.pydantic.dev/latest/concepts/validators/
