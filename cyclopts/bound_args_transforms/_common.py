import errno
import os
from abc import ABC, abstractmethod
from inspect import BoundArguments
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple, Union

from attrs import define, field

from cyclopts.utils import to_tuple_converter


@define
class ConfigFromFile(ABC):
    path: Union[str, Path] = field(converter=Path)
    root_keys: Iterable[str] = field(default=(), converter=to_tuple_converter)
    must_exist: bool = field(default=False, kw_only=True)
    search_parents: bool = field(default=False, kw_only=True)

    _config: Optional[Dict[str, Any]] = field(default=None, init=False, repr=False)

    @abstractmethod
    def _load_config(self, path: Path) -> Dict[str, Any]:
        raise NotImplementedError

    @property
    def config(self) -> Dict[str, Any]:
        if self._config is not None:
            return self._config

        assert isinstance(self.path, Path)
        for parent in self.path.parents:
            candidate = parent / self.path.name
            if candidate.exists():
                break
            elif not self.search_parents:
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(candidate))
        else:
            if self.must_exist:
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(self.path))
            else:
                self._config = {}
                return self._config

        self._config = self._load_config(candidate)
        return self._config

    def __call__(self, commands: Tuple[str, ...], bound: BoundArguments):
        config = self.config
        for key in self.root_keys:
            config = config.get(key, {})
        for key in commands:
            config = config.get(key, {})
        for key, value in config.items():
            bound.arguments.setdefault(key, value)
