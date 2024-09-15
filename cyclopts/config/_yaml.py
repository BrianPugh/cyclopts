from functools import lru_cache
from pathlib import Path
from typing import Any

from cyclopts.config._common import ConfigFromFile


@lru_cache(8)
def _load_yaml(path: Path):
    from yaml import safe_load  # pyright: ignore[reportMissingImports]

    with path.open() as f:
        return safe_load(f)


class Yaml(ConfigFromFile):
    def _load_config(self, path: Path) -> dict[str, Any]:
        return _load_yaml(path)
