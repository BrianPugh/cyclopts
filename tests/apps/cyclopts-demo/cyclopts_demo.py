#!/usr/bin/env python
"""Cyclopts Demo Application - Testing completion features."""

from pathlib import Path
from typing import Annotated, Literal, Optional

from cyclopts import App, Parameter, validators

app = App(
    name="cyclopts-demo",
    help="Demo application for testing Cyclopts completion features.",
)
app.register_install_completion()


@app.default
def main(
    verbose: bool = False,
    config: Optional[Path] = None,
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


@app.command
def files(
    input_file: Path,
    output_file: Optional[Path] = None,
    directory: Annotated[
        Path, Parameter(validator=validators.Path(exists=True, dir_okay=True, file_okay=False))
    ] = Path(),
    format: Literal["json", "yaml", "toml", "xml"] = "json",
):
    """Work with files.

    Parameters
    ----------
    input_file : Path
        Input file to process.
    output_file : Path, optional
        Output file path.
    directory : Path
        Working directory.
    format : Literal["json", "yaml", "toml", "xml"]
        Output format.
    """
    print(f"Files: input={input_file}, output={output_file}, dir={directory}, format={format}")


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
    tags: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
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
    password: Optional[str] = None,
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
    target: Optional[str] = None,
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
    tables: Optional[list[str]] = None,
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
