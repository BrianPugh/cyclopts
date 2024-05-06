from pathlib import Path
from typing import Any, Dict

from cyclopts.config._common import ConfigFromFile


class Json(ConfigFromFile):
    def _load_config(self, path: Path) -> Dict[str, Any]:
        import json

        with path.open() as f:
            return json.load(f)
