================
Group Validators
================

-------------
LimitedChoice
-------------


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

   ╭─ Vehicle (choose one) ────────────────────────────────────────────────╮
   │ --car    [default: False]                                             │
   │ --truck  [default: False]                                             │
   ╰───────────────────────────────────────────────────────────────────────╯
   ╭─ Commands ────────────────────────────────────────────────────────────╮
   │ --help,-h  Display this message and exit.                             │
   │ --version  Display application version.                               │
   ╰───────────────────────────────────────────────────────────────────────╯

   $ python drive.py --car
   I'm driving a car.

   $ python drive.py --car --truck
   ╭─ Error ───────────────────────────────────────────────────────────────╮
   │ Mutually exclusive arguments: {--car, --truck}                        │
   ╰───────────────────────────────────────────────────────────────────────╯
