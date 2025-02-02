from pathlib import Path
from typing import Any

from cyclopts.config._common import ConfigFromFile


class Json(ConfigFromFile):
    def _load_config(self, path: Path) -> dict[str, Any]:
        import json

        with path.open() as f:
            return json.load(f)
