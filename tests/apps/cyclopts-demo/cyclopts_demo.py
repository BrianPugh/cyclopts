#!/usr/bin/env python
"""Cyclopts Demo Application - Testing completion features."""

from pathlib import Path
from typing import Annotated, Literal

from cyclopts import App, Parameter, validators

app = App(
    name="cyclopts-demo",
    help="Demo application for testing Cyclopts completion features.",
)
app.register_install_completion_command()


@app.default
def main(
    verbose: bool = False,
    config: Path | None = None,
):
    """Main command.

    Parameters
    ----------
    verbose : bool
        Enable verbose output.
    config : Path, optional
        Configuration file path.
    """
    print(f"Main command: verbose={verbose}, config={config}")


files_app = App(name="files", help="File operations commands.")
app.command(files_app)


@files_app.command
def cp(
    source: Path,
    destination: Path,
    /,
    *,
    recursive: Annotated[bool, Parameter(help="Copy directories recursively")] = False,
    preserve: Annotated[bool, Parameter(help="Preserve file attributes")] = False,
    verbose: bool = False,
):
    """Copy files or directories.

    Parameters
    ----------
    source : Path
        Source file or directory.
    destination : Path
        Destination file or directory.
    recursive : bool
        Copy directories recursively.
    preserve : bool
        Preserve file attributes (timestamps, permissions).
    verbose : bool
        Show verbose output.
    """
    print(f"Copy: {source} -> {destination} (recursive={recursive}, preserve={preserve}, verbose={verbose})")


@files_app.command
def mv(
    source: Path,
    destination: Path,
    /,
    *,
    force: Annotated[bool, Parameter(help="Force overwrite if destination exists")] = False,
    backup: Annotated[bool, Parameter(help="Create backup of existing destination")] = False,
    verbose: bool = False,
):
    """Move files or directories.

    Parameters
    ----------
    source : Path
        Source file or directory.
    destination : Path
        Destination file or directory.
    force : bool
        Force overwrite if destination exists.
    backup : bool
        Create backup of existing destination files.
    verbose : bool
        Show verbose output.
    """
    print(f"Move: {source} -> {destination} (force={force}, backup={backup}, verbose={verbose})")


@files_app.command
def ls(
    path: Path = Path(),
    /,
    *,
    all: Annotated[bool, Parameter(help="Show hidden files")] = False,
    long: Annotated[bool, Parameter(help="Use long listing format")] = False,
    sort_by: Literal["name", "size", "time", "extension"] = "name",
    reverse: bool = False,
):
    """List directory contents.

    Parameters
    ----------
    path : Path
        Directory path to list (defaults to current directory).
    all : bool
        Show hidden files and directories.
    long : bool
        Use long listing format with details.
    sort_by : Literal["name", "size", "time", "extension"]
        Sort order.
    reverse : bool
        Reverse sort order.
    """
    print(f"List: {path} (all={all}, long={long}, sort_by={sort_by}, reverse={reverse})")


@files_app.command
def find(
    pattern: str,
    /,
    *,
    path: Path = Path(),
    type: Literal["file", "directory", "symlink", "any"] = "any",
    case_sensitive: bool = True,
    max_depth: int | None = None,
):
    """Find files matching a pattern.

    Parameters
    ----------
    pattern : str
        Search pattern (supports wildcards).
    path : Path
        Root directory to search from.
    type : Literal["file", "directory", "symlink", "any"]
        Type of filesystem entry to find.
    case_sensitive : bool
        Case-sensitive pattern matching.
    max_depth : int, optional
        Maximum search depth (None for unlimited).
    """
    print(f"Find: pattern={pattern}, path={path}, type={type}, case_sensitive={case_sensitive}, max_depth={max_depth}")


@app.command
def positional_choice(param: Literal["foo", "bar", "baz"], /):
    """Test positional-only parameter with Literal choices.

    Parameters
    ----------
    param : Literal["foo", "bar", "baz"]
        Choose one: foo, bar, or baz.
    """
    print(f"Called with: {param}")


@app.command
def multi_positional(
    first: Literal["alpha", "beta", "gamma"],
    second: Literal["red", "green", "blue"],
    /,
):
    """Test multiple positional-only parameters with Literal choices.

    Parameters
    ----------
    first : Literal["alpha", "beta", "gamma"]
        First choice: Greek letters.
    second : Literal["red", "green", "blue"]
        Second choice: colors.
    """
    print(f"Called with: first={first}, second={second}")


@app.command
def deploy(
    environment: Literal["dev", "staging", "production"],
    region: Literal["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"] = "us-east-1",
    dry_run: bool = False,
    skip_tests: bool = False,
    confirm: bool = True,
):
    """Deploy application.

    Parameters
    ----------
    environment : Literal["dev", "staging", "production"]
        Target environment.
    region : Literal["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
        AWS region.
    dry_run : bool
        Perform a dry run without making changes.
    skip_tests : bool
        Skip running tests.
    confirm : bool
        Require confirmation before deploying.
    """
    print(f"Deploy: env={environment}, region={region}, dry_run={dry_run}, skip_tests={skip_tests}, confirm={confirm}")


@app.command
def process(
    items: list[str],
    count: Annotated[int, Parameter(validator=validators.Number(gt=0, lte=100))] = 1,
    threshold: float = 0.5,
    tags: list[str] | None = None,
    exclude: list[str] | None = None,
):
    """Process items.

    Parameters
    ----------
    items : list[str]
        Items to process.
    count : int
        Number of iterations (1-100).
    threshold : float
        Processing threshold.
    tags : list[str], optional
        Tags to apply.
    exclude : list[str]
        Items to exclude.
    """
    if exclude is None:
        exclude = []
    print(f"Process: items={items}, count={count}, threshold={threshold}, tags={tags}, exclude={exclude}")


database_app = App(name="database", help="Database commands.")
app.command(database_app)


@database_app.command
def connect(
    host: str = "localhost",
    port: int = 5432,
    username: str = "admin",
    password: str | None = None,
    ssl: bool = True,
):
    """Connect to database.

    Parameters
    ----------
    host : str
        Database host.
    port : int
        Database port.
    username : str
        Username.
    password : str, optional
        Password.
    ssl : bool
        Use SSL connection.
    """
    print(f"DB Connect: host={host}, port={port}, user={username}, ssl={ssl}")


@database_app.command
def migrate(
    direction: Literal["up", "down"] = "up",
    steps: int = 1,
    target: str | None = None,
    force: bool = False,
):
    """Run database migrations.

    Parameters
    ----------
    direction : Literal["up", "down"]
        Migration direction.
    steps : int
        Number of migration steps.
    target : str, optional
        Target migration version.
    force : bool
        Force migration even with warnings.
    """
    print(f"DB Migrate: direction={direction}, steps={steps}, target={target}, force={force}")


@database_app.command
def backup(
    output: Path,
    tables: list[str] | None = None,
    compress: bool = True,
    encryption: Literal["none", "aes256", "rsa"] = "none",
):
    """Backup database.

    Parameters
    ----------
    output : Path
        Backup output file.
    tables : list[str], optional
        Specific tables to backup.
    compress : bool
        Compress backup.
    encryption : Literal["none", "aes256", "rsa"]
        Encryption method.
    """
    print(f"DB Backup: output={output}, tables={tables}, compress={compress}, encryption={encryption}")


server_app = App(name="server", help="Server management commands.")
app.command(server_app)


@server_app.command
def start(
    port: int = 8000,
    host: str = "0.0.0.0",
    workers: int = 4,
    reload: bool = False,
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info",
):
    """Start the server.

    Parameters
    ----------
    port : int
        Server port.
    host : str
        Server host.
    workers : int
        Number of worker processes.
    reload : bool
        Enable auto-reload.
    log_level : Literal["debug", "info", "warning", "error", "critical"]
        Logging level.
    """
    print(f"Server Start: host={host}, port={port}, workers={workers}, reload={reload}, log_level={log_level}")


@server_app.command
def stop(
    graceful: bool = True,
    timeout: int = 30,
):
    """Stop the server.

    Parameters
    ----------
    graceful : bool
        Graceful shutdown.
    timeout : int
        Shutdown timeout in seconds.
    """
    print(f"Server Stop: graceful={graceful}, timeout={timeout}")


@server_app.command
def status(
    detailed: bool = False,
    format: Literal["text", "json", "table"] = "text",
):
    """Show server status.

    Parameters
    ----------
    detailed : bool
        Show detailed status.
    format : Literal["text", "json", "table"]
        Output format.
    """
    print(f"Server Status: detailed={detailed}, format={format}")


if __name__ == "__main__":
    app()
