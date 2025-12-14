# CLI Reference

## Data Commands

Data processing commands.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

### complex-cli data process

Process data files with configurable options.

This command demonstrates dataclass parameter flattening where
all fields from ProcessingConfig and PathConfig become CLI options.

```console
complex-cli data process [OPTIONS] INPUT_FILES
```

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

Run a complete data pipeline.

Demonstrates nested dataclass flattening (PipelineConfig contains
PathConfig and ProcessingConfig).

```console
complex-cli data pipeline [OPTIONS]
```

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

Validate data files against schema.

```console
complex-cli data validate [OPTIONS] INPUT_PATH
```

**Arguments**:

* `INPUT_PATH`: Path to validate.  **[required]**

**Parameters**:

* `--strict, --no-strict`: Enable strict validation mode.  *[default: False]*
* `--schema-file`: Custom schema file (must exist).
* `--ignore-patterns, --empty-ignore-patterns`: Patterns to ignore during validation.

## Server Commands

Server management commands.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv).  *[default: 0]*
* `--quiet, --no-quiet, -q`: Suppress non-essential output.  *[default: False]*
* `--log-level`: Logging level.  *[choices: debug, info, warning, error, critical]*  *[default: info]*
* `--no-color, --no-no-color`: Disable colored output  *[default: False]*

### complex-cli server start

Start the server with configuration.

Demonstrates Pydantic model support for CLI parameters.

```console
complex-cli server start [OPTIONS]
```

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

Stop the server.

```console
complex-cli server stop [OPTIONS]
```

**Parameters**:

* `--graceful, --no-graceful`: Perform graceful shutdown.  *[default: True]*
* `--timeout`: Shutdown timeout in seconds.  *[default: 30]*
* `--force, --no-force, -f`: Force immediate shutdown.  *[default: False]*

### complex-cli server restart

Restart the server.

```console
complex-cli server restart [ARGS]
```

**Parameters**:

* `ROLLING, --rolling, --no-rolling`: Perform rolling restart (zero downtime).  *[default: False]*
* `DELAY, --delay`: Delay between worker restarts in seconds.  *[default: 5]*
