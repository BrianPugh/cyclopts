======
Groups
======
Groups offer a way of organizing parameters and commands on the help-page; for example:

.. code-block:: console

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

They also provide an additional abstraction layer that :ref:`validators <API Validators>` can operate on.

Groups can be created in two ways:

1. Explicitly creating a :class:`.Group` object.

2. Implicitly with a **string**.
   This will implicitly create a group, ``Group(my_str_group_name)``, if it doesn't exist.
   If there exists a :class:`.Group` object with the same name within the command/parameter context, it will join that group.

Every command and parameter belongs to at least one group.

Group(s) can be provided to the ``group`` keyword argument of :meth:`app.command <cyclopts.App.command>` and :class:`.Parameter`.
The :class:`.Group` class itself only marks objects with metadata and does not directly reference it's members.
This means that groups can be re-used across commands.

--------------
Command Groups
--------------
An example of using groups to organize commands:

.. code-block:: python

   from cyclopts import App

   app = App()

   # Change the group of "--help" and "--version" to the implicitly created "Admin" group.
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

The default group is defined by the registering app's :attr:`.App.group_commands`, which defaults to a group named ``"Commands"``.

----------------
Parameter Groups
----------------
Like commands above, parameter groups allow us to organize parameters on the help page.
They also allow us to add additional inter-parameter validators (e.g. mutually-exclusive parameters).
An example of using groups with parameters:

.. code-block:: python

   from cyclopts import App, Group, Parameter, validators
   from typing import Annotated

   app = App()

   vehicle_type_group = Group(
       "Vehicle (choose one)",
       default_parameter=Parameter(negative=""),  # Disable "--no-" flags
       validator=validators.MutuallyExclusive(),  # Only one option is allowed to be selected.
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

   ╭─ Engine ──────────────────────────────────────────────────────╮
   │ --hp         [default: 200]                                   │
   │ --cylinders  [default: 6]                                     │
   ╰───────────────────────────────────────────────────────────────╯
   ╭─ Vehicle (choose one) ────────────────────────────────────────╮
   │ --car    [default: False]                                     │
   │ --truck  [default: False]                                     │
   ╰───────────────────────────────────────────────────────────────╯
   ╭─ Wheels ──────────────────────────────────────────────────────╮
   │ --wheel-diameter  [default: 18]                               │
   │ --rims --no-rims  [default: False]                            │
   ╰───────────────────────────────────────────────────────────────╯

   $ python my-script.py create --car --truck
   ╭─ Error ───────────────────────────────────────────────────────╮
   │ Invalid values for group "Vehicle (choose one)". Mutually     │
   │ exclusive arguments: {--car, --truck}                         │
   ╰───────────────────────────────────────────────────────────────╯

In this example, we use the :class:`~.validators.MutuallyExclusive` validator to make it so the user can only specify ``--car`` or ``--truck``.

The default groups are defined by the registering app:

* :attr:`.App.group_arguments` for positional-only arguments, which defaults to a group named ``"Arguments"``.

* :attr:`.App.group_parameters` for all other parameters, which defaults to a group named ``"Parameters"``.

----------
Validators
----------
Group validators offer a way of jointly validating group parameter members of CLI-provided values.
Groups with an empty name, or with ``show=False``, are a way of using group validators without impacting the help-page.

.. code-block:: python

   from cyclopts import App, Group, validators

   app = App()
   mutually_exclusive = Group(
      validator=validatorsMutuallyExclusive(),
      default_parameter=Parameter(show_default=False, negative=""),
   )

   @app.command
   def foo(
       car: Annotated[bool, Parameter(group=(app.group_parameters, mutually_exclusive))],
       truck: Annotated[bool, Parameter(group=(app.group_parameters, mutually_exclusive))],
   ):
       pass

   app()

.. code-block:: console

   $ python demo.py foo --help
   Usage: demo.py foo [ARGS] [OPTIONS]

   ╭─ Parameters ──────────────────────────────────────────────────────╮
   │ CAR,--car                                                         │
   │ TRUCK,--truck                                                     │
   ╰───────────────────────────────────────────────────────────────────╯

See :attr:`.Group.validator` for details.

Cyclopts has some :ref:`builtin group-validators for common use-cases.<Group Validators>`

---------
Help Page
---------
Groups form titled panels on the help-page.

Groups with an empty name, or with :attr:`show=False <.Group.show>`, are **not** shown on the help-page.
This is useful for applying additional grouping logic (such as applying a :class:`.LimitedChoice` validator) without impacting the help-page.

By default, the ordering of panels is alphabetical.
However, the sorting can be manipulated by :attr:`.Group.sort_key`. See it's documentation for usage.

The :meth:`.Group.create_ordered` convenience classmethod creates a :class:`.Group` with a :attr:`~.Group.sort_key` value drawn drawn from a global monotonically increasing counter.
This means that the order in the help-page will match the order that the groups were instantiated.

.. code-block:: python

   from cyclopts import App, Group

   app = App()

   g_plants = Group.create_ordered("Plants")
   g_animals = Group.create_ordered("Animals")
   g_mushrooms = Group.create_ordered("Mushrooms")


   @app.command(group=g_animals)
   def zebra():
       pass


   @app.command(group=g_plants)
   def daisy():
       pass


   @app.command(group=g_mushrooms)
   def portobello():
       pass


   app()

.. code-block:: bash

   ╭─ Plants ───────────────────────────────────────────────────────────╮
   │ daisy                                                              │
   ╰────────────────────────────────────────────────────────────────────╯
   ╭─ Animals ──────────────────────────────────────────────────────────╮
   │ zebra                                                              │
   ╰────────────────────────────────────────────────────────────────────╯
   ╭─ Mushrooms ────────────────────────────────────────────────────────╮
   │ portobello                                                         │
   ╰────────────────────────────────────────────────────────────────────╯
   ╭─ Commands ─────────────────────────────────────────────────────────╮
   │ --help,-h  Display this message and exit.                          │
   │ --version  Display application version.                            │
   ╰────────────────────────────────────────────────────────────────────╯

A :attr:`~.Group.sort_key` can still be supplied; the global counter will only be used to break sorting ties.
