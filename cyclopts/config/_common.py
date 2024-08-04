import errno
import inspect
import itertools
import os
from abc import ABC, abstractmethod
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Set, Tuple, Union

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
        config = self.config
        try:
            for key in chain(self.root_keys, commands):
                config = config[key]
        except KeyError:
            return

        argument_names = {name[2:] for name in arguments.names if name.startswith("--")}
        if (
            not arguments.var_keyword
            and not self.allow_unknown
            and (remaining_keys := set(config) - set(apps[-1]) - argument_names)
        ):
            raise UnknownOptionError(token=sorted(remaining_keys)[0])

        for argument in arguments:
            if argument.tokens:
                continue
            # TODO: this direction doesn't work with VAR_KEYWORD
            for name in argument.names:
                if not name.startswith("--"):
                    continue
                name_tokens = name[2:].split(".")
                lookup = config

                try:
                    for name_token in name_tokens:
                        lookup = lookup[name_token]
                except KeyError:
                    continue

                if isinstance(lookup, dict):
                    raise NotImplementedError  # TODO
                elif not isinstance(lookup, list):
                    lookup = [lookup]
                lookup = [str(x) for x in lookup]

                complete_keyword = "".join(f"[{k}]" for k in itertools.chain(self.root_keys, name_tokens))

                for i, value in enumerate(lookup):
                    argument.append(Token(complete_keyword, value, source=str(self.path), index=i))
