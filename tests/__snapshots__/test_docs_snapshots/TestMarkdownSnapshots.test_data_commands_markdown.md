Data processing commands.

**Global Options**:

* `--verbose, -v`: Verbosity level (-v, -vv, -vvv). *[default: 0]*
* `--quiet, -q, --no-quiet`: Suppress non-essential output. *[default: False]*
* `--log-level`: Logging level. *[choices: debug, info, warning, error, critical]* *[default: info]*
* `--no-color, --no-no-color`: Disable colored output *[default: False]*

### complex-cli data process

```console
complex-cli data process [OPTIONS] INPUT_FILES
```

Process data files with configurable options.

This command demonstrates dataclass parameter flattening where
all fields from ProcessingConfig and PathConfig become CLI options.

**Arguments**:

* `INPUT_FILES`: Input files to process **[required]**

**Parameters**:

* `--batch-size INT`: Number of items to process per batch. *[default: 32]*
* `--num-workers INT`: Number of parallel workers. Use "auto" for automatic detection. *[choices: auto]* *[default: auto]*
* `--quality-level INT`: Processing quality level. Higher values mean better quality but slower. *[choices: high, medium, low]* *[default: high]*
* `--device INT`: Computing device to use. Can be "cuda", "cpu", "auto", or a GPU index. *[choices: cuda, cpu, auto]* *[default: auto]*
* `--output-formats, --empty-output-formats`: List of output formats to generate. *[choices: json, yaml, table, csv]* *[default: [json]]*
* `--input-dir PATH`: Input data directory. *[default: data/input]*
* `--output-dir PATH`: Output results directory. *[default: data/output]*
* `--cache-dir PATH`: Cache directory for intermediate files.
* `--log-dir PATH`: Directory for log files. *[default: logs]*

### complex-cli data pipeline

```console
complex-cli data pipeline [OPTIONS]
```

Run a complete data pipeline.

Demonstrates nested dataclass flattening (PipelineConfig contains
PathConfig and ProcessingConfig).

**Parameters**:

* `--name STR`: Pipeline name for identification. *[default: default-pipeline]*
* `--input-dir PATH`: Input data directory. *[default: data/input]*
* `--output-dir PATH`: Output results directory. *[default: data/output]*
* `--cache-dir PATH`: Cache directory for intermediate files.
* `--log-dir PATH`: Directory for log files. *[default: logs]*
* `--batch-size INT`: Number of items to process per batch. *[default: 32]*
* `--num-workers INT`: Number of parallel workers. Use "auto" for automatic detection. *[choices: auto]* *[default: auto]*
* `--quality-level INT`: Processing quality level. Higher values mean better quality but slower. *[choices: high, medium, low]* *[default: high]*
* `--device INT`: Computing device to use. Can be "cuda", "cpu", "auto", or a GPU index. *[choices: cuda, cpu, auto]* *[default: auto]*
* `--output-formats, --empty-output-formats`: List of output formats to generate. *[choices: json, yaml, table, csv]* *[default: [json]]*
* `--dry-run, --no-dry-run`: If True, simulate execution without making changes. *[default: False]*

### complex-cli data validate

```console
complex-cli data validate [OPTIONS] INPUT_PATH
```

Validate data files against schema.

**Arguments**:

* `INPUT_PATH`: Path to validate. **[required]**

**Parameters**:

* `--strict, --no-strict`: Enable strict validation mode. *[default: False]*
* `--schema-file PATH`: Custom schema file (must exist).
* `--ignore-patterns LIST[STR], --empty-ignore-patterns`: Patterns to ignore during validation.
