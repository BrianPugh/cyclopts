from functools import lru_cache
from pathlib import Path
from typing import Any

from cyclopts.config._common import ConfigFromFile


@lru_cache(8)
def _load_json(path: Path):
    import json

    with path.open() as f:
        return json.load(f)


class Json(ConfigFromFile):
    def _load_config(self, path: Path) -> dict[str, Any]:
        return _load_json(path)
