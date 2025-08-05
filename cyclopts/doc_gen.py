"""Automatic Markdown documentation generator for Cyclopts CLI applications.

This module defines utilities to extract the structure of a Cyclopts
application and render it to Markdown. Most the inspiration from this
is Typer's built in doc gen....
1. Traverse the `cyclopts.App` instance
2. Inspects each registered command
3. Gen a file that documents usage, arguments, options and nested commands.

Can either call :func:`generate_docs` directly to get back a Markdown
string, or you can call :func:`init_docs` to register a ``docs``
command to the app.

Example
-------

>>> from cyclopts import App
>>> from cyclopts_docs import init_docs
>>> app = App(help="Awesome CLI user manager.")
>>>
>>> @app.command
... def create(username: str):
...    '''
...     Create a new user with USERNAME.
...    '''
...     ...
>>>
>>> init_docs(app)
>>> # Running ``python your_script.py docs`` will print Markdown docs

Limitations
-----------

This is a _starter_ for the doc gen. More complex / custom things may
not be documented very well. Specifically, `inspect` is used to
determine positionals args from options. The same usage may not be able
to determine Parameter Groups or custom converters used for params. Currently
it does not show Enum Types as nicely as the help flag shows either.
"""
from __future__ import annotations
import inspect
from typing import Any, Callable, Iterable
from cyclopts import App  # type: ignore
from pathlib import Path

class _ParamInfo:
    """Structured description of a command parameter.

    Holds the name, annotaiton, default value, and wether or not the param
    is an option or argument.
    """

    def __init__(self, name: str, annotation: Any, default: Any) -> None:
        self.name = name
        self.annotation = annotation
        self.default = default

        # A default value means the parameter is an option
        self.is_option = default is not inspect._empty

    @property
    def type_name(self) -> str:
        """Return a name for the parameter's type."""
        if self.annotation is inspect._empty:
            return ""
        try:
            return self.annotation.__name__
        except AttributeError:
            return str(self.annotation)


def _extract_params(func: Callable[..., Any]) -> list[_ParamInfo]:
    """Inspect a function signature and return a list of parameter info.

    Parameters
    ----------
    func:
        The command callback whose parameters should be documented.

    Returns
    -------
    list of _ParamInfo
        Description of each parameter (excluding *args and **kwargs).
    """
    signature = inspect.signature(func)
    params: list[_ParamInfo] = []
    for param in signature.parameters.values():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            # Skiping varargs;
            continue
        params.append(_ParamInfo(param.name, param.annotation, param.default))
    return params


def _format_usage(prog: str, command_path: list[str], params: Iterable[_ParamInfo]) -> str:
    """Create a usage string for a command.

    The usage follows the pattern: 

        $ prog [OPTIONS] COMMAND [ARGS]...

    Parameters
    ----------
    prog:
        Base program name.
    command_path:
        list of command tokens (e.g. ["delete", "user"]).
    params:
        The parameter metadata.

    Returns
    -------
    str
        A usage string suitable for Markdown.
    """
    tokens = [prog] + command_path
    usage_parts: list[str] = []

    # First; Get the options if there are any and show them
    if any(p.is_option for p in params):
        usage_parts.append("[OPTIONS]")

    # Second; Get the position args
    for p in params:
        if not p.is_option:
            usage_parts.append(p.name.upper())
    if not command_path and not any(p.is_option for p in params) and params:
        # If root has only positional args, emphasise they come after command
        pass  
    return "``$ {} {}``".format(" ".join(tokens), " ".join(usage_parts)).rstrip()


def _format_options(params: Iterable[_ParamInfo]) -> list[str]:
    """Format option parameters into Markdown lines.

    Parameters with default values become options.  Booleans with a
    default of True/False are rendered as dual flags (``--name / --no-name``).

    Returns
    -------
    list of str
        Each element is a line documenting an option.
    """
    lines: list[str] = []
    for p in params:
        if not p.is_option:
            continue
        opt_name = p.name.replace("_", "-")

        # Handle the booleans 
        if isinstance(p.annotation, bool) or isinstance(p.default, bool):
            # Show negative form for boolean options
            lines.append(f"* ``--{opt_name} / --no-{opt_name}``: Boolean option.")
        else:
            default_repr = "" if p.default is inspect._empty else f" [default: {p.default}]"
            type_repr = f" ({p.type_name})" if p.type_name else ""
            lines.append(f"* ``--{opt_name}``: {p.type_name if p.type_name else 'Option'}{default_repr}")
    return lines


def _format_arguments(params: Iterable[_ParamInfo]) -> list[str]:
    """Format positional arguments into Markdown lines.

    Returns
    -------
    list of str
        Each element is a line documenting an argument.
    """
    lines: list[str] = []
    for p in params:
        if p.is_option:
            continue
        type_repr = f" ({p.type_name})" if p.type_name else ""
        lines.append(f"* ``{p.name.upper()}``: Positional argument{type_repr}.")
    return lines


def _generate_command_docs(
    prog: str,
    command_path: list[str],
    app:  App,
    md_lines: list[str],
) -> None:
    """Append Markdown documentation for a single command.

    Parameters
    ----------
    prog:
        Name of the root program.
    command_path:
        list representing the nested command invocation.
    app:
        Cyclopts subapp whose default_command will be documented.
    md_lines:
        list of lines to append documentation to.
    """
    default_cmd = getattr(app, "default_command", None)
    if default_cmd is None:
        return

    # Section header: combine program name and command tokens
    heading_tokens = [prog] + command_path
    md_lines.append(f"## ``{' '.join(heading_tokens)}``")

    # Description
    description = inspect.getdoc(default_cmd) or ""
    if description:
        md_lines.append("")
        md_lines.append(description.strip())
        md_lines.append("")

    # Usage
    params = _extract_params(default_cmd)
    md_lines.append("**Usage:**")
    md_lines.append("")
    md_lines.append(_format_usage(prog, command_path, params))
    md_lines.append("")

    # Arguments
    arg_lines = _format_arguments(params)
    if arg_lines:
        md_lines.append("**Arguments:**")
        md_lines.extend(arg_lines)
        md_lines.append("")

    # Options
    opt_lines = _format_options(params)
    if opt_lines:
        md_lines.append("**Options:**")
        md_lines.extend(opt_lines)
        md_lines.append("")


def _walk_app(app: App, path: list[str]) -> Iterable[tuple[list[str], App]]:
    """Recursively yield (command_path, subapp) pairs for all commands.

    Parameters
    ----------
    app:
        The Cyclopts App to traverse.
    path:
        Accumulated command tokens leading to this app.

    Yields
    ------
    (list[str], App)
        Each registered command and its associated subapp.
    """
    commands = getattr(app, "_registered_commands", {})
    for name, sub_app in commands.items():
        current_path = path + [name]
        yield current_path, sub_app
        # Recurse into nested commands
        yield from _walk_app(sub_app, current_path)


def generate_docs(app: App, name: str | None = None) -> str:
    """Return Markdown documentation for a Cyclopts CLI application.

    Walk the App, and generate top‑level and per‑command documentation similar 
    to Typer's `typer utils docs` subcommand.

    Parameters
    ----------
    app:
        The Cyclopts App to document.
    name:
        Optional program name override.  If not provided, uses
        ``app.name[0]`` as the root command.

    Returns
    -------
    str
        A Markdown string documenting the CLI.
    """
    prog = name or (app.name[0] if getattr(app, "name", None) else "cli")
    md_lines: list[str] = []

    # Top-level header and description
    md_lines.append(f"## ``{prog}``")

    # Use app.help property as description
    description = getattr(app, "help", "")
    if description:
        md_lines.append("")
        md_lines.append(description.strip())
        md_lines.append("")

    # Usage for top-level: show options and command placeholder
    md_lines.append("**Usage:**")
    md_lines.append("")
    md_lines.append(f"``$ {prog} [OPTIONS] COMMAND [ARGS]...``")
    md_lines.append("")

    # Options: list global help/version flags from the app
    help_flags = getattr(app, "help_flags", [])
    version_flags = getattr(app, "version_flags", [])
    option_lines: list[str] = []
    for flag in help_flags:
        option_lines.append(f"* ``{flag}``: Show help and exit.")
    for flag in version_flags:
        option_lines.append(f"* ``{flag}``: Show version and exit.")
    if option_lines:
        md_lines.append("**Options:**")
        md_lines.extend(option_lines)
        md_lines.append("")

    # Commands listing
    commands = getattr(app, "_registered_commands", {})
    if commands:
        md_lines.append("**Commands:**")
        for cmd_name, sub_app in commands.items():
            cmd_help = getattr(sub_app, "help", "").strip()
            summary = cmd_help.split("\n", 1)[0] if cmd_help else ""
            md_lines.append(f"* ``{cmd_name}``: {summary if summary else 'No description.'}")
        md_lines.append("")

    # Finally, recursively walk and generate the docs
    for command_path, sub_app in _walk_app(app, []):
        _generate_command_docs(prog, command_path, sub_app, md_lines)
    return "\n".join(md_lines)


def init_docs(app: App, name: str | None = None) -> App:
    """Register a ``docs`` command on a Cyclopts app to generate Markdown docs.

    Running `python your_file.py docs` will print the Markdown docs to the CLI.
    Optionally , the output can be redirected to the file provided via the
    `--output` argument.

    Parameters
    ----------
    app:
        The Cyclopts App to augment.
    name:
        Optional override for the program name used in the docs.  If
        omitted, ``app.name[0]`` is used.

    Returns
    -------
    cyclopts.App
        The same application passed in, for method‑chaining convenience.
    """
    def _docs_command(output: Path|None = None) -> None:
        md = generate_docs(app, name=name)
        if output:
            with output.open("w", encoding="utf-8") as f:
                f.write(md)
            print(f"Docs saved to: {output}")
        else:
            print(md)

    app.command(name="docs", help="Generate Markdown documentation for this CLI.")(_docs_command)
    return app
