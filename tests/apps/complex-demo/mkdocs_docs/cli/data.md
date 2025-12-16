# Data Processing Commands

Data processing commands that demonstrate **dataclass parameter flattening**.

When using `@Parameter(name="*")` on a dataclass, all its fields become
individual CLI options. This page shows how this appears in documentation.

## Data Commands

::: cyclopts
    module: complex_app:app
    heading_level: 3
    recursive: true
    commands: [data]
    generate_toc: false

## Understanding Dataclass Flattening

The `process` command accepts two dataclass parameters:

- `ProcessingConfig` - Controls batch size, workers, quality, device, etc.
- `PathConfig` - Controls input/output directories

Instead of requiring complex nested syntax, these become flat CLI options:

```console
$ complex-cli data process file1.txt file2.txt \
    --batch-size 64 \
    --num-workers auto \
    --quality-level high \
    --input-dir ./input \
    --output-dir ./output
```

## Nested Dataclasses

The `pipeline` command demonstrates **nested dataclass flattening** where
`PipelineConfig` contains both `PathConfig` and `ProcessingConfig`.
