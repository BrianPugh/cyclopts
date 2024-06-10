from pathlib import Path
from typing import Any, Dict

from cyclopts.config._common import ConfigFromFile


class Yaml(ConfigFromFile):
    def _load_config(self, path: Path) -> Dict[str, Any]:
        from yaml import safe_load  # pyright: ignore[reportMissingImports]

        with path.open() as f:
            return safe_load(f)
