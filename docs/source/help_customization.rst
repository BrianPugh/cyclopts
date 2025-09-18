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

   # Use a built-in formatter by name: {"default", "plain"}
   app = App(help_formatter="plain")

   # Or pass a formatter instance with custom configuration
   app = App(
       help_formatter=DefaultFormatter(
           # Custom configuration options
       )
   )

   # Or use a completely custom formatter; see HelpFormatter protocol.
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

-------------------
Built-in Formatters
-------------------

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

.. raw:: html

   <div class="highlight-default notranslate">
         <pre style="font-family: monospace;"><span style="font-weight: bold">Usage: my-app [ARGS] [OPTIONS]</span>

   A simple greeting application.

   ╭─ Commands ───────────────────────────────────────────────────────────────────╮
   │ <span style="color: #0088cc">--help -h</span>  Display this message and exit.                                    │
   │ <span style="color: #0088cc">--version</span>  Display application version.                                      │
   ╰──────────────────────────────────────────────────────────────────────────────╯
   ╭─ Parameters ─────────────────────────────────────────────────────────────────╮
   │ <span style="color: #cc3333; font-weight: bold">*</span>  <span style="color: #0088cc">NAME --name</span>    Person to greet. <span style="color: #cc3333; opacity: 0.7">[required]</span>                                │
   │    <span style="color: #0088cc">COUNT --count</span>  Number of times to greet. <span style="opacity: 0.7">[default: 1]</span>                     │
   ╰──────────────────────────────────────────────────────────────────────────────╯</pre>
   </div>

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

.. raw:: html

   <div class="highlight-default notranslate">
         <pre style="font-family: monospace;"><span style="font-weight: bold">Usage: demo.py [ARGS] [OPTIONS]</span>

   Process a file with custom panel styling.

   <span style="color: #0088cc">╔═ Commands ═══════════════════════════════════════════════════════════╗</span>
   <span style="color: #0088cc">║                                                                      ║</span>
   <span style="color: #0088cc">║  </span><span style="color: #0088cc">--help -h  </span>Display this message and exit.                           <span style="color: #0088cc">║</span>
   <span style="color: #0088cc">║  </span><span style="color: #0088cc">--version  </span>Display application version.                             <span style="color: #0088cc">║</span>
   <span style="color: #0088cc">║                                                                      ║</span>
   <span style="color: #0088cc">╚══════════════════════════════════════════════════════════════════════╝</span>
   <span style="color: #0088cc">╔═ Parameters ═════════════════════════════════════════════════════════╗</span>
   <span style="color: #0088cc">║                                                                      ║</span>
   <span style="color: #0088cc">║  </span><span style="color: #cc3333; font-weight: bold">*  </span><span style="color: #0088cc">PATH --path                   </span>  <span style="color: #cc3333; opacity: 0.7">[required]</span>                       <span style="color: #0088cc">║</span>
   <span style="color: #0088cc">║     </span><span style="color: #0088cc">VERBOSE --verbose</span>  <span style="opacity: 0.7">[default: False]</span>                              <span style="color: #0088cc">║</span>
   <span style="color: #0088cc">║       </span><span style="color: #0088cc">--no-verbose   </span>                                                <span style="color: #0088cc">║</span>
   <span style="color: #0088cc">║                                                                      ║</span>
   <span style="color: #0088cc">╚══════════════════════════════════════════════════════════════════════╝</span></pre>
   </div>


Table Customization
^^^^^^^^^^^^^^^^^^^

The :class:`~cyclopts.help.TableSpec` controls the table styling within panels:

.. code-block:: python

   from cyclopts import App
   from cyclopts.help import DefaultFormatter, TableSpec

   app = App(
       help_formatter=DefaultFormatter(
           table_spec=TableSpec(
               show_header=True,  # Show column headers
               show_lines=True,  # Show lines between rows
               show_edge=False,  # Remove outer table border
               border_style="green",  # Green table elements
               padding=(0, 2, 0, 0),  # Extra right padding
               box=SQUARE,  # otherwise we won't see the lines
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

.. raw:: html

   <div class="highlight-default notranslate">
         <pre style="font-family: monospace;"><span style="font-weight: bold">Usage: test_table_custom.py [ARGS] [OPTIONS]</span>

   Process a file with custom table styling.

   ╭─ Commands ───────────────────────────────────────────────────────────────────╮
   │ Command    <span style="color: #00aa00">│</span>Description                                                      │
   │ <span style="color: #00aa00">───────────┼────────────────────────────────────────────────────────────────</span> │
   │ <span style="color: #0088cc">--help -h</span>  <span style="color: #00aa00">│</span>Display this message and exit.                                   │
   │ <span style="color: #00aa00">───────────┼────────────────────────────────────────────────────────────────</span> │
   │ <span style="color: #0088cc">--version</span>  <span style="color: #00aa00">│</span>Display application version.                                     │
   ╰──────────────────────────────────────────────────────────────────────────────╯
   ╭─ Parameters ─────────────────────────────────────────────────────────────────╮
   │    <span style="color: #00aa00">│</span>Option             <span style="color: #00aa00">│</span>Description                                          │
   │ <span style="color: #00aa00">───┼───────────────────┼────────────────────────────────────────────────────</span> │
   │ <span style="color: #cc3333; font-weight: bold">*</span>  <span style="color: #00aa00">│</span><span style="color: #0088cc">PATH --path</span>        <span style="color: #00aa00">│</span><span style="color: #cc3333; opacity: 0.7">[required]</span>                                           │
   │ <span style="color: #00aa00">───┼───────────────────┼────────────────────────────────────────────────────</span> │
   │    <span style="color: #00aa00">│</span><span style="color: #0088cc">VERBOSE --verbose</span>  <span style="color: #00aa00">│</span><span style="opacity: 0.7">[default: False]</span>                                     │
   │    <span style="color: #00aa00">│</span><span style="color: #0088cc">  --no-verbose</span>     <span style="color: #00aa00">│</span>                                                     │
   ╰──────────────────────────────────────────────────────────────────────────────╯</pre>
   </div>

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

.. raw:: html

   <div class="highlight-default notranslate">
         <pre style="font-family: monospace;"><span style="font-weight: bold">Usage: my-app [ARGS] [OPTIONS]</span>

   Process a file with combined customizations.

   <span style="color: #00aaaa">╭─ Commands ──────────────────────────────────────────────────────────╮</span>
   <span style="color: #00aaaa">│ </span><span style="color: #0088cc">--help -h</span>  Display this message and exit.                           <span style="color: #00aaaa">│</span>
   <span style="color: #00aaaa">│ </span><span style="color: #0088cc">--version</span>  Display application version.                             <span style="color: #00aaaa">│</span>
   <span style="color: #00aaaa">╰─────────────────────────────────────────────────────────────────────╯</span>
   <span style="color: #00aaaa">╭─ Parameters ────────────────────────────────────────────────────────╮</span>
   <span style="color: #00aaaa">│ </span><span style="color: #cc3333; font-weight: bold">*</span>  <span style="color: #0088cc">PATH --path</span>       <span style="color: #cc3333; opacity: 0.7">[required]</span>                                     <span style="color: #00aaaa">│</span>
   <span style="color: #00aaaa">│    </span><span style="color: #0088cc">VERBOSE --verbose</span> <span style="opacity: 0.7">[default: False]</span>                               <span style="color: #00aaaa">│</span>
   <span style="color: #00aaaa">╰─────────────────────────────────────────────────────────────────────╯</span></pre>
   </div>

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

.. raw:: html

   <div class="highlight-default notranslate">
         <pre style="font-family: monospace;"><span style="font-weight: bold">Usage: test_group_formatting.py [ARGS] [OPTIONS]</span>

   Process files with styled help groups.

   ╭─ Commands ───────────────────────────────────────────────────────────────────╮
   │ <span style="color: #0088cc">--help -h</span>  Display this message and exit.                                    │
   │ <span style="color: #0088cc">--version</span>  Display application version.                                      │
   ╰──────────────────────────────────────────────────────────────────────────────╯
   <span style="color: #00aa00">   Optional Settings                                                            </span>
   <span style="color: #00aa00"> </span> <span style="color: #0088cc">VERBOSE --verbose</span>  <span style="opacity: 0.7">[default: False]</span>                                          <span style="color: #00aa00"> </span>
   <span style="color: #00aa00"> </span> <span style="color: #0088cc">  --no-verbose</span>     <span style="opacity: 0.7"></span>                                                          <span style="color: #00aa00"> </span>
   <span style="color: #00aa00"> </span> <span style="color: #0088cc">THREADS --threads</span>  <span style="opacity: 0.7">[default: 4]</span>                                              <span style="color: #00aa00"> </span>
   <span style="color: #00aa00">                                                                                </span>
   <span style="color: #cc3333; font-weight: bold">╔═ Required Options ═══════════════════════════════════════════════════════════╗</span>
   <span style="color: #cc3333; font-weight: bold">║</span> <span style="color: #cc3333; font-weight: bold">*</span>  <span style="color: #0088cc">INPUT-FILE --input-file</span>  <span style="color: #cc3333; opacity: 0.7">[required]</span>                                       <span style="color: #cc3333; font-weight: bold">║</span>
   <span style="color: #cc3333; font-weight: bold">║</span> <span style="color: #cc3333; font-weight: bold">*</span>  <span style="color: #0088cc">OUTPUT-DIR --output-dir</span>  <span style="color: #cc3333; opacity: 0.7">[required]</span>                                       <span style="color: #cc3333; font-weight: bold">║</span>
   <span style="color: #cc3333; font-weight: bold">╚══════════════════════════════════════════════════════════════════════════════╝</span></pre>
   </div>

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

.. raw:: html

   <div class="highlight-default notranslate">
         <pre style="font-family: monospace;"><span style="font-weight: bold">Usage: test_custom_column.py [ARGS] [OPTIONS]</span>

   Demo custom column layout.

   ╭─ Commands ───────────────────────────────────────────────────────────────────╮
   │ <span style="color: #0088cc">--help -h</span>  Display this message and exit.                                    │
   │ <span style="color: #0088cc">--version</span>  Display application version.                                      │
   ╰──────────────────────────────────────────────────────────────────────────────╯
   ╭─ Custom Layout ──────────────────────────────────────────────────────────────╮
   │     Option                     Type  Description                             │
   │ <span style="color: #ffaa00; font-weight: bold">★</span>   <span style="color: #0088cc">INPUT-PATH --input-path</span>    <span style="color: #aa00aa">str</span>   Input file path                         │
   │ <span style="color: #ffaa00; font-weight: bold">★</span>   <span style="color: #0088cc">OUTPUT-PATH --output-path</span>  <span style="color: #aa00aa">str</span>   Output file path                        │
   │     <span style="color: #0088cc">COUNT --count</span>              <span style="color: #aa00aa">int</span>   Number of iterations                    │
   ╰──────────────────────────────────────────────────────────────────────────────╯</pre>
   </div>

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

.. raw:: html

   <div class="highlight-default notranslate">
         <pre style="font-family: monospace;"><span style="font-weight: bold">Usage: test_dynamic_columns.py [ARGS] [OPTIONS]</span>

   Process files with dynamic columns.

   ╭─ Commands ───────────────────────────────────────────────────────────────────╮
   │ Option     Description                                                       │
   │ <span style="color: #0088cc">--help -h</span>  Display this message and exit.                                    │
   │ <span style="color: #0088cc">--version</span>  Display application version.                                      │
   ╰──────────────────────────────────────────────────────────────────────────────╯
   ╭─ Parameters ─────────────────────────────────────────────────────────────────╮
   │     Option                    Description                                    │
   │ <span style="color: #cc3333">*</span>   <span style="color: #0088cc">INPUT-FILE --input-file</span>                                                  │
   │ <span style="color: #cc3333">*</span>   <span style="color: #0088cc">OUTPUT-FILE</span>                                                              │
   │     <span style="color: #0088cc">--output-file</span>                                                            │
   │     <span style="color: #0088cc">VERBOSE --verbose</span>                                                        │
   │     <span style="color: #0088cc">--no-verbose</span>                                                             │
   ╰──────────────────────────────────────────────────────────────────────────────╯</pre>
   </div>

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

.. raw:: html

   <div class="highlight-default notranslate">
         <pre style="font-family: monospace;"><span style="color: #00aa00; font-weight: bold">Usage:</span> test_custom_formatter.py [ARGS] [OPTIONS]

   <span style="font-style: italic">Process files with custom formatter.</span>

   <span style="color: #0088cc">╭─ </span><span style="color: #0088cc; font-weight: bold">Commands</span><span style="color: #0088cc"> ───────────────────────────────────────────────────────────────────╮</span>
   <span style="color: #0088cc">│</span> ┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓                               <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">│</span> ┃<span style="color: #aa00aa; font-weight: bold"> Option    </span>┃<span style="color: #aa00aa; font-weight: bold"> Description                    </span>┃                               <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">│</span> ┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩                               <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">│</span> │<span style="color: #00aaaa"> --help -h </span>│ Display this message and exit. │                               <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">│</span> │<span style="color: #00aaaa"> --version </span>│ Display application version.   │                               <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">│</span> └───────────┴────────────────────────────────┘                               <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">╰──────────────────────────────────────────────────────────────────────────────╯</span>
   <span style="color: #0088cc">╭─ </span><span style="color: #0088cc; font-weight: bold">Parameters</span><span style="color: #0088cc"> ─────────────────────────────────────────────────────────────────╮</span>
   <span style="color: #0088cc">│</span> ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓                             <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">│</span> ┃<span style="color: #aa00aa; font-weight: bold"> Option                         </span>┃<span style="color: #aa00aa; font-weight: bold"> Description </span>┃                             <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">│</span> ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩                             <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">│</span> │<span style="color: #00aaaa"> INPUT-FILE --input-file        </span>│             │                             <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">│</span> │<span style="color: #00aaaa"> OUTPUT-FILE --output-file      </span>│             │                             <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">│</span> │<span style="color: #00aaaa"> VERBOSE --verbose --no-verbose </span>│             │                             <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">│</span> └────────────────────────────────┴─────────────┘                             <span style="color: #0088cc">│</span>
   <span style="color: #0088cc">╰──────────────────────────────────────────────────────────────────────────────╯</span></pre>
   </div>

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
