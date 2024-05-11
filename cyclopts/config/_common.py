import errno
import os
from abc import ABC, abstractmethod
from contextlib import suppress
from inspect import BoundArguments
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Tuple, Union

from attrs import define, field

from cyclopts.utils import to_tuple_converter

if TYPE_CHECKING:
    from cyclopts.core import App


@define
class ConfigFromFile(ABC):
    path: Union[str, Path] = field(converter=Path)
    root_keys: Iterable[str] = field(default=(), converter=to_tuple_converter)
    must_exist: bool = field(default=False, kw_only=True)
    search_parents: bool = field(default=False, kw_only=True)

    _config: Optional[Dict[str, Any]] = field(default=None, init=False, repr=False)

    @abstractmethod
    def _load_config(self, path: Path) -> Dict[str, Any]:
        """Load the config dictionary from path.

        The ``path`` is guaranteed to exist.
        """
        raise NotImplementedError

    @property
    def config(self) -> Dict[str, Any]:
        if self._config is not None:
            return self._config

        assert isinstance(self.path, Path)
        for parent in self.path.parents:
            candidate = parent / self.path.name
            if candidate.exists():
                self._config = self._load_config(candidate)
                return self._config
            elif self.search_parents:
                # Continue iterating over parents.
                continue
            elif self.must_exist:
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(self.path))

        # No matching file was found.
        if self.must_exist:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(self.path))

        self._config = {}
        return self._config

    def __call__(self, apps: List["App"], commands: Tuple[str, ...], bound: Dict[str, Any]):
        config = self.config
        with suppress(KeyError):
            for key in self.root_keys:
                config = config[key]
            for key in commands:
                config = config[key]
            for key, value in config.items():
                if key not in apps[-1]:
                    bound.setdefault(key, value)
