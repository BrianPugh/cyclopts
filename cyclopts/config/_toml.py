from functools import lru_cache
from pathlib import Path
from typing import Any

from cyclopts.config._common import ConfigFromFile


@lru_cache(8)
def _load_toml(path: Path):
    try:
        # Attempt to use builtin >=python3.11
        import tomllib  # pyright: ignore[reportMissingImports]
    except ImportError:
        # Fallback to most popular pypi toml package.
        import tomli as tomllib  # pyright: ignore[reportMissingImports]

    with path.open("rb") as f:
        return tomllib.load(f)


class Toml(ConfigFromFile):
    def _load_config(self, path: Path) -> dict[str, Any]:
        return _load_toml(path)
