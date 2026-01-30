# complex-cli

```console
complex-cli COMMAND
```

Complex CLI application for comprehensive documentation testing.

## Table of Contents

- [`version`](#complex-cli-version)
- [`info`](#complex-cli-info)
- [`admin`](#complex-cli-admin)
    - [`status`](#complex-cli-admin-status)
    - [`config-cmd`](#complex-cli-admin-config-cmd)
    - [`users`](#complex-cli-admin-users)
        - [`list-users`](#complex-cli-admin-users-list-users)
        - [`create`](#complex-cli-admin-users-create)
        - [`delete`](#complex-cli-admin-users-delete)
        - [`permissions`](#complex-cli-admin-users-permissions)
            - [`grant`](#complex-cli-admin-users-permissions-grant)
            - [`revoke`](#complex-cli-admin-users-permissions-revoke)
            - [`audit`](#complex-cli-admin-users-permissions-audit)
            - [`roles`](#complex-cli-admin-users-permissions-roles)
                - [`list-roles`](#complex-cli-admin-users-permissions-roles-list-roles)
                - [`create-role`](#complex-cli-admin-users-permissions-roles-create-role)
- [`data`](#complex-cli-data)
    - [`process`](#complex-cli-data-process)
    - [`pipeline`](#complex-cli-data-pipeline)
    - [`validate`](#complex-cli-data-validate)
- [`server`](#complex-cli-server)
    - [`start`](#complex-cli-server-start)
    - [`stop`](#complex-cli-server-stop)
    - [`restart`](#complex-cli-server-restart)
- [`cache`](#complex-cli-cache)
    - [`configure`](#complex-cli-cache-configure)
    - [`clear`](#complex-cli-cache-clear)
    - [`stats`](#complex-cli-cache-stats)
- [`complex-types`](#complex-cli-complex-types)
- [`numpy-style`](#complex-cli-numpy-style)
- [`google-style`](#complex-cli-google-style)
- [`sphinx-style`](#complex-cli-sphinx-style)
- [`secret-feature`](#complex-cli-secret-feature)

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

**Subcommands**:

* [`admin`](#complex-cli-admin): Administrative commands for system management.
* [`data`](#complex-cli-data): Data processing commands.
* [`server`](#complex-cli-server): Server management commands.

**Utilities**:

* [`cache`](#complex-cli-cache): Cache management commands.
* [`complex-types`](#complex-cli-complex-types): Demonstrate complex type annotations.
* [`google-style`](#complex-cli-google-style): Command with Google-style docstring.
* [`info`](#complex-cli-info): Show application information.
* [`numpy-style`](#complex-cli-numpy-style): Command with NumPy-style docstring.
* [`sphinx-style`](#complex-cli-sphinx-style): Command with Sphinx-style docstring.
* [`version`](#complex-cli-version): Show version information.

## complex-cli version

```console
complex-cli version
```

Show version information.

Displays the application version and system information.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

## complex-cli info

```console
complex-cli info [ARGS]
```

Show application information.

**Parameters**:

* `DETAILED, --detailed, --no-detailed`: Show detailed information including dependencies.  *[default: False]*
* `FORMAT, --format`: Output format for the information.  *[choices: json, yaml, table, csv]*  *[default: table]*

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

## complex-cli admin

Administrative commands for system management.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

### complex-cli admin status

```console
complex-cli admin status [OPTIONS] [ARGS]
```

Show system status.

**Parameters**:

* `SERVICES, --services`: Specific services to check (all if not specified).
* `--watch, -w`: Continuously watch status.  *[default: False]*
* `--interval`: Refresh interval in seconds when watching.  *[default: 5]*

### complex-cli admin config-cmd

```console
complex-cli admin config-cmd [OPTIONS]
```

Configure database settings.

**Parameters**:

* `--host`: Database server hostname.  *[default: localhost]*
* `--port`: Database server port number.  *[default: 5432]*
* `--username`: Authentication username.  *[default: admin]*
* `--password`: Authentication password (optional).
* `--ssl-mode`: SSL connection mode.  *[choices: disable, prefer, require, verify-full]*  *[default: prefer]*
* `--pool-size`: Connection pool size.  *[default: 10]*

### complex-cli admin users

User management commands.

**Commands**:

* [`create`](#complex-cli-admin-users-create): Create a new user.
* [`delete`](#complex-cli-admin-users-delete): Delete a user.
* [`list-users`](#complex-cli-admin-users-list-users): List all users.
* [`permissions`](#complex-cli-admin-users-permissions): Permission management for users.

#### complex-cli admin users list-users

```console
complex-cli admin users list-users [ARGS]
```

List all users.

**Parameters**:

* `ACTIVE-ONLY, --active-only, --no-active-only`: Show only active users.  *[default: False]*
* `ROLE, --role`: Filter by user role.  *[choices: admin, user, guest]*
* `LIMIT, --limit`: Maximum number of users to display.  *[default: 100]*
* `FORMAT, --format`: Output format.  *[choices: json, yaml, table, csv]*  *[default: table]*

#### complex-cli admin users create

```console
complex-cli admin users create [OPTIONS] USERNAME EMAIL
```

Create a new user.

**Arguments**:

* `USERNAME`: Unique username for the new user.  **[required]**
* `EMAIL`: Email address for the new user.  **[required]**

**Parameters**:

* `--role`: User role assignment.  *[choices: admin, user, guest]*  *[default: user]*
* `--permissions.none, --permissions.no-none`: Initial permission flags.  *[default: False]*
* `--permissions.read, --permissions.no-read`: Initial permission flags.  *[default: False]*
* `--permissions.write, --permissions.no-write`: Initial permission flags.  *[default: False]*
* `--permissions.execute, --permissions.no-execute`: Initial permission flags.  *[default: False]*
* `--permissions.admin, --permissions.no-admin`: Initial permission flags.  *[default: False]*
* `--send-welcome, --no-send-welcome`: Send welcome email after creation.  *[default: True]*

#### complex-cli admin users delete

```console
complex-cli admin users delete [OPTIONS] USERNAME
```

Delete a user.

**Arguments**:

* `USERNAME`: Username to delete.  **[required]**

**Parameters**:

* `--force, --no-force, -f`: Skip confirmation prompt.  *[default: False]*
* `--backup, --no-backup`: Create backup before deletion.  *[default: True]*

#### complex-cli admin users permissions

Permission management for users.

##### complex-cli admin users permissions grant

```console
complex-cli admin users permissions grant [OPTIONS] USERNAME PERMISSION
```

Grant permissions to a user.

**Arguments**:

* `USERNAME`: Target username.  **[required]**
* `PERMISSION`: Permission flags to grant.  **[required]**  *[choices: none, read, write, execute, admin]*

**Parameters**:

* `--resource`: Specific resource to grant access to.
* `--expires`: Expiration date (ISO format).

##### complex-cli admin users permissions revoke

```console
complex-cli admin users permissions revoke USERNAME PERMISSION
```

Revoke permissions from a user.

**Arguments**:

* `USERNAME`: Target username.  **[required]**
* `PERMISSION`: Permission flags to revoke.  **[required]**  *[choices: none, read, write, execute, admin]*

##### complex-cli admin users permissions audit

```console
complex-cli admin users permissions audit [ARGS]
```

Audit permission changes.

**Parameters**:

* `USERNAME, --username`: Filter by username (all users if not specified).
* `DAYS, --days`: Number of days to look back.  *[default: 30]*
* `FORMAT, --format`: Output format for audit report.  *[choices: json, yaml, table, csv]*  *[default: table]*

##### complex-cli admin users permissions roles

Role template management.

**Commands**:

* [`create-role`](#complex-cli-admin-users-permissions-roles-create-role): Create a new role template.
* [`list-roles`](#complex-cli-admin-users-permissions-roles-list-roles): List all role templates.

###### complex-cli admin users permissions roles list-roles

```console
complex-cli admin users permissions roles list-roles [ARGS]
```

List all role templates.

**Parameters**:

* `INCLUDE-SYSTEM, --include-system, --no-include-system`: Include built-in system roles.  *[default: False]*

###### complex-cli admin users permissions roles create-role

```console
complex-cli admin users permissions roles create-role [OPTIONS] NAME
```

Create a new role template.

**Arguments**:

* `NAME`: Role name.  **[required]**

**Parameters**:

* `--permissions.none, --permissions.no-none`: Default permissions for this role.  *[default: False]*
* `--permissions.read, --permissions.no-read`: Default permissions for this role.  *[default: False]*
* `--permissions.write, --permissions.no-write`: Default permissions for this role.  *[default: False]*
* `--permissions.execute, --permissions.no-execute`: Default permissions for this role.  *[default: False]*
* `--permissions.admin, --permissions.no-admin`: Default permissions for this role.  *[default: False]*
* `--description`: Role description.  *[default: ""]*

## complex-cli data

Data processing commands.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

### complex-cli data process

```console
complex-cli data process [OPTIONS] INPUT_FILES
```

Process data files with configurable options.

This command demonstrates dataclass parameter flattening where
all fields from ProcessingConfig and PathConfig become CLI options.

**Arguments**:

* `INPUT_FILES`: Input files to process  **[required]**

**Parameters**:

* `--batch-size`: Number of items to process per batch.  *[default: 32]*
* `--num-workers`: Number of parallel workers. Use "auto" for automatic detection.  *[choices: auto]*  *[default: auto]*
* `--quality-level`: Processing quality level. Higher values mean better quality but slower.  *[choices: high, medium, low]*  *[default: high]*
* `--device`: Computing device to use. Can be "cuda", "cpu", "auto", or a GPU index.  *[choices: cuda, cpu, auto]*  *[default: auto]*
* `--output-formats, --empty-output-formats`: List of output formats to generate.  *[choices: json, yaml, table, csv]*  *[default: [json]]*
* `--input-dir`: Input data directory.  *[default: data/input]*
* `--output-dir`: Output results directory.  *[default: data/output]*
* `--cache-dir`: Cache directory for intermediate files.
* `--log-dir`: Directory for log files.  *[default: logs]*

### complex-cli data pipeline

```console
complex-cli data pipeline [OPTIONS]
```

Run a complete data pipeline.

Demonstrates nested dataclass flattening (PipelineConfig contains
PathConfig and ProcessingConfig).

**Parameters**:

* `--name`: Pipeline name for identification.  *[default: default-pipeline]*
* `--input-dir`: Input data directory.  *[default: data/input]*
* `--output-dir`: Output results directory.  *[default: data/output]*
* `--cache-dir`: Cache directory for intermediate files.
* `--log-dir`: Directory for log files.  *[default: logs]*
* `--batch-size`: Number of items to process per batch.  *[default: 32]*
* `--num-workers`: Number of parallel workers. Use "auto" for automatic detection.  *[choices: auto]*  *[default: auto]*
* `--quality-level`: Processing quality level. Higher values mean better quality but slower.  *[choices: high, medium, low]*  *[default: high]*
* `--device`: Computing device to use. Can be "cuda", "cpu", "auto", or a GPU index.  *[choices: cuda, cpu, auto]*  *[default: auto]*
* `--output-formats, --empty-output-formats`: List of output formats to generate.  *[choices: json, yaml, table, csv]*  *[default: [json]]*
* `--dry-run, --no-dry-run`: If True, simulate execution without making changes.  *[default: False]*

### complex-cli data validate

```console
complex-cli data validate [OPTIONS] INPUT_PATH
```

Validate data files against schema.

**Arguments**:

* `INPUT_PATH`: Path to validate.  **[required]**

**Parameters**:

* `--strict, --no-strict`: Enable strict validation mode.  *[default: False]*
* `--schema-file`: Custom schema file (must exist).
* `--ignore-patterns, --empty-ignore-patterns`: Patterns to ignore during validation.

## complex-cli server

Server management commands.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

### complex-cli server start

```console
complex-cli server start [OPTIONS]
```

Start the server with configuration.

Demonstrates Pydantic model support for CLI parameters.

**Parameters**:

* `--server.host`: Server bind address.  *[default: 0.0.0.0]*
* `--server.port`: Server port number.  *[default: 8000]*
* `--server.workers`: Number of worker processes.  *[default: 4]*
* `--server.timeout`: Request timeout in seconds.  *[default: 30.0]*
* `--server.debug, --server.no-debug`: Enable debug mode.  *[default: False]*
* `--auth.provider`: Authentication provider type.  *[choices: oauth2, jwt, basic, none]*  *[default: jwt]*
* `--auth.token-expiry`: Token expiration time in seconds.  *[default: 3600]*
* `--auth.refresh-enabled, --auth.no-refresh-enabled`: Enable token refresh.  *[default: True]*
* `--auth.allowed-origins, --auth.empty-allowed-origins`: List of allowed CORS origins.

### complex-cli server stop

```console
complex-cli server stop [OPTIONS]
```

Stop the server.

**Parameters**:

* `--graceful, --no-graceful`: Perform graceful shutdown.  *[default: True]*
* `--timeout`: Shutdown timeout in seconds.  *[default: 30]*
* `--force, --no-force, -f`: Force immediate shutdown.  *[default: False]*

### complex-cli server restart

```console
complex-cli server restart [ARGS]
```

Restart the server.

**Parameters**:

* `ROLLING, --rolling, --no-rolling`: Perform rolling restart (zero downtime).  *[default: False]*
* `DELAY, --delay`: Delay between worker restarts in seconds.  *[default: 5]*

## complex-cli cache

Cache management commands.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

### complex-cli cache configure

```console
complex-cli cache configure [OPTIONS]
```

Configure cache settings.

Demonstrates attrs class support for CLI parameters.

**Parameters**:

* `--config.backend`: Cache backend type.  *[choices: memory, redis, memcached, disk]*  *[default: memory]*
* `--config.ttl`: Time-to-live in seconds.  *[default: 300]*
* `--config.max-size`: Maximum cache size in MB.  *[default: 1024]*
* `--config.compression, --config.no-compression`: Enable compression.  *[default: False]*

### complex-cli cache clear

```console
complex-cli cache clear [ARGS]
```

Clear cache entries.

**Parameters**:

* `PATTERN, --pattern`: Pattern to match cache keys.  *[default: *]*
* `DRY-RUN, --dry-run, --no-dry-run`: Show what would be cleared without actually clearing.  *[default: False]*

### complex-cli cache stats

```console
complex-cli cache stats [ARGS]
```

Show cache statistics.

**Parameters**:

* `DETAILED, --detailed, --no-detailed`: Show detailed statistics.  *[default: False]*
* `FORMAT, --format`: Output format.  *[choices: json, yaml, table, csv]*  *[default: table]*

## complex-cli complex-types

```console
complex-cli complex-types [ARGS]
```

Demonstrate complex type annotations.

This command showcases various complex type patterns that the
documentation system needs to handle correctly.

**Parameters**:

* `WORKER-COUNT, --worker-count`: Number of workers or "auto" for automatic detection.  *[choices: auto]*  *[default: auto]*
* `QUALITY, --quality`: Quality preset or "custom" for manual configuration.  *[choices: low, medium, high, custom]*  *[default: medium]*
* `TAGS, --tags, --empty-tags`: Optional list of tags.
* `FORMATS, --formats, --empty-formats`: List of output formats.  *[choices: json, yaml, table, csv]*  *[default: [json]]*
* `THRESHOLDS, --thresholds, --empty-thresholds`: Threshold values or "default" for defaults.  *[choices: default]*  *[default: default]*
* `CONFIG-PATH, --config-path`: Optional config file path (must exist if provided).

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

## complex-cli numpy-style

```console
complex-cli numpy-style NAME [ARGS]
```

Command with NumPy-style docstring.                                                                                     

This command demonstrates NumPy docstring format which is the default for cyclopts.

Examples

                                                                                                                        
     >>> numpy_style("test", count=5)

**Parameters**:

* `NAME, --name`: The name parameter.  **[required]**
* `COUNT, --count`: The count parameter, by default 1.  *[default: 1]*

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

## complex-cli google-style

```console
complex-cli google-style NAME [ARGS]
```

Command with Google-style docstring.                                                                                    

This command demonstrates Google docstring format.

Examples

                                                                                                                        
     >>> google_style("test", count=5)

**Parameters**:

* `NAME, --name`: The name parameter.  **[required]**
* `COUNT, --count`: The count parameter. Defaults to 1.  *[default: 1]*

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

## complex-cli sphinx-style

```console
complex-cli sphinx-style NAME [ARGS]
```

Command with Sphinx-style docstring.

This command demonstrates Sphinx/reST docstring format.

**Parameters**:

* `NAME, --name`: The name parameter.  **[required]**
* `COUNT, --count`: The count parameter.  *[default: 1]*

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

## complex-cli secret-feature

```console
complex-cli secret-feature [ARGS]
```

Secret feature command.

This command has a hidden parameter.

**Parameters**:

* `ENABLE, --enable, --no-enable`: Enable the secret feature.  *[default: False]*

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*
