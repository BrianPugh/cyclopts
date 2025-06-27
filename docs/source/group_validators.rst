.. _Group Validators:

================
Group Validators
================
Group validators operate on a set of parameters, :ref:`ensuring that their values are mutually compatible <Parameter Groups>`.
Validator(s) for a group can be set via the :attr:`.Group.validator` attribute. An individual validator is a callable object/function with signature:

.. code-block:: python

    def validator(argument_collection: ArgumentCollection):
        "Raise an exception if something is invalid."


Cyclopts has some builtin common group validators in the :ref:`cyclopts.validators <API Validators>` module.

.. _Group Validators - LimitedChoice:

-------------
LimitedChoice
-------------
Limits the number of specified arguments within the group.
Most commonly used for mutually-exclusive arguments (default behavior).


.. code-block:: python

   from cyclopts import App, Group, Parameter, validators
   from typing import Annotated

   app = App()

   vehicle = Group(
       "Vehicle (choose one)",
       default_parameter=Parameter(negative=""),  # Disable "--no-" flags
       validator=validators.LimitedChoice(),  # Mutually Exclusive Options
   )

   @app.default
   def main(
       *,
       car: Annotated[bool, Parameter(group=vehicle)] = False,
       truck: Annotated[bool, Parameter(group=vehicle)] = False,
   ):
       if car:
           print("I'm driving a car.")
       if truck:
           print("I'm driving a truck.")

   app()

.. code-block:: console

   $ python drive.py --help
   Usage: main COMMAND [OPTIONS]

   ╭─ Commands ─────────────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                          │
   │ --version  Display application version.                            │
   ╰────────────────────────────────────────────────────────────────────╯
   ╭─ Vehicle (choose one) ─────────────────────────────────────────────╮
   │ --car    [default: False]                                          │
   │ --truck  [default: False]                                          │
   ╰────────────────────────────────────────────────────────────────────╯

   $ python drive.py --car
   I'm driving a car.

   $ python drive.py --car --truck
   ╭─ Error ────────────────────────────────────────────────────────────╮
   │ Invalid values for group "Vehicle (choose one)". Mutually          │
   │ exclusive arguments: {--car, --truck}                              │
   ╰────────────────────────────────────────────────────────────────────╯

See the :class:`.LimitedChoice` docs for more info.

-----------------
MutuallyExclusive
-----------------
Alias for :class:`.LimitedChoice` with default arguments.
Exists primarily because the usage/implication will be more directly obvious and searchable to developers than :class:`.LimitedChoice`.
Since this class takes no arguments, an already instantiated version :obj:`.mutually_exclusive` is also provided for convenience.

-----------
all_or_none
-----------
Group validator that enforces that either **all** parameters in the group must be supplied an argument, or **none** of them.

.. code-block:: python

   from typing import Annotated

   from cyclopts import App, Group, Parameter
   from cyclopts.validators import all_or_none

   app = App()

   group_1 = Group(validator=all_or_none)
   group_2 = Group(validator=all_or_none)


   @app.default
   def default(
       foo: Annotated[bool, Parameter(group=group_1)] = False,
       bar: Annotated[bool, Parameter(group=group_1)] = False,
       fizz: Annotated[bool, Parameter(group=group_2)] = False,
       buzz: Annotated[bool, Parameter(group=group_2)] = False,
   ):
       print(f"{foo=} {bar=}")
       print(f"{fizz=} {buzz=}")


   if __name__ == "__main__":
       app()

.. code-block:: console

   $ python all_or_none.py
   foo=False bar=False
   fizz=False buzz=False

   $ python all_or_none.py --foo
   ╭─ Error ──────────────────────────────────────────────────────────╮
   │ Missing argument: --bar                                          │
   ╰──────────────────────────────────────────────────────────────────╯

   $ python all_or_none.py --foo --bar
   foo=True bar=True
   fizz=False buzz=False

   $ python all_or_none.py --foo --bar --fizz
   ╭─ Error ────────────────────────────────────────────────────────────╮
   │ Missing argument: --buzz                                           │
   ╰────────────────────────────────────────────────────────────────────╯

   $ python all_or_none.py --foo --bar --fizz --buzz
   foo=True bar=True
   fizz=True buzz=True


See the :obj:`.all_or_none` docs for more info.
