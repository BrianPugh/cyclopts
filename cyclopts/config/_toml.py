from pathlib import Path
from typing import Any

from cyclopts.config._common import ConfigFromFile


class Toml(ConfigFromFile):
    def _load_config(self, path: Path) -> dict[str, Any]:
        import tomllib

        with path.open("rb") as f:
            return tomllib.load(f)
