## complex-cli

Complex CLI application for comprehensive documentation testing.

```console
complex-cli COMMAND
```

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

**Subcommands**:

* `admin`: Administrative commands for system management.
* `data`: Data processing commands.
* `server`: Server management commands.

**Utilities**:

* `cache`: Cache management commands.
* `complex-types`: Demonstrate complex type annotations.
* `google-style`: Command with Google-style docstring.
* `info (i)`: Show application information.
* `numpy-style`: Command with NumPy-style docstring.
* `sphinx-style`: Command with Sphinx-style docstring.
* `version (ver, v)`: Show version information.

### complex-cli version

Show version information.

Displays the application version and system information.

```console
complex-cli version
```

### complex-cli info

Show application information.

```console
complex-cli info [ARGS]
```

### complex-cli debug-internal

Internal debug command (hidden from help).

This command is for internal debugging purposes only.

```console
complex-cli debug-internal
```

### complex-cli admin

Administrative commands for system management.

### complex-cli data

Data processing commands.

### complex-cli server

Server management commands.

### complex-cli cache

Cache management commands.

### complex-cli complex-types

Demonstrate complex type annotations.

This command showcases various complex type patterns that the
documentation system needs to handle correctly.

```console
complex-cli complex-types [ARGS]
```

### complex-cli numpy-style

Command with NumPy-style docstring.

This command demonstrates NumPy docstring format which is the
default for cyclopts.

```console
complex-cli numpy-style NAME [ARGS]
```

### complex-cli google-style

Command with Google-style docstring.

This command demonstrates Google docstring format.

```console
complex-cli google-style NAME [ARGS]
```

### complex-cli sphinx-style

Command with Sphinx-style docstring.

This command demonstrates Sphinx/reST docstring format.

```console
complex-cli sphinx-style NAME [ARGS]
```

### complex-cli internal-maintenance

Internal maintenance command.

This command is hidden from the main help but can still be invoked.

```console
complex-cli internal-maintenance
```

### complex-cli secret-feature

Secret feature command.

This command has a hidden parameter.

```console
complex-cli secret-feature [ARGS]
```
