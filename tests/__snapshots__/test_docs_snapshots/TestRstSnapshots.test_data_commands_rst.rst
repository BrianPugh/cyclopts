.. _cyclopts-complex-cli:

complex-cli
-----------

::

    complex-cli COMMAND

Complex CLI application for comprehensive documentation testing.

.. contents:: Table of Contents
   :local:
   :depth: 6

**Global Options:**

``--verbose, -v``
    Verbosity level (-v, -vv, -vvv). [Default: ``0``]

``--quiet, --no-quiet, -q``
    Suppress non-essential output. [Default: ``False``]

``--log-level``
    Logging level. [Choices: ``debug``, ``info``, ``warning``, ``error``, ``critical``, Default: ``info``]

``--no-color, --no-no-color``
    Disable colored output [Default: ``False``]

**Subcommands:**

``data``
    Data processing commands.

.. _cyclopts-complex-cli-data:

data
^^^^

Data processing commands.

**Commands:**

``pipeline``
    Run a complete data pipeline.

``process``
    Process data files with configurable options.

``validate``
    Validate data files against schema.

.. _cyclopts-complex-cli-data-process:

process
"""""""

::

    complex-cli data process [OPTIONS] INPUT_FILES

Process data files with configurable options.

This command demonstrates dataclass parameter flattening where
all fields from ProcessingConfig and PathConfig become CLI options.

**Arguments:**

``INPUT_FILES``
    Input files to process [**Required**]

**Parameters:**

``--batch-size``
    Number of items to process per batch. [Default: ``32``]

``--num-workers``
    Number of parallel workers. Use "auto" for automatic detection. [Choices: ``auto``, Default: ``auto``]

``--quality-level``
    Processing quality level. Higher values mean better quality but slower. [Choices: ``high``, ``medium``, ``low``, Default: ``high``]

``--device``
    Computing device to use. Can be "cuda", "cpu", "auto", or a GPU index. [Choices: ``cuda``, ``cpu``, ``auto``, Default: ``auto``]

``--output-formats, --empty-output-formats``
    List of output formats to generate. [Choices: ``json``, ``yaml``, ``table``, ``csv``, Default: ``[json]``]

``--input-dir``
    Input data directory. [Default: ``data/input``]

``--output-dir``
    Output results directory. [Default: ``data/output``]

``--cache-dir``
    Cache directory for intermediate files.

``--log-dir``
    Directory for log files. [Default: ``logs``]

.. _cyclopts-complex-cli-data-pipeline:

pipeline
""""""""

::

    complex-cli data pipeline [OPTIONS]

Run a complete data pipeline.

Demonstrates nested dataclass flattening (PipelineConfig contains
PathConfig and ProcessingConfig).

**Parameters:**

``--name``
    Pipeline name for identification. [Default: ``default-pipeline``]

``--input-dir``
    Input data directory. [Default: ``data/input``]

``--output-dir``
    Output results directory. [Default: ``data/output``]

``--cache-dir``
    Cache directory for intermediate files.

``--log-dir``
    Directory for log files. [Default: ``logs``]

``--batch-size``
    Number of items to process per batch. [Default: ``32``]

``--num-workers``
    Number of parallel workers. Use "auto" for automatic detection. [Choices: ``auto``, Default: ``auto``]

``--quality-level``
    Processing quality level. Higher values mean better quality but slower. [Choices: ``high``, ``medium``, ``low``, Default: ``high``]

``--device``
    Computing device to use. Can be "cuda", "cpu", "auto", or a GPU index. [Choices: ``cuda``, ``cpu``, ``auto``, Default: ``auto``]

``--output-formats, --empty-output-formats``
    List of output formats to generate. [Choices: ``json``, ``yaml``, ``table``, ``csv``, Default: ``[json]``]

``--dry-run, --no-dry-run``
    If True, simulate execution without making changes. [Default: ``False``]

.. _cyclopts-complex-cli-data-validate:

validate
""""""""

::

    complex-cli data validate [OPTIONS] INPUT_PATH

Validate data files against schema.

**Arguments:**

``INPUT_PATH``
    Path to validate. [**Required**]

**Parameters:**

``--strict, --no-strict``
    Enable strict validation mode. [Default: ``False``]

``--schema-file``
    Custom schema file (must exist).

``--ignore-patterns, --empty-ignore-patterns``
    Patterns to ignore during validation.
