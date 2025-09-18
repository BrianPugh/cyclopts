.. _Help Customization:

==================
Help Customization
==================

Cyclopts provides extensive customization options for help screen appearance and formatting through the ``help_formatter`` parameter available on both :attr:`App <cyclopts.App.help_formatter>` and :attr:`Group <cyclopts.Group.help_formatter>`. These parameters accept formatters that follow the :class:`~cyclopts.help.protocols.HelpFormatter` protocol.

--------------------------
Setting Help Formatters
--------------------------

App-Level Formatting
^^^^^^^^^^^^^^^^^^^^

The :class:`~cyclopts.App` class accepts a ``help_formatter`` parameter that controls the default formatting for all help output:

.. code-block:: python

   from cyclopts import App
   from cyclopts.help import DefaultFormatter, PlainFormatter

   # Use a built-in formatter by name
   app = App(help_formatter="plain")

   # Or pass a formatter instance with custom configuration
   app = App(
       help_formatter=DefaultFormatter(
           # Custom configuration options
       )
   )

   # Or use a completely custom formatter
   app = App(help_formatter=MyCustomFormatter())

Group-Level Formatting
^^^^^^^^^^^^^^^^^^^^^^

Individual :class:`~cyclopts.Group` instances can have their own ``help_formatter`` that overrides the app-level default:

.. code-block:: python

   from cyclopts import App, Group
   from cyclopts.help import DefaultFormatter, PanelSpec
   from rich.box import DOUBLE

   # Create a group with custom formatting
   advanced_group = Group(
       "Advanced Options",
       help_formatter=DefaultFormatter(
           panel_spec=PanelSpec(
               border_style="red",
               box=DOUBLE,
           )
       )
   )

   # The app can have a different default formatter
   app = App(help_formatter="plain")

   # Parameters in advanced_group will use the group's formatter,
   # while other parameters use the app's formatter

This allows you to:

- Apply consistent formatting across your entire application via ``App.help_formatter``
- Override formatting for specific parameter groups via ``Group.help_formatter``
- Mix different formatting styles within a single application (e.g., highlighting critical options differently)

-------------------
Built-in Formatters
-------------------

Cyclopts includes two built-in formatters to cover common use cases:

DefaultFormatter
^^^^^^^^^^^^^^^^

The :class:`~cyclopts.help.DefaultFormatter` is the default help formatter that uses
`Rich <https://github.com/Textualize/rich>`_ for beautiful terminal output with colors,
borders, and structured layouts.

.. code-block:: python

   from cyclopts import App

   # Explicitly use the default formatter (same as not specifying)
   app = App(help_formatter="default")

   @app.default
   def main(name: str, count: int = 1):
       """A simple greeting application.

       Parameters
       ----------
       name : str
           Person to greet.
       count : int
           Number of times to greet.
       """
       for _ in range(count):
           print(f"Hello, {name}!")

   if __name__ == "__main__":
       app()

Output:

.. code-block:: text

   Usage: my-app [ARGS] [OPTIONS]

   A simple greeting application.

   ╭─ Parameters ──────────────────────────────────────────────────────────╮
   │ *  NAME --name    Person to greet. [required]                         │
   │    COUNT --count  Number of times to greet. [default: 1]              │
   ╰───────────────────────────────────────────────────────────────────────╯
   ╭─ Commands ────────────────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                             │
   │ --version  Display application version.                               │
   ╰───────────────────────────────────────────────────────────────────────╯

PlainFormatter
^^^^^^^^^^^^^^

The :class:`~cyclopts.help.PlainFormatter` provides accessibility-focused plain text output
without colors or special characters, ideal for screen readers and simpler terminals.

.. code-block:: python

   from cyclopts import App

   # Use plain text formatter for accessibility
   app = App(help_formatter="plain")

   @app.default
   def main(name: str, count: int = 1):
       """A simple greeting application.

       Parameters
       ----------
       name : str
           Person to greet.
       count : int
           Number of times to greet.
       """
       for _ in range(count):
           print(f"Hello, {name}!")

   if __name__ == "__main__":
       app()

Output:

.. code-block:: text

   Usage: demo.py [ARGS] [OPTIONS]

   A simple greeting application.

   Commands:
   --help, -h: Display this message and exit.
   --version: Display application version.

   Parameters:
   NAME, --name: Person to greet.
   COUNT, --count: Number of times to greet.

---------------------
Basic Customization
---------------------

The :class:`~cyclopts.help.DefaultFormatter` accepts several customization options
through its initialization parameters.

Panel Customization
^^^^^^^^^^^^^^^^^^^

The :class:`~cyclopts.help.PanelSpec` controls the outer panel appearance:

.. code-block:: python

   from cyclopts import App
   from cyclopts.help import DefaultFormatter, PanelSpec
   from rich.box import DOUBLE

   app = App(
       help_formatter=DefaultFormatter(
           panel_spec=PanelSpec(
               box=DOUBLE,              # Use double-line borders
               border_style="blue",     # Blue border color
               padding=(1, 2),         # (vertical, horizontal) padding
               expand=True,            # Expand to full terminal width
           )
       )
   )

   @app.default
   def main(path: str, verbose: bool = False):
       """Process a file with custom panel styling."""
       print(f"Processing {path}")

   if __name__ == "__main__":
       app()

Output:

.. code-block:: text

   Usage: demo.py [ARGS] [OPTIONS]

   Process a file with custom panel styling.

   ╔═ Commands ═══════════════════════════════════════════════════════════╗
   ║                                                                      ║
   ║  --help -h  Display this message and exit.                           ║
   ║  --version  Display application version.                             ║
   ║                                                                      ║
   ╚══════════════════════════════════════════════════════════════════════╝
   ╔═ Parameters ═════════════════════════════════════════════════════════╗
   ║                                                                      ║
   ║  *  PATH --path                     [required]                       ║
   ║     VERBOSE --verbose --no-verbose  [default: False]                 ║
   ║                                                                      ║
   ╚══════════════════════════════════════════════════════════════════════╝


Table Customization
^^^^^^^^^^^^^^^^^^^

The :class:`~cyclopts.help.TableSpec` controls the table styling within panels:

.. code-block:: python

   from cyclopts import App
   from cyclopts.help import DefaultFormatter, TableSpec

   app = App(
       help_formatter=DefaultFormatter(
           table_spec=TableSpec(
               show_header=True,        # Show column headers
               show_lines=True,         # Show lines between rows
               border_style="green",    # Green table elements
               padding=(0, 2, 0, 0),   # Extra right padding
           )
       )
   )

   @app.default
   def main(path: str, verbose: bool = False):
       """Process a file with custom table styling."""
       print(f"Processing {path}")

   if __name__ == "__main__":
       app()

Output:

.. code-block:: text

   Usage: my-app [ARGS] [OPTIONS]

   Process a file with custom table styling.

   ╭─ Parameters ──────────────────────────────────────────────────────────╮
   │ Required │ Option           │ Description                            │
   │ ─────────┼──────────────────┼─────────────────────────────────────── │
   │ *        │ PATH --path      │ [required]                             │
   │          │ VERBOSE --verbose│ [default: False]                       │
   ╰───────────────────────────────────────────────────────────────────────╯

Combining Customizations
^^^^^^^^^^^^^^^^^^^^^^^^

You can combine both panel and table specifications:

.. code-block:: python

   from cyclopts import App
   from cyclopts.help import DefaultFormatter, PanelSpec, TableSpec
   from rich.box import ROUNDED

   app = App(
       help_formatter=DefaultFormatter(
           panel_spec=PanelSpec(
               box=ROUNDED,
               border_style="cyan",
               padding=(0, 1),
           ),
           table_spec=TableSpec(
               show_header=False,
               show_lines=False,
               padding=(0, 1),
           )
       )
   )

   @app.default
   def main(path: str, verbose: bool = False):
       """Process a file with combined customizations."""
       print(f"Processing {path}")

   if __name__ == "__main__":
       app()

Output:

.. code-block:: text

   Usage: my-app [ARGS] [OPTIONS]

   Process a file with combined customizations.

   ╭──────────────────────────────────────────────────────────────────────╮
   │ *  PATH --path       [required]                                      │
   │    VERBOSE --verbose [default: False]                                │
   ╰──────────────────────────────────────────────────────────────────────╯
   ╭──────────────────────────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                            │
   │ --version  Display application version.                              │
   ╰──────────────────────────────────────────────────────────────────────╯

-----------------------
Group-Level Formatting
-----------------------

Different parameter groups can have different formatting styles, allowing you to
visually distinguish between different types of options:

.. code-block:: python

   from cyclopts import App, Group, Parameter
   from cyclopts.help import DefaultFormatter, PanelSpec
   from rich.box import DOUBLE, MINIMAL
   from typing import Annotated

   # Create groups with different styles
   required_group = Group(
       "Required Options",
       help_formatter=DefaultFormatter(
           panel_spec=PanelSpec(
               box=DOUBLE,
               border_style="red bold",
           )
       )
   )

   optional_group = Group(
       "Optional Settings",
       help_formatter=DefaultFormatter(
           panel_spec=PanelSpec(
               box=MINIMAL,
               border_style="green",
           )
       )
   )

   app = App()

   @app.default
   def main(
       # Required parameters with red double border
       input_file: Annotated[str, Parameter(group=required_group)],
       output_dir: Annotated[str, Parameter(group=required_group)],

       # Optional parameters with green minimal border
       verbose: Annotated[bool, Parameter(group=optional_group)] = False,
       threads: Annotated[int, Parameter(group=optional_group)] = 4,
   ):
       """Process files with styled help groups."""
       print(f"Processing {input_file} -> {output_dir}")
       if verbose:
           print(f"Using {threads} threads")

   if __name__ == "__main__":
       app()

Output:

.. code-block:: text

   Usage: my-app [ARGS] [OPTIONS]

   Process files with styled help groups.

   ╔═══════════════════════════════════════════════════════════════════════╗
   ║ *  INPUT-FILE --input-file  [required]                               ║
   ║ *  OUTPUT-DIR --output-dir  [required]                               ║
   ╚═══════════════════════════════════════════════════════════════════════╝
   ┌───────────────────────────────────────────────────────────────────────┐
   │ VERBOSE --verbose  [default: False]                                   │
   │ THREADS --threads  [default: 4]                                       │
   └───────────────────────────────────────────────────────────────────────┘
   ╭─ Commands ────────────────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                             │
   │ --version  Display application version.                               │
   ╰───────────────────────────────────────────────────────────────────────╯

---------------------
Custom Column Layout
---------------------

For complete control over the help table layout, you can define custom columns
using :class:`~cyclopts.help.ColumnSpec`:

.. code-block:: python

   from cyclopts import App, Group, Parameter
   from cyclopts.help import DefaultFormatter, ColumnSpec, TableSpec
   from typing import Annotated

   # Define custom column renderers
   def names_renderer(entry):
       """Combine parameter names and shorts."""
       names = " ".join(entry.names) if entry.names else ""
       shorts = " ".join(entry.shorts) if entry.shorts else ""
       return f"{names} {shorts}".strip()

   def type_renderer(entry):
       """Show the parameter type."""
       from cyclopts.annotations import get_hint_name
       return get_hint_name(entry.type) if entry.type else ""

   # Create custom columns
   custom_group = Group(
       "Custom Layout",
       help_formatter=DefaultFormatter(
           table_spec=TableSpec(show_header=True),
           column_specs=(
               ColumnSpec(
                   renderer=lambda e: "★" if e.required else " ",
                   header="",
                   width=2,
                   style="yellow bold",
               ),
               ColumnSpec(
                   renderer=names_renderer,
                   header="Option",
                   style="cyan",
                   max_width=30,
               ),
               ColumnSpec(
                   renderer=type_renderer,
                   header="Type",
                   style="magenta",
                   justify="center",
               ),
               ColumnSpec(
                   renderer="description",  # Use attribute name
                   header="Description",
                   overflow="fold",
               ),
           )
       )
   )

   app = App()

   @app.default
   def main(
       input_path: Annotated[str, Parameter(group=custom_group, help="Input file path")],
       output_path: Annotated[str, Parameter(group=custom_group, help="Output file path")],
       count: Annotated[int, Parameter(group=custom_group, help="Number of iterations")] = 1,
   ):
       """Demo custom column layout."""
       print(f"Processing {input_path} -> {output_path} ({count} times)")

   if __name__ == "__main__":
       app()

Output:

.. code-block:: text

   Usage: my-app [ARGS] [OPTIONS]

   Demo custom column layout.

   ╭─ Custom Layout ────────────────────────────────────────────────────────╮
   │    Option                     Type   Description                      │
   │ ★  INPUT-PATH --input-path    str    Input file path                 │
   │ ★  OUTPUT-PATH --output-path  str    Output file path                │
   │    COUNT --count              int    Number of iterations            │
   ╰────────────────────────────────────────────────────────────────────────╯
   ╭─ Commands ─────────────────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                             │
   │ --version  Display application version.                               │
   ╰────────────────────────────────────────────────────────────────────────╯

Dynamic Column Builders
^^^^^^^^^^^^^^^^^^^^^^^

For even more flexibility, you can create columns dynamically based on runtime
conditions:

.. code-block:: python

   from cyclopts import App, Parameter
   from cyclopts.help import DefaultFormatter, ColumnSpec
   from typing import Annotated

   def dynamic_columns(console, options, entries):
       """Build columns based on console width and entries."""
       columns = []

       # Only show required indicator if there are required params
       if any(e.required for e in entries):
           columns.append(ColumnSpec(
               renderer=lambda e: "*" if e.required else "",
               width=2,
               style="red",
           ))

       # Adjust name column width based on console size
       max_width = min(40, int(console.width * 0.3))
       columns.append(ColumnSpec(
           renderer=lambda e: " ".join(e.names + e.shorts),
           header="Option",
           max_width=max_width,
           style="cyan",
       ))

       # Always include description
       columns.append(ColumnSpec(
           renderer="description",
           header="Description",
           overflow="fold",
       ))

       return tuple(columns)

   app = App(
       help_formatter=DefaultFormatter(
           column_specs=dynamic_columns
       )
   )

   @app.default
   def main(
       input_file: str,
       output_file: str,
       verbose: bool = False,
   ):
       """Process files with dynamic columns."""
       print(f"Processing {input_file} -> {output_file}")

   if __name__ == "__main__":
       app()

Output (adjusts based on terminal width):

.. code-block:: text

   Usage: my-app [ARGS] [OPTIONS]

   Process files with dynamic columns.

   ╭─ Parameters ───────────────────────────────────────────────────────────╮
   │ Option                          Description                           │
   │ * INPUT-FILE --input-file       [required]                            │
   │ * OUTPUT-FILE --output-file     [required]                            │
   │   VERBOSE --verbose             [default: False]                      │
   ╰────────────────────────────────────────────────────────────────────────╯

--------------------------
Creating Custom Formatters
--------------------------

For complete control, you can implement your own formatter by following the
:class:`~cyclopts.help.protocols.HelpFormatter` protocol. The formatter methods
receive the console and options first, followed by the content to render:

.. code-block:: python

   from cyclopts import App
   from cyclopts.help import HelpPanel
   from rich.console import Console, ConsoleOptions
   from rich.table import Table
   from rich.panel import Panel

   class MyCustomFormatter:
       """A custom formatter with unique styling."""

       def __call__(self, console: Console, options: ConsoleOptions, panel: HelpPanel) -> None:
           """Render a help panel with custom styling."""
           if not panel.entries:
               return

           # Create a custom table
           table = Table(show_header=True, header_style="bold magenta")
           table.add_column("Option", style="cyan", no_wrap=True)
           table.add_column("Description", style="white")

           for entry in panel.entries:
               name = " ".join(entry.names + entry.shorts)
               # Extract plain text from description (handles InlineText, etc)
               desc = ""
               if entry.description:
                   if hasattr(entry.description, 'plain'):
                       desc = entry.description.plain
                   elif hasattr(entry.description, '__rich_console__'):
                       # Render to plain text without styles
                       with console.capture() as capture:
                           console.print(entry.description, end="")
                       desc = capture.get()
                   else:
                       desc = str(entry.description)
               table.add_row(name, desc)

           # Wrap in a custom panel
           panel_title = panel.title or "Options"
           styled_panel = Panel(
               table,
               title=f"[bold blue]{panel_title}[/bold blue]",
               border_style="blue",
           )

           console.print(styled_panel)

       def render_usage(self, console: Console, options: ConsoleOptions, usage) -> None:
           """Render the usage line."""
           if usage:
               console.print(f"[bold green]Usage:[/bold green] {usage}")

       def render_description(self, console: Console, options: ConsoleOptions, description) -> None:
           """Render the description."""
           if description:
               console.print(f"\n[italic]{description}[/italic]\n")

   # Use the custom formatter
   app = App(help_formatter=MyCustomFormatter())

   @app.default
   def main(input_file: str, output_file: str, verbose: bool = False):
       """Process files with custom formatter."""
       print(f"Processing {input_file} -> {output_file}")

   if __name__ == "__main__":
       app()

Output:

.. code-block:: text

   Usage: my-app [ARGS] [OPTIONS]

   Process files with custom formatter.

   ╭─ Parameters ──────────────────────────────────────────────────────────╮
   │ Option                       Description                              │
   │ INPUT-FILE --input-file      [required]                               │
   │ OUTPUT-FILE --output-file    [required]                               │
   │ VERBOSE --verbose            [default: False]                         │
   ╰────────────────────────────────────────────────────────────────────────╯
   ╭─ Commands ─────────────────────────────────────────────────────────────╮
   │ Option             Description                                        │
   │ --help -h          Display this message and exit.                     │
   │ --version          Display application version.                       │
   ╰────────────────────────────────────────────────────────────────────────╯

---------------------------
Complete Example
---------------------------

Here's a complete example demonstrating various customization techniques:

.. code-block:: python

   #!/usr/bin/env python
   """CLI with extensively customized help formatting."""

   from pathlib import Path
   from typing import Annotated

   from rich.box import DOUBLE, MINIMAL_HEAVY_HEAD, ROUNDED

   from cyclopts import App, Group, Parameter
   from cyclopts.help import (
       ColumnSpec,
       DefaultFormatter,
       PanelSpec,
       TableSpec,
   )

   # Define different styles for different parameter groups
   critical_group = Group(
       "🔴 Critical Settings",
       help="These options significantly affect operation",
       help_formatter=DefaultFormatter(
           panel_spec=PanelSpec(
               box=DOUBLE,
               border_style="red bold",
               padding=(0, 2),
           ),
           table_spec=TableSpec(
               show_header=True,
               border_style="red",
           ),
           column_specs=(
               ColumnSpec(
                   renderer=lambda e: "⚠" if e.required else " ",
                   width=2,
                   style="red bold",
               ),
               ColumnSpec(
                   renderer=lambda e: " ".join(e.names + e.shorts),
                   header="Option",
                   style="yellow bold",
               ),
               ColumnSpec(
                   renderer="description",
                   header="Impact",
                   style="white",
               ),
           ),
       ),
   )

   performance_group = Group(
       "⚡ Performance Tuning",
       help_formatter=DefaultFormatter(
           panel_spec=PanelSpec(
               box=MINIMAL_HEAVY_HEAD,
               border_style="cyan",
           ),
           table_spec=TableSpec(
               show_lines=True,
               padding=(0, 1),
           ),
       ),
   )

   # Create the application
   app = App(
       name="styled-cli",
       help="A beautifully formatted CLI application",
       # Set a default formatter for ungrouped parameters
       help_formatter=DefaultFormatter(
           panel_spec=PanelSpec(
               box=ROUNDED,
               border_style="green",
           ),
       ),
   )

   @app.default
   def main(
       # Critical parameters
       config: Annotated[
           Path,
           Parameter(
               group=critical_group,
               help="Configuration file (changes entire behavior)",
           ),
       ],

       # Performance parameters
       workers: Annotated[
           int,
           Parameter(
               group=performance_group,
               help="Number of parallel workers",
           ),
       ] = 4,
       cache_size: Annotated[
           int,
           Parameter(
               group=performance_group,
               help="Cache size in MB",
           ),
       ] = 100,

       # Regular parameters (use default formatting)
       verbose: Annotated[
           bool,
           Parameter(help="Enable verbose output"),
       ] = False,
   ):
       """Process data with style.

       This application demonstrates how different parameter
       groups can have completely different visual styles
       in the help output.
       """
       print(f"Loading config from {config}")
       print(f"Using {workers} workers with {cache_size}MB cache")

   if __name__ == "__main__":
       app()

Output:

.. code-block:: text

   Usage: styled-cli [ARGS] [OPTIONS]

   A beautifully formatted CLI application

   Process data with style.

   This application demonstrates how different parameter
   groups can have completely different visual styles
   in the help output.

   ╔═══════════════════════════════════════════════════════════════════════╗
   ║                                                                       ║
   ║     Option                Impact                                      ║
   ║  ⚠  CONFIG --config       Configuration file (changes entire         ║
   ║                           behavior)                                  ║
   ║                                                                       ║
   ╚═══════════════════════════════════════════════════════════════════════╝
   ┏━ ⚡ Performance Tuning ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   ┃                                                                       ┃
   ┃  WORKERS --workers      Number of parallel workers [default: 4]      ┃
   ┃ ───────────────────────────────────────────────────────────────────  ┃
   ┃  CACHE-SIZE --cache-size Cache size in MB [default: 100]             ┃
   ┃                                                                       ┃
   ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
   ╭─ Parameters ──────────────────────────────────────────────────────────╮
   │ VERBOSE --verbose  Enable verbose output [default: False]             │
   ╰───────────────────────────────────────────────────────────────────────╯
   ╭─ Commands ────────────────────────────────────────────────────────────╮
   │ --help -h  Display this message and exit.                             │
   │ --version  Display application version.                               │
   ╰───────────────────────────────────────────────────────────────────────╯

---------
Reference
---------

For complete API documentation of help formatting components, see:

* :class:`cyclopts.help.DefaultFormatter` - Rich-based formatter with full customization
* :class:`cyclopts.help.PlainFormatter` - Plain text formatter for accessibility
* :class:`cyclopts.help.PanelSpec` - Panel appearance specification
* :class:`cyclopts.help.TableSpec` - Table styling specification
* :class:`cyclopts.help.ColumnSpec` - Column definition and rendering
* :class:`cyclopts.help.protocols.HelpFormatter` - Protocol for custom formatters

See also:

* :ref:`Help` - General help system documentation
* :ref:`Groups` - Organizing parameters into groups
