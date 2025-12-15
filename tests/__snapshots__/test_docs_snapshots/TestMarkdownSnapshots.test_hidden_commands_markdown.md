## complex-cli

```console
complex-cli COMMAND
```

Complex CLI application for comprehensive documentation testing.

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

### complex-cli version

```console
complex-cli version
```

Show version information.

Displays the application version and system information.

### complex-cli info

```console
complex-cli info [ARGS]
```

Show application information.

### complex-cli debug-internal

```console
complex-cli debug-internal
```

Internal debug command (hidden from help).

This command is for internal debugging purposes only.

### complex-cli admin

Administrative commands for system management.

### complex-cli data

Data processing commands.

### complex-cli server

Server management commands.

### complex-cli cache

Cache management commands.

### complex-cli complex-types

```console
complex-cli complex-types [ARGS]
```

Demonstrate complex type annotations.

This command showcases various complex type patterns that the
documentation system needs to handle correctly.

### complex-cli numpy-style

```console
complex-cli numpy-style NAME [ARGS]
```

Command with NumPy-style docstring.

This command demonstrates NumPy docstring format which is the
default for cyclopts.

### complex-cli google-style

```console
complex-cli google-style NAME [ARGS]
```

Command with Google-style docstring.

This command demonstrates Google docstring format.

### complex-cli sphinx-style

```console
complex-cli sphinx-style NAME [ARGS]
```

Command with Sphinx-style docstring.

This command demonstrates Sphinx/reST docstring format.

### complex-cli internal-maintenance

```console
complex-cli internal-maintenance
```

Internal maintenance command.

This command is hidden from the main help but can still be invoked.

### complex-cli secret-feature

```console
complex-cli secret-feature [ARGS]
```

Secret feature command.

This command has a hidden parameter.
