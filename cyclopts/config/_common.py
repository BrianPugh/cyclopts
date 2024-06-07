import errno
import inspect
import os
from abc import ABC, abstractmethod
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Tuple, Union

from attrs import define, field

from cyclopts.exceptions import UnknownOptionError
from cyclopts.utils import to_tuple_converter

if TYPE_CHECKING:
    from cyclopts.core import App


@define
class Unset:
    """Placeholder object for an unset parameter.

    Used with :attr:`cyclopts.App.config`.

    Parameters
    ----------
    type_: Any
        The type annotation for the unset parameter.
    related: List[str]
        List of CLI names that map to the same :class:`inspect.Parameter`.
    """

    iparam: inspect.Parameter
    related: List[str] = field(factory=list)

    def related_set(self, bound: Dict[str, Union["Unset", List[str]]]) -> List[str]:
        out = []
        for name in self.related:
            with suppress(KeyError):
                if not isinstance(bound[name], Unset):
                    out.append(name)
        return out


@define
class ConfigFromFile(ABC):
    path: Union[str, Path] = field(converter=Path)
    root_keys: Iterable[str] = field(default=(), converter=to_tuple_converter)
    must_exist: bool = field(default=False, kw_only=True)
    search_parents: bool = field(default=False, kw_only=True)
    allow_unknown: bool = field(default=False, kw_only=True)

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

    def __call__(self, apps: List["App"], commands: Tuple[str, ...], bound: Dict[str, Union[Unset, List[str]]]):
        config = self.config
        try:
            for key in self.root_keys:
                config = config[key]
            for key in commands:
                config = config[key]
        except KeyError:
            return

        if not self.allow_unknown:
            remaining_config_keys = set(config)
            remaining_config_keys -= set(apps[-1])
            remaining_config_keys -= set(bound)
            if remaining_config_keys:
                raise UnknownOptionError(token=sorted(remaining_config_keys)[0])

        for key in bound:
            value = bound[key]

            # If a value is already parsed for this option, then skip
            # attempting to parse it from config file.
            if not isinstance(value, Unset) or value.related_set(bound):
                continue

            with suppress(KeyError):
                new_value = config[key]
                if not isinstance(new_value, list):
                    new_value = [new_value]
                bound[key] = [str(x) for x in new_value]
