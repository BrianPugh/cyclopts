import errno
import inspect
import os
from abc import ABC, abstractmethod
from contextlib import suppress
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Set, Tuple, Union

from attrs import define, field

from cyclopts.exceptions import UnknownOptionError
from cyclopts.utils import to_tuple_converter

if TYPE_CHECKING:
    from cyclopts.core import App


@define
class Unset:
    """Placeholder object for a parameter that does not yet have any associated string tokens.

    Used with :attr:`App.config <cyclopts.App.config>`.

    Parameters
    ----------
    iparam: inspect.Parameter
        The corresponding :class:`inspect.Parameter` for the unset variable.
    related: set[str]
        Other CLI names that map to the same :class:`inspect.Parameter`.
        These may be aliases, or things like negative flags.
    """

    iparam: inspect.Parameter
    related: Set[str] = field(factory=set)

    def related_set(self, mapping: Dict[str, Union["Unset", List[str]]]) -> Set[str]:
        """Other CLI keys that map to the same :class:`inspect.Parameter` that have parsed token(s).

        Parameters
        ----------
        mapping: dict
            All associated cli_name to tokens.

        Returns
        -------
        set[str]
            CLI keys that map to the same :class:`inspect.Parameter` that have parsed token(s).
        """
        return {x for x in self.related.intersection(mapping) if not isinstance(mapping[x], Unset)}


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

        Parameters
        ----------
        path: Path
            Path to the file. Guaranteed to exist.

        Returns
        -------
        dict
            Loaded configuration.
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

    def __call__(self, apps: List["App"], commands: Tuple[str, ...], mapping: Dict[str, Union[Unset, List[str]]]):
        config = self.config
        try:
            for key in chain(self.root_keys, commands):
                config = config[key]
        except KeyError:
            return

        if not self.allow_unknown and (remaining_keys := set(config) - set(apps[-1]) - set(mapping)):
            raise UnknownOptionError(token=sorted(remaining_keys)[0])

        for key, value in mapping.items():
            if not isinstance(value, Unset) or value.related_set(mapping):
                continue

            with suppress(KeyError):
                new_value = config[key]
                if not isinstance(new_value, list):
                    new_value = [new_value]
                mapping[key] = [str(x) for x in new_value]
