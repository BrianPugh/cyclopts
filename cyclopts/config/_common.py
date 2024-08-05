import errno
import inspect
import itertools
import os
from abc import ABC, abstractmethod
from itertools import chain
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from attrs import define, field

from cyclopts.argument import Token
from cyclopts.exceptions import UnknownOptionError
from cyclopts.utils import to_tuple_converter

if TYPE_CHECKING:
    from cyclopts.argument import ArgumentCollection
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


def _walk_leaves(
    d,
    parent_keys: Optional[Tuple[str, ...]] = None,
) -> Iterator[Tuple[Tuple[str, ...], Any]]:
    if parent_keys is None:
        parent_keys = ()

    if isinstance(d, dict):
        for key, value in d.items():
            current_keys = parent_keys + (key,)
            if isinstance(value, dict):
                yield from _walk_leaves(value, current_keys)
            else:
                yield current_keys, value
    else:
        yield (), d


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

    def __call__(self, apps: List["App"], commands: Tuple[str, ...], arguments: "ArgumentCollection"):
        config: Dict[str, Any] = self.config
        try:
            for key in chain(self.root_keys, commands):
                config = config[key]
        except KeyError:
            return

        for option_key, option_value in config.items():
            if option_key in apps[-1]:  # Check if it's a command.
                continue

            for subkeys, value in _walk_leaves(option_value):
                cli_option_name = "--" + ".".join(chain((option_key,), subkeys))
                complete_keyword = "".join(f"[{k}]" for k in itertools.chain(self.root_keys, (option_key,), subkeys))

                try:
                    argument, remaining_keys, _ = arguments.match(cli_option_name)
                except ValueError:
                    if self.allow_unknown:
                        continue
                    else:
                        raise UnknownOptionError(token=complete_keyword) from None

                if argument.tokens:
                    continue

                if not isinstance(value, list):
                    value = (value,)
                value = tuple(str(x) for x in value)

                for i, v in enumerate(value):
                    argument.append(Token(complete_keyword, v, source=str(self.path), index=i, keys=remaining_keys))
