==========
Validation
==========
Typer has builtin argument validation for certain type annotations.


.. code-block:: python

   typer_app = typer.Typer()


   @typer_app.command()
   def foo(age: Annotated[int, typer.Argument(min=0)]):
       pass

This works for a select few builtins, but the Typer solution doesn't abstract out validation properly.
Why does the generic ``typer.Argument`` have fields that only have meaning if the annotated type is a number?
The ``typer.Argument`` signature has a ridiculous number of fields that only apply for certain types.

.. code-block:: python

   def Argument(
       # Parameter
       default: Optional[Any] = ...,
       *,
       callback: Optional[Callable[..., Any]] = None,
       metavar: Optional[str] = None,
       expose_value: bool = True,
       is_eager: bool = False,
       envvar: Optional[Union[str, List[str]]] = None,
       shell_complete: Optional[
           Callable[
               [click.Context, click.Parameter, str],
               Union[List["click.shell_completion.CompletionItem"], List[str]],
           ]
       ] = None,
       autocompletion: Optional[Callable[..., Any]] = None,
       # Custom type
       parser: Optional[Callable[[str], Any]] = None,
       # TyperArgument
       show_default: Union[bool, str] = True,
       show_choices: bool = True,
       show_envvar: bool = True,
       help: Optional[str] = None,
       hidden: bool = False,
       # Choice
       case_sensitive: bool = True,
       # Numbers
       min: Optional[Union[int, float]] = None,
       max: Optional[Union[int, float]] = None,
       clamp: bool = False,
       # DateTime
       formats: Optional[List[str]] = None,
       # File
       mode: Optional[str] = None,
       encoding: Optional[str] = None,
       errors: Optional[str] = "strict",
       lazy: Optional[bool] = None,
       atomic: bool = False,
       # Path
       exists: bool = False,
       file_okay: bool = True,
       dir_okay: bool = True,
       writable: bool = False,
       readable: bool = True,
       resolve_path: bool = False,
       allow_dash: bool = False,
       path_type: Union[None, Type[str], Type[bytes]] = None,
       # Rich settings
       rich_help_panel: Union[str, None] = None,
   ) -> Any:
       ...

Cyclopts has an explicit :attr:`~.Parameter.validator` field that accepts a function:

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
