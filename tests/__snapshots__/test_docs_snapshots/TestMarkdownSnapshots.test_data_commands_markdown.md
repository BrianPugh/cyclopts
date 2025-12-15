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
