# Lazy Loading Demo

Demonstrates Cyclopts lazy loading to improve CLI startup time.

## The Problem

CLIs with many commands often have expensive imports (ML libraries, ORMs, etc.).
Eager loading imports everything at startup, even for `--help`:
This demo uses `time.sleep` to simulate expensive imports.

```bash
time python main_eager.py --help  # ~4.5s - imports ALL modules first
```

## The Solution

Lazy loading defers imports until a command actually runs:

```bash
time python main_lazy.py --help           # ~0.1s - no imports
time python main_lazy.py user --help      # ~0.1s - docstrings via AST
time python main_lazy.py user create a b  # ~1s   - only users.py imported
time python main_lazy.py ml train resnet  # ~2s   - only ml.py imported
```
