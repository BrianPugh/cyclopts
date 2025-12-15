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

**Utilities**:

* `cache`: Cache management commands.
* `complex-types`: Demonstrate complex type annotations.
* `info (i)`: Show application information.
* `version (ver, v)`: Show version information.

### complex-cli version

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

### complex-cli info

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

### complex-cli cache

Cache management commands.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

#### complex-cli cache configure

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

#### complex-cli cache clear

```console
complex-cli cache clear [ARGS]
```

Clear cache entries.

**Parameters**:

* `PATTERN, --pattern`: Pattern to match cache keys.  *[default: *]*
* `DRY-RUN, --dry-run, --no-dry-run`: Show what would be cleared without actually clearing.  *[default: False]*

#### complex-cli cache stats

```console
complex-cli cache stats [ARGS]
```

Show cache statistics.

**Parameters**:

* `DETAILED, --detailed, --no-detailed`: Show detailed statistics.  *[default: False]*
* `FORMAT, --format`: Output format.  *[choices: json, yaml, table, csv]*  *[default: table]*

### complex-cli complex-types

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
