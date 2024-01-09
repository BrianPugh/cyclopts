======
Groups
======
Groups offer a way of organizing parameters and commands on the help-page.
They also provide an additional abstraction layer that converters and validators can operate on.

Groups can be created in 2 ways:

1. Creating an instance of the :class:`.Group` object.

2. Implicitly with string title name.
   This is short for ``Group(my_group_name)``.
   If there exists a :class:`.Group` object with the same name within the command/parameter context, it will join that group.

Every command and parameter belongs to one (or more) groups.

Group(s) can be provided to the ``group`` keyword argument of :meth:`@app.command <cyclopts.App.command>` and :class:`.Parameter`.
The :class:`.Group` class itself only marks objects with metadata and doesn't contain a set of it's members.
This means that groups can be re-used across commands.

--------------
Command Groups
--------------
An example of using groups with commands:

.. code-block:: python

   from cyclopts import App, Group, Parameter

   app = App()

   # Change the group of "--help" and "--version" to the implicit "Admin" group.
   app["--help"].group = "Admin"
   app["--version"].group = "Admin"


   @app.command(group="Admin")
   def info():
       """Print debugging system information."""
       print("Displaying system info.")


   @app.command
   def download(path, url):
       """Download a file."""
       print(f"Downloading {url} to {path}.")


   @app.command
   def upload(path, url):
       """Upload a file."""
       print(f"Downloading {url} to {path}.")


   app()

.. code-block:: console

   $ python my-script.py --help
   Usage: my-script.py COMMAND

   ╭─ Admin ──────────────────────────────────────────────────────────────────────╮
   │ info       Print debugging system information.                               │
   │ --help,-h  Display this message and exit.                                    │
   │ --version  Display application version.                                      │
   ╰──────────────────────────────────────────────────────────────────────────────╯
   ╭─ Commands ───────────────────────────────────────────────────────────────────╮
   │ download  Download a file.                                                   │
   │ upload    Upload a file.                                                     │
   ╰──────────────────────────────────────────────────────────────────────────────╯

The default group is defined by the registering app's :attr:`.App.group_command`, which defaults to a group named ``"Commands"``.

----------------
Parameter Groups
----------------
An example of using groups with parameters:

.. code-block:: python

   from cyclopts import App, Group, Parameter, validators
   from typing_extensions import Annotated

   app = App()


   vehicle_type_group = Group(
       "Vehicle (choose one)",
       default_parameter=Parameter(negative=""),  # Disable "--no-" flags
       validator=validators.LimitedChoice(),  # Mutually Exclusive Options
   )


   @app.command
   def create(
       *,
       # Using an explicitly created group object.
       car: Annotated[bool, Parameter(group=vehicle_type_group)] = False,
       truck: Annotated[bool, Parameter(group=vehicle_type_group)] = False,
       # Implicitly creating an "Engine" group.
       hp: Annotated[float, Parameter(group="Engine")] = 200,
       cylinders: Annotated[int, Parameter(group="Engine")] = 6,
       # You can explicitly create groups in-line.
       wheel_diameter: Annotated[float, Parameter(group=Group("Wheels"))] = 18,
       # Groups within the function signature can always be referenced with a string.
       rims: Annotated[bool, Parameter(group="Wheels")] = False,
   ):
       pass


   app()

.. code-block:: console

   $ python my-script.py create --help
   Usage: my-script.py create [OPTIONS]

   ╭─ Vehicle (choose one) ───────────────────────────────────────────────────────╮
   │ --car    [default: False]                                                    │
   │ --truck  [default: False]                                                    │
   ╰──────────────────────────────────────────────────────────────────────────────╯
   ╭─ Engine ─────────────────────────────────────────────────────────────────────╮
   │ --hp         [default: 200]                                                  │
   │ --cylinders  [default: 6]                                                    │
   ╰──────────────────────────────────────────────────────────────────────────────╯
   ╭─ Wheels ─────────────────────────────────────────────────────────────────────╮
   │ --wheel-diameter  [default: 18]                                              │
   │ --rims,--no-rims  [default: False]                                           │
   ╰──────────────────────────────────────────────────────────────────────────────╯

   $ python my-script.py create --car --truck
   ╭─ Error ──────────────────────────────────────────────────────────────────────╮
   │ Mutually exclusive arguments: {--car, --truck}                               │
   ╰──────────────────────────────────────────────────────────────────────────────╯

The default groups are defined by the registering app:

* :attr:`.App.group_arguments` for positional-only arguments, which defaults to a group named ``"Arguments"``.

* :attr:`.App.group_parameters` for all other parameters, which defaults to a group named ``"Parameters"``.

----------
Converters
----------
Converters offer a way of having parameters within a group interact during processing.
See :attr:`.Group.converter` for details.

----------
Validators
----------
Group validators offer a way of jointly validating group parameter members of CLI-provided values.
See :attr:`.Group.validator` for details.

Cyclopts has some :ref:`builtin group-validators for common use-cases.<Group Validators>`
