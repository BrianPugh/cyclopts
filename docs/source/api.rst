.. _API:

===
API
===

.. autoclass:: cyclopts.App
   :members: default, command, version_print, help_print, interactive_shell, parse_commands, parse_known_args, parse_args, run_async, assemble_argument_collection, update, generate_docs, generate_completion, install_completion, register_install_completion_command
   :special-members: __call__, __getitem__, __iter__

   Cyclopts Application.

   .. attribute:: name
      :type: Optional[Union[str, Iterable[str]]]
      :value: None

      Name of application, or subcommand if registering to another application. Name resolution order:

      1. User specified :attr:`~.App.name` parameter.
      2. If a :attr:`~.App.default` function has been registered, the name of that function.
      3. If the module name is ``__main__.py``, the name of the encompassing package.
      4. The value of :data:`sys.argv[0] <sys.argv>`; i.e. the name of the python script.

      Multiple names can be provided in the case of a subcommand, but this is relatively unusual.

      Special value ``"*"`` can be used when registering sub-apps with :meth:`~.App.command` to flatten all commands from the sub-app into the parent app. See :ref:`Flattening SubCommands` for details.

      Example:

      .. code-block:: python

         from cyclopts import App

         app = App()
         app.command(App(name="foo"))

         @app["foo"].command
         def bar():
             print("Running bar.")

         app()

      .. code-block:: console

         $ my-script foo bar
         Running bar.

   .. attribute:: alias
      :type: Optional[Union[str, Iterable[str]]]
      :value: None

      Extends :attr:`.name` with additional names.
      Unlike :attr:`.name`, this does not override Cyclopts-derived names.

      .. code-block:: python

         from cyclopts import App

         app = App()

         @app.command(alias="bar")
         def foo():
             print("Running foo.")

         app()

      .. code-block:: console

         $ my-script foo
         Running bar.

         $ my-script bar
         Running bar.

   .. attribute:: help
      :type: Optional[str]
      :value: None

      Text to display on help screen.
      If not supplied, fallbacks to parsing the docstring of function registered with :meth:`.App.default`.

      .. code-block:: python

         from cyclopts import App

         app = App(help="This is my help string.")
         app()

      .. code-block:: console

         $ my-script --help
         Usage: scratch.py COMMAND

         This is my help string.

         ╭─ Commands ────────────────────────────────────────────────────────────╮
         │ --help -h  Display this message and exit.                             │
         │ --version  Display application version.                               │
         ╰───────────────────────────────────────────────────────────────────────╯

   .. attribute:: help_flags
      :type: Union[str, Iterable[str]]
      :value: ("--help", "-h")

      CLI flags that trigger :meth:`help_print`.
      Set to an empty list to disable this feature.
      Defaults to ``["--help", "-h"]``.

   .. attribute:: help_format
      :type: Optional[Literal["plaintext", "markdown", "md", "restructuredtext", "rst"]]
      :value: None

      The markup language used in function docstring.
      If :obj:`None`, fallback to parenting :attr:`~.App.help_format`.
      If no :attr:`~.App.help_format` is defined, falls back to ``"markdown"``.

      .. note::
         The ``"restructuredtext"`` and ``"rst"`` formats require the optional ``rst`` extra,
         which installs rich-rst_:
         ``pip install "cyclopts[rst]"``

   .. attribute:: help_formatter
      :type: Union[None, Literal["default", "plain"], HelpFormatter]
      :value: None

      Help formatter to use for rendering help panels.

      * If :obj:`None` (default), inherits from parent :class:`.App`, eventually defaulting to :class:`~cyclopts.help.DefaultFormatter`.

      * If ``"default"``, uses :class:`~cyclopts.help.DefaultFormatter`.

      * If ``"plain"``, uses :class:`~cyclopts.help.PlainFormatter` for no-frills plain text output.

      * If a callable (see :class:`~cyclopts.help.protocols.HelpFormatter` protocol), uses the provided formatter.

      Example:

      .. code-block:: python

         from cyclopts import App
         from cyclopts.help import DefaultFormatter, PlainFormatter, PanelSpec

         # Use plain text formatter
         app = App(help_formatter="plain")

         # Use default formatter with customization
         app = App(help_formatter=DefaultFormatter(
             panel_spec=PanelSpec(border_style="blue")
         ))

      See :ref:`Help Customization` for detailed examples and advanced usage.

   .. attribute:: help_epilogue
      :type: Optional[str]
      :value: None

      Text to display at the end of the help screen, after all help panels.
      Commonly used for version information, contact details, or additional notes.
      If :obj:`None`, no epilogue is displayed.
      If not set, attempts to inherit from parenting :class:`.App`.

      The epilogue supports the same formatting as :attr:`help` based on :attr:`help_format` (markdown, plaintext, restructuredtext, or rich).
      Note that restructuredtext format requires installing ``cyclopts[rst]``, which installs rich-rst_.

      Example:

      .. code-block:: python

         from cyclopts import App

         app = App(
             name="myapp",
             help="My application help.",
             help_epilogue="Support: support@example.com"
         )
         app()

      .. code-block:: console

         $ my-script --help
         Usage: myapp COMMAND

         My application help.

         ╭─ Commands ────────────────────────────────────────────────────────────╮
         │ --help -h  Display this message and exit.                             │
         │ --version  Display application version.                               │
         ╰───────────────────────────────────────────────────────────────────────╯

         Support: support@example.com

   .. attribute:: help_on_error
      :type: Optional[bool]
      :value: None

      Prints the help-page before printing an error.
      If not set, attempts to inherit from parenting :class:`.App`, eventually defaulting to :obj:`False`.

   .. attribute:: print_error
      :type: Optional[bool]
      :value: None

      Print a rich-formatted error on error.
      If not set, attempts to inherit from parenting :class:`.App`, eventually defaulting to :obj:`True`.

   .. attribute:: exit_on_error
      :type: Optional[bool]
      :value: None

      If there is an error parsing the CLI tokens, invoke :func:`sys.exit(1) <sys.exit>`.
      Otherwise, continue to raise the exception.
      If not set, attempts to inherit from parenting :class:`.App`, eventually defaulting to :obj:`True`.

   .. attribute:: verbose
      :type: Optional[bool]
      :value: None

      Populate exception strings with more information intended for developers.
      If not set, attempts to inherit from parenting :class:`.App`, eventually defaulting to :obj:`False`.

   .. attribute:: version_format
      :type: Optional[Literal["plaintext", "markdown", "md", "restructuredtext", "rst"]]
      :value: None

      The markup language used in the version string.
      If :obj:`None`, fallback to parenting :attr:`~.App.version_format`.
      If no :attr:`~.App.version_format` is defined, falls back to resolved :attr:`~.App.help_format`.

      .. note::
         The ``"restructuredtext"`` and ``"rst"`` formats require the optional ``rst`` extra,
         which installs rich-rst_:
         ``pip install "cyclopts[rst]"``

   .. attribute:: usage
      :type: Optional[str]
      :value: None

      Text to be displayed in lieue of the default ``Usage: app COMMAND ...`` at the beginning of the help-page.
      Set to an empty-string ``""`` to disable showing the default usage.

   .. attribute:: show
      :type: bool
      :value: True

      Show this **command** on the help screen.
      Hidden commands (``show=False``) are still executable.

      .. code-block:: python

         from cyclopts import App
         app = App()

         @app.command
         def foo():
            print("Running foo.")

         @app.command(show=False)
         def bar():
            print("Running bar.")

         app()

      .. code-block:: console

         $ my-script foo
         Running foo.

         $ my-script bar
         Running bar.

         $ my-script --help
         Usage: scratch.py COMMAND

         ╭─ Commands ─────────────────────────────────────────────────╮
         │ foo                                                        │
         │ --help -h  Display this message and exit.                  │
         │ --version  Display application version.                    │
         ╰────────────────────────────────────────────────────────────╯

   .. attribute:: sort_key
      :type: Any
      :value: None

      Modifies command display order on the help-page.

      1. If :attr:`sort_key` is a generator, it will be consumed immediately with :func:`next` to get the actual value.

      2. If :attr:`sort_key`, or any of it's contents, are ``Callable``, then invoke it ``sort_key(app)`` and apply the returned value to (3) if :obj:`None`, (4) otherwise.

      3. For all commands with ``sort_key==None`` (default value), sort them alphabetically.
         These sorted commands will be displayed **after** ``sort_key != None`` list (see 4).

      4. For all commands with ``sort_key!=None``, sort them by ``(sort_key, app.name)``.
         It is the user's responsibility that ``sort_key`` s are comparable.

      Example usage:

      .. code-block:: python

         from cyclopts import App

         app = App()

         @app.command  # sort_key not specified; will be sorted AFTER bob/charlie.
         def alice():
             """Alice help description."""

         @app.command(sort_key=2)
         def bob():
             """Bob help description."""

         @app.command(sort_key=1)
         def charlie():
             """Charlie help description."""

         app()

      Resulting help-page:

      .. code-block:: text

         Usage: demo.py COMMAND

         ╭─ Commands ──────────────────────────────────────────────────╮
         │ charlie    Charlie help description.                        │
         │ bob        Bob help description.                            │
         │ alice      Alice help description.                          │
         │ --help -h  Display this message and exit.                   │
         │ --version  Display application version.                     │
         ╰─────────────────────────────────────────────────────────────╯

      Using generators (e.g., :func:`itertools.count`):

      .. code-block:: python

         import itertools
         from cyclopts import App

         app = App()
         counter = itertools.count()

         @app.command(sort_key=counter)
         def beta():
             """Beta help description."""

         @app.command(sort_key=counter)
         def alpha():
             """Alpha help description."""

         app()

      .. code-block:: text

         Usage: demo.py COMMAND

         ╭─ Commands ──────────────────────────────────────────────────╮
         │ beta       Beta help description.                           │
         │ alpha      Alpha help description.                          │
         │ --help -h  Display this message and exit.                   │
         │ --version  Display application version.                     │
         ╰─────────────────────────────────────────────────────────────╯

   .. attribute:: version
      :type: Union[None, str, Callable]
      :value: None

      Version to be displayed when a :attr:`version_flags` is parsed.
      Defaults to the version of the package instantiating :class:`.App`.
      If a :obj:`~typing.Callable`, it will be invoked with no arguments when version is queried.

   .. attribute:: version_flags
      :type: Union[str, Iterable[str]]
      :value: ("--version",)

      Token(s) that trigger :meth:`version_print`.
      Set to an empty list to disable version feature.
      Defaults to ``["--version"]``.

   .. attribute:: console
      :type: ~rich.console.Console
      :value: None

      Default :class:`~rich.console.Console` to use when displaying runtime messages.
      Cyclopts console resolution is as follows:

      #. Any explicitly passed in console to methods like :meth:`.App.__call__`, :meth:`.App.parse_args`, etc.
      #. The relevant subcommand's :attr:`.App.console` attribute, if not :obj:`None`.
      #. The parenting :attr:`.App.console` (and so on), if not :obj:`None`.
      #. If all values are :obj:`None`, then the default :class:`~rich.console.Console` is used.

   .. attribute:: error_console
      :type: ~rich.console.Console
      :value: None

      Default :class:`~rich.console.Console` to use when displaying error messages.
      Cyclopts error_console resolution is as follows:

      #. Any explicitly passed in error_console to methods like :meth:`.App.__call__`, :meth:`.App.parse_args`, etc.
      #. The relevant subcommand's :attr:`.App.error_console` attribute, if not :obj:`None`.
      #. The parenting :attr:`.App.error_console` (and so on), if not :obj:`None`.
      #. If all values are :obj:`None`, then a default :class:`~rich.console.Console` with ``stderr=True`` is used.

      This separation of error output from normal output follows Unix conventions, allowing
      users to redirect error messages independently from normal output (e.g., ``program > output.txt 2> errors.txt``).

   .. attribute:: default_parameter
      :type: Parameter
      :value: None

      Default :class:`.Parameter` configuration. Unspecified values of command-annotated :class:`.Parameter` will inherit these values.
      See :ref:`Default Parameter` for more details.

   .. attribute:: group
      :type: Union[None, str, Group, Iterable[Union[str, Group]]]
      :value: None

      The group(s) that :attr:`default_command` belongs to.

      * If :obj:`None`, defaults to the ``"Commands"`` group.

      * If :obj:`str`, use an existing :class:`.Group` (from neighboring sub-commands) with name,
        **or** create a :class:`.Group` with provided name if it does not exist.

      * If :class:`.Group`, directly use it.

   .. attribute:: group_commands
      :type: Group
      :value: Group("Commands")

      The default :class:`.Group` that sub-commands are assigned to.

   .. attribute:: group_arguments
      :type: Group
      :value: Group("Arguments")

      The default :class:`.Group` that positional-only parameters are assigned to.

   .. attribute:: group_parameters
      :type: Group
      :value: Group("Parameters")

      The default :class:`.Group` that non-positional-only parameters are assigned to.

   .. attribute:: validator
      :type: Union[None, Callable, list[Callable]]
      :value: []

      A function (or list of functions) where all the converted CLI-provided variables will be **keyword-unpacked**,
      regardless of their positional/keyword-type in the command function signature.
      The python variable names will be used, which may differ from their CLI names.

      Example usage:

      .. code-block:: python

         def validator(**kwargs):
             "Raise an exception if something is invalid."

      This validator runs **after** :class:`.Parameter` and :class:`.Group` validators.

   .. attribute:: name_transform
      :type: Optional[Callable[[str], str]]
      :value: None

      A function that converts function names to their CLI command counterparts.

      The function must have signature:

      .. code-block:: python

         def name_transform(s: str) -> str:
             ...

      The returned string should be **without** a leading ``--``.
      If :obj:`None` (default value), uses :func:`~.default_name_transform`.
      Subapps inherit from the first non-:obj:`None` parent :attr:`name_transform`.

   .. attribute:: config
      :type: Union[None, Callable, Iterable[Callable]]
      :value: None

      A function or list of functions that are consecutively executed after parsing CLI tokens and environment variables.
      These function(s) are called **before** any conversion and validation.
      Each config function must have signature:

      .. code-block:: python

         def config(app: "App", commands: Tuple[str, ...], arguments: ArgumentCollection):
             """Modifies given mapping inplace with some injected values.

             Parameters
             ----------
             app: App
                The current command app being executed.
             commands: Tuple[str, ...]
                The CLI strings that led to the current command function.
             arguments: ArgumentCollection
                Complete ArgumentCollection for the app.
                Modify this collection inplace to influence values provided to the function.
             """

      The intended use-case of this feature is to allow users to specify functions that can load defaults from some external configuration.
      See :ref:`cyclopts.config <API Config>` for useful builtins and :ref:`Config Files` for examples.

   .. attribute:: end_of_options_delimiter
      :type: Optional[str]
      :value: None

      All tokens after this delimiter will be force-interpreted as positional arguments.
      If not set, attempts to inherit from parenting :class:`.App`, eventually defaulting to POSIX-standard ``"--"``.
      Set to an empty string to disable.

   .. attribute:: suppress_keyboard_interrupt
      :type: bool
      :value: True

      If the application receives a keyboard interrupt (Ctrl-C), suppress the error message and exit gracefully.
      Set to :obj:`False` to let :class:`KeyboardInterrupt` propagate normally.

   .. attribute:: backend
      :type: Optional[Literal["asyncio", "trio"]]
      :value: None

      The async backend to use when executing async commands.
      If not set, attempts to inherit from parenting :class:`.App`, eventually defaulting to ``"asyncio"``.

      Example:

      .. code-block:: python

         from cyclopts import App

         app = App(backend="asyncio")

         @app.default
         async def main():
             await some_async_operation()

         app()

      The backend can also be overridden on a per-call basis:

      .. code-block:: python

         app(backend="trio")  # Override the app's backend for this call

   .. attribute:: result_action
      :type: Literal["return_value", "call_if_callable", "print_non_int_return_int_as_exit_code", "print_str_return_int_as_exit_code", "print_str_return_zero", "print_non_none_return_int_as_exit_code", "print_non_none_return_zero", "return_int_as_exit_code_else_zero", "print_non_int_sys_exit", "sys_exit", "return_none", "return_zero", "print_return_zero", "sys_exit_zero", "print_sys_exit_zero"] | Callable[[Any], Any] | Iterable[Literal[...] | Callable[[Any], Any]] | None
      :value: None

      Controls how :meth:`.App.__call__` and :meth:`.App.run_async` handle command return values. By default (``"print_non_int_sys_exit"``), the app will call :func:`sys.exit` with an appropriate exit code. This default was chosen for consistent functionality between standalone scripts, and console entrypoints.

      Can be a predefined literal string, a custom callable that takes the result and returns a processed value, or a **sequence of actions** to be applied left-to-right in a pipeline.

      Each predefined mode's exact behavior is shown below:

      **"print_non_int_sys_exit"** (default)

         The default CLI mode. Prints non-int values to stdout, then calls :func:`sys.exit` with the appropriate exit code.

         .. code-block:: python

            if isinstance(result, bool):
                sys.exit(0 if result else 1)  # i.e. True is success
            elif isinstance(result, int):
                sys.exit(result)
            elif result is not None:
                print(result)
                sys.exit(0)
            else:
                sys.exit(0)

      **"return_value"**

         Returns the command's value unchanged. Use for embedding Cyclopts in other Python code or testing.

         .. code-block:: python

            return result

      **"call_if_callable"**

         Calls the result if it's callable (with no arguments), otherwise returns it unchanged. Useful for the dataclass command pattern where commands return class instances with ``__call__`` methods. Intended to be used in composition with other result actions (e.g., ``["call_if_callable", "print_non_int_sys_exit"]``).

         .. code-block:: python

            return result() if callable(result) else result

         See :ref:`Dataclass Commands` for usage examples.

      **"sys_exit"**

         Never prints output. Calls :func:`sys.exit` with the appropriate exit code. Useful for CLI apps that handle their own output and just need exit code handling.

         .. code-block:: python

            if isinstance(result, bool):
                sys.exit(0 if result else 1)  # i.e. True is success
            elif isinstance(result, int):
                sys.exit(result)
            else:
                sys.exit(0)

      **"print_non_int_return_int_as_exit_code"**

         Prints non-int values, returns int/bool as exit codes. Useful for testing and embedding.

         .. code-block:: python

            if isinstance(result, bool):
                return 0 if result else 1  # i.e. True is success
            elif isinstance(result, int):
                return result
            elif result is not None:
                print(result)
                return 0
            else:
                return 0

      **"print_str_return_int_as_exit_code"**

         Only prints string return values. Returns int/bool as exit codes, silently returns 0 for other types.

         .. code-block:: python

            if isinstance(result, str):
                print(result)
                return 0
            elif isinstance(result, bool):
                return 0 if result else 1  # i.e. True is success
            elif isinstance(result, int):
                return result
            else:
                return 0

      **"print_str_return_zero"**

         Only prints string return values, always returns 0. Useful for simple output-only CLIs.

         .. code-block:: python

            if isinstance(result, str):
                print(result)
            return 0

      **"print_non_none_return_int_as_exit_code"**

         Prints all non-None values (including ints), returns int/bool as exit codes.

         .. code-block:: python

            if result is not None:
                print(result)
            if isinstance(result, bool):
                return 0 if result else 1  # i.e. True is success
            elif isinstance(result, int):
                return result
            return 0

      **"print_non_none_return_zero"**

         Prints all non-None values (including ints), always returns 0.

         .. code-block:: python

            if result is not None:
                print(result)
            return 0

      **"return_int_as_exit_code_else_zero"**

         Never prints output. Returns int/bool as exit codes, 0 for all other types. Useful for silent CLIs.

         .. code-block:: python

            if isinstance(result, bool):
                return 0 if result else 1  # i.e. True is success
            elif isinstance(result, int):
                return result
            else:
                return 0

      **"return_none"**

         Always returns None, regardless of the command's return value.

         .. code-block:: python

            return None

      **"return_zero"**

         Always returns 0, regardless of the command's return value.

         .. code-block:: python

            return 0

      **"print_return_zero"**

         Always prints the result (even None), then always returns 0.

         .. code-block:: python

            print(result)
            return 0

      **"sys_exit_zero"**

         Always calls :func:`sys.exit(0) <sys.exit>`, regardless of the command's return value.

         .. code-block:: python

            sys.exit(0)

      **"print_sys_exit_zero"**

         Always prints the result (even None), then calls :func:`sys.exit(0) <sys.exit>`.

         .. code-block:: python

            print(result)
            sys.exit(0)

      **Custom Callable**

         Provide a function for fully custom result handling. Receives the command's return value and returns a processed value.

         .. code-block:: python

            def custom_handler(result):
                if result is None:
                    return 0
                elif isinstance(result, str):
                    print(f"[OUTPUT] {result}")
                    return 0
                return result

            app = App(result_action=custom_handler)

      **Sequence of Actions**

         Provide a sequence (list or tuple) of actions to create a result-processing pipeline. Actions are applied left-to-right, with each action receiving the result of the previous action.

         .. code-block:: python

            def uppercase(result):
                return result.upper() if isinstance(result, str) else result

            def add_prefix(result):
                return f"[OUTPUT] {result}" if isinstance(result, str) else result

            # Pipeline: result → uppercase → add_prefix → return
            app = App(result_action=[uppercase, add_prefix, "return_value"])

            @app.command
            def greet(name: str) -> str:
                return f"hello {name}"

            result = app(["greet", "world"])
            # result == "[OUTPUT] HELLO WORLD"

         Actions in a sequence can be any combination of predefined literal strings and custom callables. Empty sequences raise a ``ValueError`` at app initialization.

      Example:

      .. code-block:: python

         from cyclopts import App

         # For CLI applications with console_scripts entry points
         app = App(result_action="print_non_int_return_int_as_exit_code")

         @app.command
         def greet(name: str) -> str:
             return f"Hello {name}!"

         app()

      See :ref:`Result Action` for detailed examples and usage patterns.

.. autoclass:: cyclopts.Parameter
   :special-members: __call__

   .. attribute:: name
      :type: Union[None, str, Iterable[str]]
      :value: None

      Name(s) to expose to the CLI.
      If not specified, cyclopts will apply :attr:`name_transform` to the python parameter name.

      .. code-block:: python

         from cyclopts import App, Parameter
         from typing import Annotated

         app = App()

         @app.default
         def main(foo: Annotated[int, Parameter(name=("bar", "-b"))]):
            print(f"{foo=}")

         app()

      .. code-block:: console

         $ my-script --help
         Usage: main COMMAND [ARGS] [OPTIONS]

         ╭─ Commands ─────────────────────────────────────────────────────╮
         │ --help -h  Display this message and exit.                      │
         │ --version  Display application version.                        │
         ╰────────────────────────────────────────────────────────────────╯
         ╭─ Parameters ───────────────────────────────────────────────────╮
         │ *  BAR --bar  -b  [required]                                   │
         ╰────────────────────────────────────────────────────────────────╯

         $ my-script --bar 100
         foo=100

         $ my-script -b 100
         foo=100

      If specifying name in a nested data structure (e.g. a dataclass), beginning the name with a hyphen ``-`` will override any hierarchical dot-notation.

      .. code-block:: python

         from cyclopts import App, Parameter
         from dataclasses import dataclass
         from typing import Annotated

         app = App()

         @dataclass
         class User:
            id: int  # default behavior
            email: Annotated[str, Parameter(name="--email")]  # overrides
            pwd: Annotated[str, Parameter(name="password")]  # dot-notation with parent

         @app.command
         def create(user: User):
            print(f"Creating {user=}")

         app()

      .. code-block:: console

         $ my-script create --help
         Usage: scratch.py create [ARGS] [OPTIONS]

         ╭─ Parameters ───────────────────────────────────────────────────╮
         │ *  USER.ID --user.id  [required]                               │
         │ *  EMAIL --email      [required]                               │
         │ *  USER.PASSWORD      [required]                               │
         │      --user.password                                           │
         ╰────────────────────────────────────────────────────────────────╯

   .. attribute:: alias
      :type: Union[None, str, Iterable[str]]
      :value: None

      Additional name(s) to expose to the CLI.
      Unlike :attr:`.name`, this does not override Cyclopts-derived names.

      The following two examples are functionally equivalent:

      .. code-block:: python

         @app.default
         def main(foo: Annotated[int, Parameter(name=["--foo", "-f"])]):
             pass

      .. code-block:: python

         @app.default
         def main(foo: Annotated[int, Parameter(alias="-f")]):
             pass

   .. attribute:: converter
      :type: Optional[Callable]
      :value: None

      A function that converts tokens into an object. The converter should have signature:

      .. code-block:: python

          def converter(type_, tokens) -> Any:
              pass

      Where ``type_`` is the parameter's type hint, and ``tokens`` is either:

      * A ``list[cyclopts.Token]`` of CLI tokens (most commonly).

        .. code-block:: python

           from cyclopts import App, Parameter
           from typing import Annotated

           app = App()

           def converter(type_, tokens):
              assert type_ == tuple[int, int]
              return tuple(2 * int(x.value) for x in tokens)

           @app.default
           def main(coordinates: Annotated[tuple[int, int], Parameter(converter=converter)]):
              print(f"{coordinates=}")

           app()

        .. code-block:: console

           $ python my-script.py 7 12
           coordinates=(14, 24)

      * A ``dict`` of :class:`.Token` if keys are specified in the CLI. E.g.

        .. code-block:: console

           $ python my-script.py --foo.key1=val1

        would be parsed into:

        .. code-block:: python

           tokens = {
              "key1": ["val1"],
           }

      If not provided, defaults to Cyclopts's internal coercion engine.
      If a pydantic type-hint is provided, Cyclopts will disable its internal coercion
      engine (including this `converter` argument) and leave the coercion to pydantic.

      The number of tokens passed to the converter is inferred from the type hint by default,
      but can be explicitly controlled with :attr:`~.Parameter.n_tokens`. This is useful when
      the type signature doesn't match the desired CLI token consumption. When loading complex
      objects with multiple fields, it may also be useful to combine with :attr:`~.Parameter.accepts_keys`.

      **Decorating Converters:** Converter functions can be decorated with :class:`.Parameter` to define
      reusable conversion behavior:

      .. code-block:: python

         @Parameter(n_tokens=1, accepts_keys=False)
         def load_from_id(type_, tokens):
             """Load object from database by ID."""
             return fetch_from_db(tokens[0].value)

         @app.default
         def main(obj: Annotated[MyType, Parameter(converter=load_from_id)]):
             # Automatically inherits n_tokens=1 and accepts_keys=False
             pass

      **Classmethod Support:** Converters can be classmethods. Use string references for class decoration
      or direct references in annotations. Classmethod signature should be ``(cls, tokens)`` instead of
      ``(type_, tokens)``:

      .. code-block:: python

         @Parameter(converter="from_env")
         class Config:
             @Parameter(n_tokens=1, accepts_keys=False)
             @classmethod
             def from_env(cls, tokens):
                 env = tokens[0].value
                 configs = {"dev": ("localhost", 8080), "prod": ("api.example.com", 443)}
                 return cls(*configs[env])


   .. attribute:: validator
      :type: Union[None, Callable, Iterable[Callable]]
      :value: None

      A function (or list of functions) that validates data returned by the :attr:`converter`.

      .. code-block:: python

          def validator(type_, value: Any) -> None:
              pass  # Raise a TypeError, ValueError, or AssertionError here if data is invalid.

   .. attribute:: group
      :type: Union[None, str, Group, Iterable[Union[str, Group]]]
      :value: None

      The group(s) that this parameter belongs to.
      This can be used to better organize the help-page, and/or to add additional conversion/validation logic (such as ensuring mutually-exclusive arguments).

      If :obj:`None`, defaults to one of the following groups:

      1. Parenting :attr:`.App.group_arguments` if the parameter is ``POSITIONAL_ONLY``.
         By default, this is ``Group("Arguments")``.

      2. Parenting :attr:`.App.group_parameters` otherwise.
         By default, this is ``Group("Parameters")``.

      See :ref:`Groups` for examples.

   .. attribute:: negative
      :type: Union[None, str, Iterable[str]]
      :value: None

      Name(s) for empty iterables or false boolean flags.

      * For booleans, defaults to ``no-{name}`` (see :attr:`negative_bool`).

      * For iterables, defaults to ``empty-{name}`` (see :attr:`negative_iterable`).

      Set to an empty list or string to disable the creation of negative flags.

      Example usage:

      .. code-block:: python

         from cyclopts import App, Parameter
         from typing import Annotated

         app = App()

         @app.default
         def main(*, verbose: Annotated[bool, Parameter(negative="--quiet")] = False):
            print(f"{verbose=}")

         app()

      .. code-block:: console

         $ my-script --help
         Usage: main COMMAND [ARGS] [OPTIONS]

         ╭─ Commands ─────────────────────────────────────────────────────╮
         │ --help -h  Display this message and exit.                      │
         │ --version  Display application version.                        │
         ╰────────────────────────────────────────────────────────────────╯
         ╭─ Parameters ───────────────────────────────────────────────────╮
         │ --verbose --quiet  [default: False]                            │
         ╰────────────────────────────────────────────────────────────────╯

   .. attribute:: negative_bool
      :type: Optional[str]
      :value: None

      Prefix for negative boolean flags. Defaults to ``"no-"``.

   .. attribute:: negative_iterable
      :type: Optional[str]
      :value: None

      Prefix for empty iterables (like lists and sets) flags. Defaults to ``"empty-"``.

   .. attribute:: negative_none
      :type: Optional[str]
      :value: None

      Prefix for setting optional parameters to :obj:`None`.
      Not enabled by default (no prefixes set).

      Example:

      .. code-block:: python

         from pathlib import Path
         from typing import Annotated

         from cyclopts import App, Parameter

         app = App(
            default_parameter=Parameter(negative_none="none-")
         )

         @app.default
         def default(path: Path | None = Path("data.bin")):
             print(f"{path=}")

         app()

      .. code-block:: console

         $ my-script
         path=PosixPath('data.bin')

         $ my-script --path=cat.jpeg
         path=PosixPath('cat.jpeg')

         $ my-script --none-path
         path=None

   .. attribute:: allow_leading_hyphen
      :type: bool
      :value: False

      Allow parsing non-numeric values that begin with a hyphen ``-``.
      This is disabled (:obj:`False`) by default, allowing for more helpful error messages for unknown CLI options.

   .. attribute:: parse
      :type: Union[None, bool, str, re.Pattern]
      :value: None

      Attempt to use this parameter while parsing.
      Annotated parameter **must** be keyword-only or have a default value.
      This is intended to be used with :ref:`meta apps <Meta App>` for injecting values.

      * :obj:`True` - Parse this parameter from CLI tokens.
      * :obj:`False` - Do not parse; parameter will appear in the ``ignored`` dict from :meth:`.App.parse_args`.
      * :obj:`None` - Default behavior (parse).
      * :obj:`str` - A regex pattern; parse **if the pattern matches the parameter name**, otherwise skip. String patterns are automatically compiled to :class:`re.Pattern` for performance.
      * :class:`re.Pattern` - A pre-compiled regex pattern; same behavior as string patterns.

      Regex patterns are primarily intended for use with :attr:`.App.default_parameter` to define app-wide skip patterns. For example, if we wanted to skip all fields that begin with an underscore ``_``:

      .. code-block:: python

         import re
         from cyclopts import App, Parameter

         # Skip parsing underscore-prefixed KEYWORD_ONLY parameters (i.e. private parameters)
         # Both string and pre-compiled patterns are supported:
         app = App(default_parameter=Parameter(parse="^(?!_)"))
         # or: app = App(default_parameter=Parameter(parse=re.compile("^(?!_)")))

         @app.default
         def main(visible: str, *, _injected: str = "default"):
             # _injected is NOT parsed from CLI; uses default value
             pass

   .. attribute:: required
      :type: Optional[bool]
      :value: None

      Indicates that the parameter must be supplied.
      Defaults to inferring from the function signature; i.e. :obj:`False` if the parameter has a default, :obj:`True` otherwise.

   .. attribute:: show
      :type: Optional[bool]
      :value: None

      Show this parameter on the help screen.
      Defaults to whether the parameter is :attr:`parsed <.Parameter.parse>` (usually :obj:`True`).

   .. attribute:: show_default
      :type: Union[None, bool, Callable[[Any], Any]]
      :value: None

      If a variable has a default, display the default on the help page.
      Defaults to :obj:`None`, similar to :obj:`True`, but will **not** display the default if it is :obj:`None`.

      If set to a function with signature:

      .. code-block:: python

         def formatter(value: Any) -> Any:
             ...

      Then the function will be called with the default value, and the returned value will be used as the displayed default value.

      Example formatting function:

      .. code-block:: python

         def hex_formatter(value: int) -> str
            """Will result in something like "[default: 0xFF]" instead of "[default: 255]"."""
            return f"0x{value:X}"

   .. attribute:: show_choices
      :type: Optional[bool]
      :value: True

      If a variable has a set of choices, display the choices on the help page.

   .. attribute:: help
      :type: Optional[str]
      :value: None

      Help string to be displayed on the help page.
      If not specified, defaults to the docstring.

   .. attribute:: show_env_var
      :type: Optional[bool]
      :value: True

      If a variable has :attr:`env_var` set, display the variable name on the help page.

   .. attribute:: env_var
      :type: Union[None, str, Iterable[str]]
      :value: None

      Fallback to environment variable(s) if CLI value not provided.
      If multiple environment variables are given, the left-most environment variable **with a set value** will be used.
      If no environment variable is set, Cyclopts will fallback to the function-signature default.

   .. attribute:: env_var_split
      :type: Callable
      :value: cyclopts.env_var_split

      Function that splits up the read-in :attr:`~cyclopts.Parameter.env_var` value.
      The function must have signature:

      .. code-block:: python

         def env_var_split(type_: type, val: str) -> list[str]:
             ...

      where ``type_`` is the associated parameter type-hint, and ``val`` is the environment value.

   .. attribute:: name_transform
      :type: Optional[Callable[[str], str]]
      :value: None

      A function that converts python parameter names to their CLI command counterparts.

      The function must have signature:

      .. code-block:: python

         def name_transform(s: str) -> str:
             ...

      If :obj:`None` (default value), uses :func:`cyclopts.default_name_transform`.

   .. attribute:: accepts_keys
      :type: Optional[bool]
      :value: None

      If :obj:`False`, treat the user-defined class annotation similar to a tuple.
      Individual class sub-parameters will not be addressable by CLI keywords.
      The class will consume enough tokens to populate all required positional parameters.

      Default behavior (``accepts_keys=True``):

      .. code-block:: python

         from cyclopts import App, Parameter
         from typing import Annotated

         app = App()

         class Image:
            def __init__(self, path, label):
               self.path = path
               self.label = label

            def __repr__(self):
               return f"Image(path={self.path!r}, label={self.label!r})"

         @app.default
         def main(image: Image):
            print(f"{image=}")

         app()

      .. code-block:: console

         $ my-program --help
         Usage: main COMMAND [ARGS] [OPTIONS]

         ╭─ Commands ──────────────────────────────────────────────────────────╮
         │ --help -h  Display this message and exit.                           │
         │ --version  Display application version.                             │
         ╰─────────────────────────────────────────────────────────────────────╯
         ╭─ Parameters ────────────────────────────────────────────────────────╮
         │ *  IMAGE.PATH --image.path    [required]                            │
         │ *  IMAGE.LABEL --image.label  [required]                            │
         ╰─────────────────────────────────────────────────────────────────────╯

         $ my-program foo.jpg nature
         image=Image(path='foo.jpg', label='nature')

         $ my-program --image.path foo.jpg --image.label nature
         image=Image(path='foo.jpg', label='nature')

      Behavior when ``accepts_keys=False``:

      .. code-block:: python

         # Modify the default command function's signature.
         @app.default
         def main(image: Annotated[Image, Parameter(accepts_keys=False)]):
            print(f"{image=}")

      .. code-block:: console

         $ my-program --help
         Usage: main COMMAND [ARGS] [OPTIONS]

         ╭─ Commands ──────────────────────────────────────────────────────────╮
         │ --help -h  Display this message and exit.                           │
         │ --version  Display application version.                             │
         ╰─────────────────────────────────────────────────────────────────────╯
         ╭─ Parameters ────────────────────────────────────────────────────────╮
         │ *  IMAGE --image  [required]                                        │
         ╰─────────────────────────────────────────────────────────────────────╯

         $ my-program foo.jpg nature
         image=Image(path='foo.jpg', label='nature')

         $ my-program --image foo.jpg nature
         image=Image(path='foo.jpg', label='nature')

      The ``accepts_keys=False`` option is commonly used with :attr:`~.Parameter.converter` and
      :attr:`~.Parameter.n_tokens`.

   .. attribute:: consume_multiple
      :type: Optional[bool]
      :value: None

      Lists use `different parsing rules <rules.html#list>`__ depending on whether the values are provided positionally or by keyword. If the parameter is specified **positionally**, :attr:`.Parameter.consume_multiple` is ignored.

      If the parameter is specified **by keyword** and ``consume_multiple=True``, all remaining CLI tokens will be consumed until the stream is exhausted or an option-like token (typically a keyword) is reached (unless :attr:`.Parameter.allow_leading_hyphen` is :obj:`True`, in which case it will also be consumed).

      .. code-block:: python

         from cyclopts import App, Parameter
         from typing import Annotated

         app = App()

         @app.command
         def name_ext(
             name: str,
             ext: Annotated[list[str], Parameter(consume_multiple=True)],
         ):
             for extension in ext:
                 print(f"{name}.{extension}")

         app()

      .. code-block:: console

         $ my-program --name "my_file" --ext "txt" "pdf"  # stream is exhausted
         my_file.txt
         my_file.pdf

         $ my-program --ext "txt" "pdf" --name "my_file"  # a keyword is reached
         my_file.txt
         my_file.pdf

      When ``consume_multiple=True``, providing the keyword flag without any values will create an empty container, equivalent to using the :attr:`negative_iterable` prefix (e.g., ``--empty-ext``):

      .. code-block:: console

         $ my-program --name "my_file" --ext
         # No output - ext is an empty list []

         $ my-program --name "my_file" --empty-ext
         # No output - ext is an empty list []

      If the parameter is specified **by keyword** and ``consume_multiple=False`` (the default), only a single element worth of CLI tokens will be consumed.

      .. code-block:: python

         from cyclopts import App
         from pathlib import Path

         app = App()

         @app.default
         def name_ext(name: str, ext: list[str]): # same as `ext: Annotated[list[str], Parameter(consume_multiple=False)]``
             for extension in ext:
                 print(f"{name}.{extension}")

         app()

      .. code-block:: console

         $ my-program --name "my_file" --ext "txt" "pdf"
         ╭─ Error ────────────────────────────────────────────╮
         │ Unused Tokens: ['pdf'].                            │
         ╰────────────────────────────────────────────────────╯

   .. attribute:: json_dict
      :type: Optional[bool]
      :value: None

      Allow for the parsing of json-dict-strings as data.
      If :obj:`None` (default behavior), acts like :obj:`True`, **unless** the annotated type is union'd with :obj:`str`.
      When :obj:`True`, data will be parsed as json if the following conditions are met:

      1. The parameter is specified as a keyword option; e.g. ``--movie``.

      2. The referenced parameter is dataclass-like.

      3. The first character of the token is a ``{``.

   .. attribute:: json_list
      :type: Optional[bool]
      :value: None

      Allow for the parsing of json-list-strings as data.
      If :obj:`None` (default behavior), acts like :obj:`True`, **unless** the annotated type has each element type :obj:`str`.
      When :obj:`True`, data will be parsed as json if the following conditions are met:

      1. The referenced parameter is iterable (not including :obj:`str`).

      2. The first character of the token is a ``[``.

   .. attribute:: count
      :type: bool
      :value: False

      If :obj:`True`, count the number of times the flag appears instead of parsing a value.
      Each occurrence increments the count by 1 (e.g., ``-vvv`` results in ``3``).

      Requirements and behavior:

      * The parameter **must** have an :obj:`int` type hint (or ``Optional[int]``).
      * Short flags can be concatenated: ``-vvv`` is equivalent to ``-v -v -v``.
      * Long flags can be repeated: ``--verbose --verbose`` results in ``2``.
      * Negative flag variants (e.g., ``--no-verbose``) are **not** generated.

      Common use case: verbosity levels.

      .. code-block:: python

         from cyclopts import App, Parameter
         from typing import Annotated

         app = App()

         @app.default
         def main(verbose: Annotated[int, Parameter(name="-v", count=True)] = 0):
            print(f"Verbosity level: {verbose}")

         app()

      .. code-block:: console

         $ my-script -vvv
         Verbosity level: 3

      See :ref:`Coercion Rules` for more details.

   .. attribute:: n_tokens
      :type: Optional[int]
      :value: None

      Explicitly override the number of CLI tokens this parameter consumes.

      By default, Cyclopts infers the token count from the parameter's type hint
      (e.g., :obj:`int` consumes 1 token, ``tuple[int, int]`` consumes 2, :obj:`list` consumes all remaining).
      This attribute allows you to override that inference, which is particularly useful when:

      * Using custom converters that need a different token count than the type suggests.
      * Loading complex types from a single token (e.g., loading from a file path).
      * Implementing selection/lookup patterns where one token identifies an object.

      Values:

      * ``None`` (default): Infer token count from the type hint.
      * non-negative integer: Consume exactly that many tokens.
      * ``-1``: Consume all remaining tokens (similar to iterables).

      For ``*args`` parameters, ``n_tokens`` specifies tokens **per element**.
      For example, ``n_tokens=2`` with 6 tokens creates 3 elements.

      .. code-block:: python

         from cyclopts import App, Parameter
         from typing import Annotated

         class Config:
             def __init__(self, host: str, port: int):
                 self.host = host
                 self.port = port

         def load_config(type_, tokens):
             # Load config from a file path (single token)
             filepath = tokens[0].value
             # ... load from file ...
             return Config("example.com", 8080)

         app = App()

         @app.default
         def main(
             config: Annotated[
                 Config,
                 Parameter(n_tokens=1, converter=load_config, accepts_keys=False)
             ]
         ):
             print(f"Connecting to {config.host}:{config.port}")

         app()

      .. code-block:: console

         $ my-script --config prod.conf
         Connecting to example.com:8080

   .. automethod:: combine

   .. automethod:: default

.. autoclass:: cyclopts.Group
   :members: create_ordered

   A group of parameters and/or commands in a CLI application.

   .. attribute:: name
      :type: str
      :value: ""

      Group name used for the help-page and for group-referenced-by-string.
      This is a title, so the first character should be capitalized.
      If a name is not specified, it will not be shown on the help-page.

   .. attribute:: help
      :type: str
      :value: ""

      Additional documentation shown on the help-page.
      This will be displayed inside the group's panel, above the parameters/commands.

   .. attribute:: show
      :type: Optional[bool]
      :value: None

      Show this group on the help-page.
      Defaults to :obj:`None`, which will only show the group if a ``name`` is provided.

   .. attribute:: help_formatter
      :type: Union[None, Literal["default", "plain"], HelpFormatter]
      :value: None

      Help formatter to use for rendering this group's help panel.

      * If :obj:`None` (default), inherits from the :class:`.App`'s :attr:`~.App.help_formatter`.

      * If ``"default"``, uses :class:`~cyclopts.help.DefaultFormatter`.

      * If ``"plain"``, uses :class:`~cyclopts.help.PlainFormatter` for no-frills plain text output.

      * If a callable (see :class:`~cyclopts.help.protocols.HelpFormatter` protocol), uses the provided formatter.

      This allows per-group customization of help appearance:

      .. code-block:: python

         from cyclopts import App, Group, Parameter
         from cyclopts.help import DefaultFormatter, PanelSpec
         from typing import Annotated

         app = App()

         # Using string literal
         simple_group = Group(
             "Simple Options",
             help_formatter="plain"
         )

         # Using custom formatter instance
         custom_group = Group(
             "Custom Options",
             help_formatter=DefaultFormatter(
                 panel_spec=PanelSpec(border_style="red")
             )
         )

         @app.default
         def main(
             opt1: Annotated[str, Parameter(group=simple_group)],
             opt2: Annotated[str, Parameter(group=custom_group)]
         ):
             pass

      See :ref:`Help Customization` for detailed examples.

   .. attribute:: sort_key
      :type: Any
      :value: None

      Modifies group-panel display order on the help-page.

      1. If :attr:`sort_key` is a generator, it will be consumed immediately with :func:`next` to get the actual value.

      2. If :attr:`sort_key`, or any of it's contents, are ``Callable``, then invoke it ``sort_key(group)`` and apply the rules below.

      3. The :class:`.App` default groups (:attr:`.App.group_command`, :attr:`.App.group_arguments`, :attr:`.App.group_parameters`) will be displayed first.
         If you want to further customize the ordering of these default groups, you can define custom values and they will be treated like any other group:

         .. code-block:: python

            from cyclopts import App, Group

            app = App(
                group_parameters=Group("Parameters", sort_key=1),
                group_arguments=Group("Arguments", sort_key=2),
                group_commands=Group("Commands", sort_key=3),
            )


            @app.default
            def main(foo, /, bar):
                pass


            if __name__ == "__main__":
                app()

        .. code-block:: console

            $ python main.py --help
            Usage: main [ARGS] [OPTIONS]

            ╭─ Parameters ──────────────────────────────────────────────────────────╮
            │ *  BAR --bar  [required]                                              │
            ╰───────────────────────────────────────────────────────────────────────╯
            ╭─ Arguments ───────────────────────────────────────────────────────────╮
            │ *  FOO  [required]                                                    │
            ╰───────────────────────────────────────────────────────────────────────╯
            ╭─ Commands ────────────────────────────────────────────────────────────╮
            │ --help -h  Display this message and exit.                             │
            │ --version  Display application version.                               │
            ╰───────────────────────────────────────────────────────────────────────╯

      4. For all groups with ``sort_key!=None``, sort them by ``(sort_key, group.name)``.
         That is, sort them by their ``sort_key``, and then break ties alphabetically.
         It is the user's responsibility that ``sort_key`` are comparable.

      5. For all groups with ``sort_key==None`` (default value), sort them alphabetically after (4), :attr:`.App.group_commands`, :attr:`.App.group_arguments`, and :attr:`.App.group_parameters`.

      Example usage:

      .. code-block:: python

         from cyclopts import App, Group

         app = App()

         @app.command(group=Group("4", sort_key=5))
         def cmd1():
             pass


         @app.command(group=Group("3", sort_key=lambda x: 10))
         def cmd2():
             pass


         @app.command(group=Group("2", sort_key=lambda x: None))
         def cmd3():
             pass


         @app.command(group=Group("1"))
         def cmd4():
             pass

         app()

      Resulting help-page:

      .. code-block:: text

        Usage: app COMMAND

        ╭─ 4 ────────────────────────────────────────────────────────────────╮
        │ cmd1                                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ 3 ────────────────────────────────────────────────────────────────╮
        │ cmd2                                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ 1 ────────────────────────────────────────────────────────────────╮
        │ cmd4                                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ 2 ────────────────────────────────────────────────────────────────╮
        │ cmd3                                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help,-h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯

   .. attribute:: default_parameter
      :type: Optional[Parameter]
      :value: None

      Default :class:`.Parameter` in the parameter-resolution-stack that goes between :attr:`.App.default_parameter` and the function signature's :obj:`Annotated` :class:`.Parameter`.
      The provided :class:`.Parameter` is not allowed to have a :attr:`~.Parameter.group` value.

   .. attribute:: validator
      :type: Optional[Callable]
      :value: None

      A function (or list of functions) that validates an :class:`.ArgumentCollection`.

      Example usage:

      .. code-block:: python

         def validator(argument_collection: ArgumentCollection):
             "Raise an exception if something is invalid."

      The :class:`.ArgumentCollection` will contain all arguments that belong to that group.
      The validator(s) will **always be invoked**, regardless if any argument within the collection has token(s).

      Validators are **not** invoked for command groups.

.. autoclass:: cyclopts.Token

   .. attribute:: keyword
      :type: Optional[str]
      :value: None

      **Unadulterated** user-supplied keyword like ``--foo`` or ``--foo.bar.baz``; ``None`` when token was pared positionally.
      Could also be something like ``tool.project.foo`` if from non-cli sources.

   .. attribute:: value
      :type: str
      :value: ""

      The parsed token value (unadulterated).

   .. attribute:: source
      :type: str
      :value: ""

      Where the token came from; used for error message purposes.
      Cyclopts uses the string ``cli`` for cli-parsed tokens.

   .. attribute:: index
      :type: int
      :value: 0

      The relative positional index in which the value was provided.

   .. attribute:: keys
      :type: tuple[str, ...]
      :value: ()

      The additional parsed **python** variable keys from :attr:`keyword`.

      Only used for Arguments that take arbitrary keys.

   .. attribute:: implicit_value
      :type: Any
      :value: cyclopts.UNSET

      Final value that should be used instead of converting from :attr:`value`.

      Commonly used for boolean flags.

      Ignored if :obj:`~.UNSET`.

.. autoclass:: cyclopts.field_info.FieldInfo

.. autoclass:: cyclopts.Argument
   :members:

.. autoclass:: cyclopts.ArgumentCollection
   :members:

.. autoclass:: cyclopts.UNSET

.. autofunction:: cyclopts.default_name_transform

.. autofunction:: cyclopts.env_var_split

.. autofunction:: cyclopts.edit

.. autofunction:: cyclopts.run

.. autoclass:: cyclopts.CycloptsPanel

.. _API Validators:

----------
Validators
----------
Cyclopts has several builtin validators for common CLI inputs.

.. autoclass:: cyclopts.validators.LimitedChoice
   :members:

.. autoclass:: cyclopts.validators.MutuallyExclusive
   :members:

.. autodata:: cyclopts.validators.mutually_exclusive

   Instantiated version of :class:`~.validators.MutuallyExclusive`.
   Can be used directly in group validators:

   .. code-block:: python

       import cyclopts
       from cyclopts import Group

       mutually_exclusive_group = Group(validator=cyclopts.validators.mutually_exclusive)

.. autodata:: cyclopts.validators.all_or_none

   Group validator that enforces that either all parameters in the group must be supplied an argument, or none of them.

.. autoclass:: cyclopts.validators.Number
   :members:

.. autoclass:: cyclopts.validators.Path
   :members:


.. _Annotated Types:

-----
Types
-----
Cyclopts has builtin pre-defined annotated-types for common conversion and validation configurations.
Most definitions in this section are simply predefined annotations for convenience:

.. code-block:: python

   Annotated[..., Parameter(...)]

Custom classes that provide additional functionality beyond simple annotations will be noted.

Due to Cyclopts's advanced :class:`.Parameter` resolution engine, these annotations can themselves be annotated to further configure behavior. E.g:

.. code-block:: python

   Annotated[PositiveInt, Parameter(...)]

.. _Annotated Path Types:

^^^^
Path
^^^^
:class:`~pathlib.Path` annotated types for checking existence, type, and performing path-resolution.
All of these types will also work on sequence of paths (e.g. ``tuple[Path, Path]`` or ``list[Path]``).

.. class:: cyclopts.types.StdioPath

   .. note::
      This is a custom class, not a simple :obj:`~typing.Annotated` type alias.

      Requires **Python 3.12+** due to :class:`~pathlib.Path` subclassing support.

   A :class:`~pathlib.Path` subclass that treats ``-`` as stdin (for reading) or stdout (for writing).
   This follows `common Unix convention <https://clig.dev/#arguments-and-flags>`_.

   :class:`StdioPath` is pre-configured with ``allow_leading_hyphen=True``, so ``-`` can be passed as an argument without being interpreted as an option.

   .. attribute:: STDIO_STRING
      :type: str
      :value: "-"

      Class attribute defining the string that triggers stdio behavior.
      Override in subclasses to use a different string.

   .. attribute:: is_stdio
      :type: bool

      Returns :obj:`True` if this path represents stdin/stdout (i.e., ``str(self) == STDIO_STRING``).
      Override this property in subclasses for custom matching logic (e.g., matching multiple strings).

   Basic usage:

   .. code-block:: python

      from cyclopts import App
      from cyclopts.types import StdioPath

      app = App()

      @app.default
      def main(input_file: StdioPath):
          data = input_file.read_text()
          print(data.upper())

      app()

   .. code-block:: console

      $ echo "hello" | python my_script.py -
      HELLO

      $ python my_script.py data.txt
      <contents of data.txt uppercased>

   To default to stdin/stdout when no argument is provided:

   .. code-block:: python

      @app.default
      def main(input_file: StdioPath = StdioPath("-")):
          data = input_file.read_text()
          print(data.upper())

   See :ref:`Reading/Writing From File or Stdin/Stdout` for more examples.

   **Subclassing**

   To use a different trigger string or custom matching logic, subclass :class:`StdioPath`:

   .. code-block:: python

      from cyclopts.types import StdioPath

      # Simple: different trigger string
      class StdinPath(StdioPath):
          STDIO_STRING = "STDIN"

      class StdoutPath(StdioPath):
          STDIO_STRING = "STDOUT"

      # Advanced: match multiple strings
      class MultiStdioPath(StdioPath):
          @property
          def is_stdio(self) -> bool:
              return str(self) in ("-", "STDIN", "STDOUT")

.. autodata:: cyclopts.types.ExistingPath

.. autodata:: cyclopts.types.NonExistentPath

.. autodata:: cyclopts.types.ResolvedPath

.. autodata:: cyclopts.types.ResolvedExistingPath

.. autodata:: cyclopts.types.Directory

.. autodata:: cyclopts.types.ExistingDirectory

.. autodata:: cyclopts.types.NonExistentDirectory

.. autodata:: cyclopts.types.ResolvedDirectory

.. autodata:: cyclopts.types.ResolvedExistingDirectory

.. autodata:: cyclopts.types.File

.. autodata:: cyclopts.types.ExistingFile

.. autodata:: cyclopts.types.NonExistentFile

.. autodata:: cyclopts.types.ResolvedFile

.. autodata:: cyclopts.types.ResolvedExistingFile

.. autodata:: cyclopts.types.BinPath

.. autodata:: cyclopts.types.ExistingBinPath

.. autodata:: cyclopts.types.NonExistentBinPath

.. autodata:: cyclopts.types.CsvPath

.. autodata:: cyclopts.types.ExistingCsvPath

.. autodata:: cyclopts.types.NonExistentCsvPath

.. autodata:: cyclopts.types.TxtPath

.. autodata:: cyclopts.types.ExistingTxtPath

.. autodata:: cyclopts.types.NonExistentTxtPath

.. autodata:: cyclopts.types.ImagePath

.. autodata:: cyclopts.types.ExistingImagePath

.. autodata:: cyclopts.types.NonExistentImagePath

.. autodata:: cyclopts.types.Mp4Path

.. autodata:: cyclopts.types.ExistingMp4Path

.. autodata:: cyclopts.types.NonExistentMp4Path

.. autodata:: cyclopts.types.JsonPath

.. autodata:: cyclopts.types.ExistingJsonPath

.. autodata:: cyclopts.types.NonExistentJsonPath

.. autodata:: cyclopts.types.TomlPath

.. autodata:: cyclopts.types.ExistingTomlPath

.. autodata:: cyclopts.types.NonExistentTomlPath

.. autodata:: cyclopts.types.YamlPath

.. autodata:: cyclopts.types.ExistingYamlPath

.. autodata:: cyclopts.types.NonExistentYamlPath

.. _Annotated Number Types:

^^^^^^
Number
^^^^^^
Annotated types for checking common int/float value constraints.
All of these types will also work on sequence of numbers (e.g. ``tuple[int, int]`` or ``list[float]``).

.. autodata:: cyclopts.types.PositiveFloat

.. autodata:: cyclopts.types.NonNegativeFloat

.. autodata:: cyclopts.types.NegativeFloat

.. autodata:: cyclopts.types.NonPositiveFloat

.. autodata:: cyclopts.types.PositiveInt

.. autodata:: cyclopts.types.NonNegativeInt

.. autodata:: cyclopts.types.NegativeInt

.. autodata:: cyclopts.types.NonPositiveInt

.. autodata:: cyclopts.types.UInt8

.. autodata:: cyclopts.types.HexUInt8

.. autodata:: cyclopts.types.Int8

.. autodata:: cyclopts.types.UInt16

.. autodata:: cyclopts.types.HexUInt16

.. autodata:: cyclopts.types.Int16

.. autodata:: cyclopts.types.UInt32

.. autodata:: cyclopts.types.HexUInt32

.. autodata:: cyclopts.types.Int32

.. autodata:: cyclopts.types.UInt64

.. autodata:: cyclopts.types.HexUInt64

.. autodata:: cyclopts.types.Int64

^^^^
Json
^^^^
Annotated types for parsing a json-string from the CLI.

.. autodata:: cyclopts.types.Json

.. _API Config:


^^^
Web
^^^
Annotated types for common web-related values.

.. autodata:: cyclopts.types.Email

.. autodata:: cyclopts.types.Port

.. autodata:: cyclopts.types.URL

---------------
Help Formatting
---------------
Cyclopts provides a flexible help formatting system for customizing the help-page's appearance.

.. autoclass:: cyclopts.help.protocols.HelpFormatter
   :members:


.. autoclass:: cyclopts.help.DefaultFormatter
   :members:


.. autoclass:: cyclopts.help.PlainFormatter
   :members:


.. autoclass:: cyclopts.help.protocols.ColumnSpecBuilder
   :members:


.. autoclass:: cyclopts.help.PanelSpec
   :members:


.. autoclass:: cyclopts.help.TableSpec
   :members:


.. autoclass:: cyclopts.help.ColumnSpec
   :members:


.. autoclass:: cyclopts.help.NameRenderer
   :members:


.. autoclass:: cyclopts.help.DescriptionRenderer
   :members:


.. autoclass:: cyclopts.help.AsteriskRenderer
   :members:


.. autoclass:: cyclopts.help.HelpPanel
   :members:


.. autoclass:: cyclopts.help.HelpEntry
   :members:


------
Config
------
Cyclopts has builtin configuration classes to be used with :attr:`App.config <cyclopts.App.config>` for loading user-defined defaults in many common scenarios.
All Cyclopts builtins index into the configuration file with the following rules:

1. Apply ``root_keys`` (if provided) to enter the project's configuration namespace.

2. Apply the command name(s) to enter the current command's configuration namespace.

3. Apply each key/value pair if CLI arguments have **not** been provided for that parameter.

.. autoclass:: cyclopts.config.Toml

   Automatically read configuration from Toml file.

   .. attribute:: path
      :type: str | pathlib.Path

      Path to TOML configuration file.

   .. attribute:: source
      :type: str | None
      :value: None

      Identifier for the configuration source, used in error messages.
      If not provided, defaults to the absolute path of the configuration file.

   .. attribute:: root_keys
      :type: Iterable[str]
      :value: None

      The key or sequence of keys that lead to the root configuration structure for this app.
      For example, if referencing a ``pyproject.toml``, it is common to store all of your projects configuration under:

      .. code-block:: toml

         [tool.myproject]

      So, your Cyclopts :class:`~cyclopts.App` should be configured as:

      .. code-block:: python

         app = cyclopts.App(config=cyclopts.config.Toml("pyproject.toml", root_keys=("tool", "myproject")))

   .. attribute:: must_exist
      :type: bool
      :value: False

      The configuration file MUST exist. Raises :class:`FileNotFoundError` if it does not exist.

   .. attribute:: search_parents
      :type: bool
      :value: False

      If ``path`` doesn't exist, iteratively search parenting directories for a same-named configuration file.
      Raises :class:`FileNotFoundError` if no configuration file is found.

   .. attribute:: allow_unknown
      :type: bool
      :value: False

      Allow for unknown keys. Otherwise, if an unknown key is provided, raises :class:`UnknownOptionError`.
   .. attribute:: use_commands_as_keys
      :type: bool
      :value: True

      Use the sequence of commands as keys into the configuration.

      For example, the following CLI invocation:

      .. code-block:: console

          $ python my-script.py my-command

      Would search into ``["my-command"]`` for values.

.. autoclass:: cyclopts.config.Yaml

   Automatically read configuration from YAML file.

   .. attribute:: path
      :type: str | pathlib.Path

      Path to YAML configuration file.

   .. attribute:: source
      :type: str | None
      :value: None

      Identifier for the configuration source, used in error messages.
      If not provided, defaults to the absolute path of the configuration file.

   .. attribute:: root_keys
      :type: Iterable[str]
      :value: None

      The key or sequence of keys that lead to the root configuration structure for this app.
      For example, if referencing a common ``config.yaml`` that is shared with other applications, it is common to store your projects configuration under a key like ``myproject:``.

      Your Cyclopts :class:`~cyclopts.App` would be configured as:

      .. code-block:: python

         app = cyclopts.App(config=cyclopts.config.Yaml("config.yaml", root_keys="myproject"))

   .. attribute:: must_exist
      :type: bool
      :value: False

      The configuration file MUST exist. Raises :class:`FileNotFoundError` if it does not exist.

   .. attribute:: search_parents
      :type: bool
      :value: False

      If ``path`` doesn't exist, iteratively search parenting directories for a same-named configuration file.
      Raises :class:`FileNotFoundError` if no configuration file is found.

   .. attribute:: allow_unknown
      :type: bool
      :value: False

      Allow for unknown keys. Otherwise, if an unknown key is provided, raises :class:`UnknownOptionError`.
   .. attribute:: use_commands_as_keys
      :type: bool
      :value: True

      Use the sequence of commands as keys into the configuration.

      For example, the following CLI invocation:

      .. code-block:: console

          $ python my-script.py my-command

      Would search into ``["my-command"]`` for values.


.. autoclass:: cyclopts.config.Json

   Automatically read configuration from Json file.

   .. attribute:: path
      :type: str | pathlib.Path

      Path to JSON configuration file.

   .. attribute:: source
      :type: str | None
      :value: None

      Identifier for the configuration source, used in error messages.
      If not provided, defaults to the absolute path of the configuration file.
      Can be customized to provide more descriptive error context.

      Example:

      .. code-block:: python

         app = cyclopts.App(config=cyclopts.config.Json("config.json", source="production-config"))

   .. attribute:: root_keys
      :type: Iterable[str]
      :value: None

      The key or sequence of keys that lead to the root configuration structure for this app.
      For example, if referencing a common ``config.json`` that is shared with other applications, it is common to store your projects configuration under a key like ``"myproject":``.

      Your Cyclopts :class:`~cyclopts.App` would be configured as:

      .. code-block:: python

         app = cyclopts.App(config=cyclopts.config.Json("config.json", root_keys="myproject"))

   .. attribute:: must_exist
      :type: bool
      :value: False

      The configuration file MUST exist. Raises :class:`FileNotFoundError` if it does not exist.

   .. attribute:: search_parents
      :type: bool
      :value: False

      If ``path`` doesn't exist, iteratively search parenting directories for a same-named configuration file.
      Raises :class:`FileNotFoundError` if no configuration file is found.

   .. attribute:: allow_unknown
      :type: bool
      :value: False

      Allow for unknown keys. Otherwise, if an unknown key is provided, raises :class:`UnknownOptionError`.
   .. attribute:: use_commands_as_keys
      :type: bool
      :value: True

      Use the sequence of commands as keys into the configuration.

      For example, the following CLI invocation:

      .. code-block:: console

          $ python my-script.py my-command

      Would search into ``["my-command"]`` for values.


.. autoclass:: cyclopts.config.Dict

   Use an in-memory Python dictionary as configuration source.

   .. attribute:: data
      :type: dict[str, Any]

      The configuration dictionary.

   .. attribute:: source
      :type: str
      :value: "dict"

      Identifier for the configuration source, used in error messages.

   .. attribute:: root_keys
      :type: Iterable[str]
      :value: ()

      The key or sequence of keys that lead to the root configuration structure for this app.

   .. attribute:: allow_unknown
      :type: bool
      :value: False

      Allow for unknown keys. Otherwise, if an unknown key is provided, raises :class:`UnknownOptionError`.

   .. attribute:: use_commands_as_keys
      :type: bool
      :value: True

      Use the sequence of commands as keys into the configuration.


.. autoclass:: cyclopts.config.Env

   Automatically derive environment variable names to read configurations from.

   For example, consider the following app:

   .. code-block:: python

      import cyclopts

      app = cyclopts.App(config=cyclopts.config.Env("MY_SCRIPT_"))

      @app.command
      def my_command(foo, bar):
          print(f"{foo=} {bar=}")

      app()

   If values for ``foo`` and ``bar`` are not supplied by the command line, the app will check
   the environment variables ``MY_SCRIPT_MY_COMMAND_FOO`` and ``MY_SCRIPT_MY_COMMAND_BAR``, respectively:

   .. code-block:: console

      $ python my_script.py my-command 1 2
      foo=1 bar=2

      $ export MY_SCRIPT_MY_COMMAND_FOO=100
      $ python my_script.py my-command --bar=2
      foo=100 bar=2
      $ python my_script.py my-command 1 2
      foo=1 bar=2


   .. attribute:: prefix
      :type: str
      :value: ""

      String to prepend to all autogenerated environment variable names.
      Typically ends in ``_``, and is something like ``MY_APP_``.

   .. attribute:: source
      :type: str
      :value: "env"

      Identifier for the configuration source, used in error messages and token tracking.
      Defaults to ``"env"``.

   .. attribute:: command
      :type: bool
      :value: True

      If :obj:`True`, add the command's name (uppercase) after :attr:`prefix`.

   .. attribute:: show
      :type: bool
      :value: True

      If :obj:`True`, then show the environment variables on the help-page.


----------
Exceptions
----------

.. autoexception:: cyclopts.CycloptsError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.ValidationError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.UnknownOptionError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.CoercionError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.UnknownCommandError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.UnusedCliTokensError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.MissingArgumentError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.RepeatArgumentError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.MixedArgumentError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.CommandCollisionError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.CombinedShortOptionError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.EditorError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.EditorNotFoundError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.EditorDidNotSaveError
   :show-inheritance:
   :members:

.. autoexception:: cyclopts.EditorDidNotChangeError
   :show-inheritance:
   :members:

.. _rich-rst: https://github.com/wasi-master/rich-rst
