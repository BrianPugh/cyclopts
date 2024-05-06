from pathlib import Path
from typing import Any, Dict

from cyclopts.config._common import ConfigFromFile


class Toml(ConfigFromFile):
    def _load_config(self, path: Path) -> Dict[str, Any]:
        try:
            import tomllib

            with path.open("rb") as f:
                return tomllib.load(f)
        except ImportError:
            import toml  # pyright: ignore[reportMissingModuleSource]

            with path.open() as f:
                return toml.load(f)
