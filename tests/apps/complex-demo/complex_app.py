"""Complex Demo Application - Comprehensive edge case testing for documentation generation.

This application tests all known edge cases for cyclopts documentation plugins:
- Dataclass parameter flattening with @Parameter(name="*")
- Pydantic model support
- attrs class support
- 3+ level nested command hierarchies
- Complex union types (int | Literal[...])
- Custom groups with Group.create_ordered()
- meta.default pattern for global options
- Count parameters, parse=False, allow_leading_hyphen
- Validators
- Hidden commands/parameters
- Multiple docstring formats
- Enums and Flags
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum, Flag, auto
from pathlib import Path
from typing import Annotated, Literal

import cyclopts
from cyclopts import App, Group, Parameter, validators

# ============================================================================
# Enums and Flags
# ============================================================================


class LogLevel(Enum):
    """Log level enumeration."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class OutputFormat(Enum):
    """Output format options."""

    JSON = "json"
    YAML = "yaml"
    TABLE = "table"
    CSV = "csv"


class Permission(Flag):
    """Permission flags for access control."""

    NONE = 0
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    ADMIN = READ | WRITE | EXECUTE


# ============================================================================
# Dataclasses with Parameter(name="*") for flattening
# ============================================================================


@cyclopts.Parameter(name="*")
@dataclass(frozen=True)
class DatabaseConfig:
    """Database connection configuration.

    Parameters
    ----------
    host
        Database server hostname.
    port
        Database server port number.
    username
        Authentication username.
    password
        Authentication password (optional).
    ssl_mode
        SSL connection mode.
    pool_size
        Connection pool size.
    """

    host: str = "localhost"
    port: int = 5432
    username: str = "admin"
    password: str | None = None
    ssl_mode: Literal["disable", "prefer", "require", "verify-full"] = "prefer"
    pool_size: Annotated[int, Parameter(validator=validators.Number(gte=1, lte=100))] = 10


@cyclopts.Parameter(name="*")
@dataclass
class ProcessingConfig:
    """Data processing configuration.

    Parameters
    ----------
    batch_size
        Number of items to process per batch.
    num_workers
        Number of parallel workers. Use "auto" for automatic detection.
    quality_level
        Processing quality level. Higher values mean better quality but slower.
    device
        Computing device to use. Can be "cuda", "cpu", "auto", or a GPU index.
    output_formats
        List of output formats to generate.
    """

    batch_size: Annotated[int, Parameter(validator=validators.Number(gt=0))] = 32
    num_workers: int | Literal["auto"] = "auto"
    quality_level: int | Literal["high", "medium", "low"] = "high"
    device: Literal["cuda", "cpu", "auto"] | int = "auto"
    output_formats: list[OutputFormat] = field(default_factory=lambda: [OutputFormat.JSON])


@cyclopts.Parameter(name="*")
@dataclass(frozen=True)
class PathConfig:
    """Path configuration for input/output directories.

    Parameters
    ----------
    input_dir
        Input data directory.
    output_dir
        Output results directory.
    cache_dir
        Cache directory for intermediate files.
    log_dir
        Directory for log files.
    """

    input_dir: Path = Path("data/input")
    output_dir: Path = Path("data/output")
    cache_dir: Path | None = None
    log_dir: Path = Path("logs")


# Nested dataclass (dataclass containing another dataclass)
@cyclopts.Parameter(name="*")
@dataclass
class PipelineConfig:
    """Complete pipeline configuration combining multiple configs.

    Parameters
    ----------
    name
        Pipeline name for identification.
    paths
        Path configuration.
    processing
        Processing configuration.
    dry_run
        If True, simulate execution without making changes.
    """

    name: str = "default-pipeline"
    paths: PathConfig = field(default_factory=PathConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    dry_run: bool = False


# ============================================================================
# Pydantic Models
# ============================================================================

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Server configuration using Pydantic.

    Parameters
    ----------
    host
        Server bind address.
    port
        Server port number.
    workers
        Number of worker processes.
    timeout
        Request timeout in seconds.
    debug
        Enable debug mode.
    """

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=4, ge=1)
    timeout: float = 30.0
    debug: bool = False


class AuthConfig(BaseModel):
    """Authentication configuration.

    Parameters
    ----------
    provider
        Authentication provider type.
    token_expiry
        Token expiration time in seconds.
    refresh_enabled
        Enable token refresh.
    allowed_origins
        List of allowed CORS origins.
    """

    provider: Literal["oauth2", "jwt", "basic", "none"] = "jwt"
    token_expiry: int = 3600
    refresh_enabled: bool = True
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])


# ============================================================================
# attrs Classes
# ============================================================================

import attrs


@attrs.define
class CacheConfig:
    """Cache configuration using attrs.

    Parameters
    ----------
    backend
        Cache backend type.
    ttl
        Time-to-live in seconds.
    max_size
        Maximum cache size in MB.
    compression
        Enable compression.
    """

    backend: Literal["memory", "redis", "memcached", "disk"] = "memory"
    ttl: int = 300
    max_size: int = 1024
    compression: bool = False


# ============================================================================
# Main Application with Groups
# ============================================================================

# Create ordered groups for better organization
# Note: Use create_ordered() consistently for all groups to avoid sort_key type conflicts
# create_ordered() generates tuple sort_keys like (sort_key, count) while plain Group() uses raw values
global_group = Group.create_ordered("Global Options", sort_key=0)
subcommands_group = Group.create_ordered("Subcommands", sort_key=1)
utilities_group = Group.create_ordered("Utilities", sort_key=2)
hidden_group = Group.create_ordered("Hidden", sort_key=99, show=False)

app = App(
    name="complex-cli",
    help="Complex CLI application for comprehensive documentation testing.",
    version="1.0.0",
)
app.meta.group_parameters = global_group


# ============================================================================
# Meta Default - Global option interceptor
# ============================================================================


@app.meta.default
def main_launcher(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    config_file: Annotated[Path | None, Parameter(parse=False, group=global_group)] = None,
    verbose: Annotated[int, Parameter(name=["-v", "--verbose"], count=True, group=global_group)] = 0,
    quiet: Annotated[bool, Parameter(name=["-q", "--quiet"], group=global_group)] = False,
    log_level: Annotated[LogLevel, Parameter(group=global_group)] = LogLevel.INFO,
    no_color: Annotated[bool, Parameter(group=global_group, help="Disable colored output")] = False,
):
    """Global option handler that intercepts all commands.

    This demonstrates the meta.default pattern for handling global options
    that apply to all subcommands.

    Parameters
    ----------
    tokens
        Command tokens to forward.
    config_file
        Configuration file path (not parsed from CLI).
    verbose
        Verbosity level (-v, -vv, -vvv).
    quiet
        Suppress non-essential output.
    log_level
        Logging level.
    no_color
        Disable colored output.
    """
    # In real usage, this would set up logging, load config, etc.
    app(tokens)


# ============================================================================
# Simple Commands
# ============================================================================


@app.command(alias=["ver", "v"], group=utilities_group)
def version():
    """Show version information.

    Displays the application version and system information.
    """
    print("complex-cli version 1.0.0")
    print(f"Python {sys.version}")


@app.command(alias="i", group=utilities_group)
def info(
    detailed: bool = False,
    format: OutputFormat = OutputFormat.TABLE,
):
    """Show application information.

    Parameters
    ----------
    detailed
        Show detailed information including dependencies.
    format
        Output format for the information.
    """
    print(f"Info: detailed={detailed}, format={format.value}")


@app.command(group=hidden_group, show=False)
def debug_internal():
    """Internal debug command (hidden from help).

    This command is for internal debugging purposes only.
    """
    print("Debug internal command executed")


# ============================================================================
# Level 1: Admin App
# ============================================================================

admin_app = App(
    name="admin",
    help="Administrative commands for system management.",
    group=subcommands_group,
    default_parameter=Parameter(negative=""),
)
app.command(admin_app)


@admin_app.command
def status(
    services: list[str] | None = None,
    *,
    watch: Annotated[bool, Parameter(name=["-w", "--watch"])] = False,
    interval: Annotated[int, Parameter(validator=validators.Number(gte=1))] = 5,
):
    """Show system status.

    Parameters
    ----------
    services
        Specific services to check (all if not specified).
    watch
        Continuously watch status.
    interval
        Refresh interval in seconds when watching.
    """
    print(f"Status: services={services}, watch={watch}, interval={interval}")


@admin_app.command
def config_cmd(
    *,
    db: DatabaseConfig = DatabaseConfig(),  # noqa: B008
):
    """Configure database settings.

    Parameters
    ----------
    db
        Database configuration options.
    """
    print(f"Config: db={db}")


# ============================================================================
# Level 2: Users App (nested under admin)
# ============================================================================

users_app = App(
    name="users",
    help="User management commands.",
)
admin_app.command(users_app)


@users_app.command
def list_users(
    active_only: bool = False,
    role: Literal["admin", "user", "guest"] | None = None,
    limit: Annotated[int, Parameter(validator=validators.Number(gte=1, lte=1000))] = 100,
    format: OutputFormat = OutputFormat.TABLE,
):
    """List all users.

    Parameters
    ----------
    active_only
        Show only active users.
    role
        Filter by user role.
    limit
        Maximum number of users to display.
    format
        Output format.
    """
    print(f"List users: active_only={active_only}, role={role}, limit={limit}")


@users_app.command
def create(
    username: str,
    email: str,
    /,
    *,
    role: Literal["admin", "user", "guest"] = "user",
    permissions: Permission = Permission.READ,
    send_welcome: bool = True,
):
    """Create a new user.

    Parameters
    ----------
    username
        Unique username for the new user.
    email
        Email address for the new user.
    role
        User role assignment.
    permissions
        Initial permission flags.
    send_welcome
        Send welcome email after creation.
    """
    print(f"Create user: {username}, {email}, role={role}, permissions={permissions}")


@users_app.command
def delete(
    username: str,
    /,
    *,
    force: Annotated[bool, Parameter(name=["-f", "--force"])] = False,
    backup: bool = True,
):
    """Delete a user.

    Parameters
    ----------
    username
        Username to delete.
    force
        Skip confirmation prompt.
    backup
        Create backup before deletion.
    """
    print(f"Delete user: {username}, force={force}, backup={backup}")


# ============================================================================
# Level 3: Permissions App (nested under users)
# ============================================================================

permissions_app = App(
    name="permissions",
    help="Permission management for users.",
)
users_app.command(permissions_app)


@permissions_app.command
def grant(
    username: str,
    permission: Permission,
    /,
    *,
    resource: str | None = None,
    expires: str | None = None,
):
    """Grant permissions to a user.

    Parameters
    ----------
    username
        Target username.
    permission
        Permission flags to grant.
    resource
        Specific resource to grant access to.
    expires
        Expiration date (ISO format).
    """
    print(f"Grant: {username}, {permission}, resource={resource}")


@permissions_app.command
def revoke(
    username: str,
    permission: Permission,
    /,
):
    """Revoke permissions from a user.

    Parameters
    ----------
    username
        Target username.
    permission
        Permission flags to revoke.
    """
    print(f"Revoke: {username}, {permission}")


@permissions_app.command
def audit(
    username: str | None = None,
    days: int = 30,
    format: OutputFormat = OutputFormat.TABLE,
):
    """Audit permission changes.

    Parameters
    ----------
    username
        Filter by username (all users if not specified).
    days
        Number of days to look back.
    format
        Output format for audit report.
    """
    print(f"Audit: username={username}, days={days}, format={format}")


# ============================================================================
# Level 4: Roles App (nested under permissions) - 4 levels deep!
# ============================================================================

roles_app = App(
    name="roles",
    help="Role template management.",
)
permissions_app.command(roles_app)


@roles_app.command
def list_roles(
    include_system: bool = False,
):
    """List all role templates.

    Parameters
    ----------
    include_system
        Include built-in system roles.
    """
    print(f"List roles: include_system={include_system}")


@roles_app.command
def create_role(
    name: str,
    /,
    *,
    permissions: Permission = Permission.READ,
    description: str = "",
):
    """Create a new role template.

    Parameters
    ----------
    name
        Role name.
    permissions
        Default permissions for this role.
    description
        Role description.
    """
    print(f"Create role: {name}, permissions={permissions}")


# ============================================================================
# Data Processing App with Dataclass Flattening
# ============================================================================

data_app = App(
    name="data",
    help="Data processing commands.",
    group=subcommands_group,
)
app.command(data_app)


@data_app.command
def process(
    input_files: Annotated[list[Path], Parameter(help="Input files to process")],
    /,
    *,
    config: ProcessingConfig = ProcessingConfig(),  # noqa: B008
    paths: PathConfig = PathConfig(),  # noqa: B008
):
    """Process data files with configurable options.

    This command demonstrates dataclass parameter flattening where
    all fields from ProcessingConfig and PathConfig become CLI options.

    Parameters
    ----------
    input_files
        List of input files to process.
    config
        Processing configuration.
    paths
        Path configuration.
    """
    print(f"Process: files={input_files}, config={config}, paths={paths}")


@data_app.command
def pipeline(
    *,
    config: PipelineConfig = PipelineConfig(),  # noqa: B008
):
    """Run a complete data pipeline.

    Demonstrates nested dataclass flattening (PipelineConfig contains
    PathConfig and ProcessingConfig).

    Parameters
    ----------
    config
        Complete pipeline configuration.
    """
    print(f"Pipeline: config={config}")


@data_app.command
def validate(
    input_path: Path,
    /,
    *,
    strict: bool = False,
    schema_file: Annotated[Path | None, Parameter(validator=validators.Path(exists=True))] = None,
    ignore_patterns: list[str] | None = None,
):
    """Validate data files against schema.

    Parameters
    ----------
    input_path
        Path to validate.
    strict
        Enable strict validation mode.
    schema_file
        Custom schema file (must exist).
    ignore_patterns
        Patterns to ignore during validation.
    """
    print(f"Validate: {input_path}, strict={strict}")


# ============================================================================
# Server App
# ============================================================================

server_app = App(
    name="server",
    help="Server management commands.",
    group=subcommands_group,
)
app.command(server_app)


@server_app.command
def start(
    *,
    server: ServerConfig = ServerConfig(),  # noqa: B008
    auth: AuthConfig = AuthConfig(),  # noqa: B008
):
    """Start the server with configuration.

    Demonstrates Pydantic model support for CLI parameters.

    Parameters
    ----------
    server
        Server configuration.
    auth
        Authentication configuration.
    """
    print(f"Start server: {server}, auth={auth}")


@server_app.command
def stop(
    *,
    graceful: bool = True,
    timeout: Annotated[int, Parameter(validator=validators.Number(gte=0))] = 30,
    force: Annotated[bool, Parameter(name=["-f", "--force"])] = False,
):
    """Stop the server.

    Parameters
    ----------
    graceful
        Perform graceful shutdown.
    timeout
        Shutdown timeout in seconds.
    force
        Force immediate shutdown.
    """
    print(f"Stop server: graceful={graceful}, timeout={timeout}, force={force}")


@server_app.command
def restart(
    rolling: bool = False,
    delay: int = 5,
):
    """Restart the server.

    Parameters
    ----------
    rolling
        Perform rolling restart (zero downtime).
    delay
        Delay between worker restarts in seconds.
    """
    print(f"Restart server: rolling={rolling}, delay={delay}")


# ============================================================================
# Cache App
# ============================================================================

cache_app = App(
    name="cache",
    help="Cache management commands.",
    group=utilities_group,
)
app.command(cache_app)


@cache_app.command
def configure(
    *,
    config: CacheConfig = CacheConfig(),  # noqa: B008
):
    """Configure cache settings.

    Demonstrates attrs class support for CLI parameters.

    Parameters
    ----------
    config
        Cache configuration.
    """
    print(f"Configure cache: {config}")


@cache_app.command
def clear(
    pattern: str = "*",
    dry_run: bool = False,
):
    """Clear cache entries.

    Parameters
    ----------
    pattern
        Pattern to match cache keys.
    dry_run
        Show what would be cleared without actually clearing.
    """
    print(f"Clear cache: pattern={pattern}, dry_run={dry_run}")


@cache_app.command
def stats(
    detailed: bool = False,
    format: OutputFormat = OutputFormat.TABLE,
):
    """Show cache statistics.

    Parameters
    ----------
    detailed
        Show detailed statistics.
    format
        Output format.
    """
    print(f"Cache stats: detailed={detailed}, format={format}")


# ============================================================================
# Complex Type Examples
# ============================================================================


@app.command(group=utilities_group)
def complex_types(
    # Union with Literal and int
    worker_count: int | Literal["auto"] = "auto",
    # Union with multiple Literals
    quality: Literal["low", "medium", "high"] | Literal["custom"] = "medium",
    # Optional list
    tags: list[str] | None = None,
    # List of enums
    formats: list[OutputFormat] = [OutputFormat.JSON],  # noqa: B006
    # Complex nested type
    thresholds: list[float] | Literal["default"] = "default",
    # Path that may or may not exist
    config_path: Annotated[Path | None, Parameter(validator=validators.Path(exists=True))] = None,
):
    """Demonstrate complex type annotations.

    This command showcases various complex type patterns that the
    documentation system needs to handle correctly.

    Parameters
    ----------
    worker_count
        Number of workers or "auto" for automatic detection.
    quality
        Quality preset or "custom" for manual configuration.
    tags
        Optional list of tags.
    formats
        List of output formats.
    thresholds
        Threshold values or "default" for defaults.
    config_path
        Optional config file path (must exist if provided).
    """
    print(f"Complex types: worker_count={worker_count}, quality={quality}")


# ============================================================================
# Commands with Various Docstring Styles
# ============================================================================


@app.command(group=utilities_group)
def numpy_style(
    name: str,
    count: int = 1,
):
    """Command with NumPy-style docstring.

    This command demonstrates NumPy docstring format which is the
    default for cyclopts.

    Parameters
    ----------
    name : str
        The name parameter.
    count : int, optional
        The count parameter, by default 1.

    Returns
    -------
    None
        This function doesn't return anything.

    Raises
    ------
    ValueError
        If name is empty.

    Examples
    --------
    >>> numpy_style("test", count=5)
    """
    print(f"NumPy style: name={name}, count={count}")


@app.command(group=utilities_group)
def google_style(
    name: str,
    count: int = 1,
):
    """Command with Google-style docstring.

    This command demonstrates Google docstring format.

    Args:
        name: The name parameter.
        count: The count parameter. Defaults to 1.

    Returns
    -------
        None: This function doesn't return anything.

    Raises
    ------
        ValueError: If name is empty.

    Example:
        >>> google_style("test", count=5)
    """
    print(f"Google style: name={name}, count={count}")


@app.command(group=utilities_group)
def sphinx_style(
    name: str,
    count: int = 1,
):
    """Command with Sphinx-style docstring.

    This command demonstrates Sphinx/reST docstring format.

    :param name: The name parameter.
    :type name: str
    :param count: The count parameter.
    :type count: int
    :returns: None
    :rtype: None
    :raises ValueError: If name is empty.
    """
    print(f"Sphinx style: name={name}, count={count}")


# ============================================================================
# Hidden and Show=False Examples
# ============================================================================


@app.command(show=False)
def internal_maintenance():
    """Internal maintenance command.

    This command is hidden from the main help but can still be invoked.
    """
    print("Running internal maintenance...")


@app.command(group=hidden_group)
def secret_feature(
    enable: bool = False,
    code: Annotated[str, Parameter(show=False)] = "default",
):
    """Secret feature command.

    This command has a hidden parameter.

    Parameters
    ----------
    enable
        Enable the secret feature.
    code
        Secret activation code (hidden from help).
    """
    print(f"Secret feature: enable={enable}, code={code}")


if __name__ == "__main__":
    app()
