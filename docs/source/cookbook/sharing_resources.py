import inspect
import itertools
import sys
from contextlib import ExitStack
from typing import Annotated, Optional

from cyclopts import App, Dispatcher, Parameter

app = App(name="demo-shell-app")


class Connection:
    """Dummy connection implementation contextmanager for demo."""

    def __init__(self, uri):
        self.uri = uri

    def __enter__(self):
        print(f"Opening connection to {self.uri}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"Closing connection to {self.uri}")


# Shared connection between shell commands.
_in_shell = False


@app.meta.default
def main(*tokens: Annotated[str, Parameter(show=False)], uri: Optional[str] = None):
    """Main Application Help String.

    Parameters
    ----------
    uri
        Some URI to connect to.
    """
    global _in_shell

    connection: Connection = None
    delimiter = "AND"
    # The ``or [[]]` is so that groups has at least one (empty) element.
    groups = [list(group) for key, group in itertools.groupby(tokens, lambda x: x == delimiter) if not key] or [[]]

    with ExitStack() as stack:

        def dispatcher(command, bound):
            nonlocal connection
            additional_kwargs = {}
            if "connection" in inspect.signature(command).parameters:
                if connection is None:
                    # Instantiate connection the first time it's needed.
                    if uri:
                        connection = stack.enter_context(Connection(uri))
                    else:
                        print("Need to specify URI: --uri VALUE.")
                        sys.exit(1)
                additional_kwargs["connection"] = connection
            if command == shell:
                additional_kwargs["dispatcher"] = dispatcher

            command(*bound.args, **bound.kwargs, **additional_kwargs)

        for group in groups:
            command, bound = app.parse_args(group, exit_on_error=not _in_shell)
            dispatcher(command, bound)


@app.default
def shell(*, dispatcher: Annotated[Dispatcher, Parameter(parse=False)]):
    global _in_shell
    if _in_shell:
        print("Cannot nest shells.")
    _in_shell = True
    try:
        app.interactive_shell(prompt="> ", dispatcher=dispatcher)
    finally:
        _in_shell = False


@app.command
def foo(count: int = 1, *, connection: Annotated[Connection, Parameter(parse=False)]):
    """Applies "foo" to the connection "count" times.

    Parameters
    ----------
    foo: int
        Number of times to apply foo.
    """
    print(f"Calling {count}x FOO on {connection.uri}.")


@app.command
def bar():
    print("The command 'bar' was called.")


@app.command
def help():
    """Display help screen."""
    app.help_print([])


if __name__ == "__main__":
    app.meta()
