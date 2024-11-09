import errno
import itertools
import os
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from contextlib import suppress
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union

from attrs import define, field

from cyclopts.argument import ArgumentCollection
from cyclopts.exceptions import CycloptsError, UnknownOptionError
from cyclopts.token import Token
from cyclopts.utils import to_tuple_converter

if TYPE_CHECKING:
    from cyclopts.core import App


def _walk_leaves(
    d,
    parent_keys: Optional[tuple[str, ...]] = None,
) -> Iterator[tuple[tuple[str, ...], Any]]:
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


def _meta_arguments(apps: list["App"]) -> "ArgumentCollection":
    argument_collection = ArgumentCollection()
    for i, app in enumerate(apps):
        if app._meta is None:
            continue
        argument_collection.extend(app._meta.assemble_argument_collection(apps=apps[:i]))
    return argument_collection


@define
class ConfigFromFile(ABC):
    path: Union[str, Path] = field(converter=Path)

    root_keys: Iterable[str] = field(default=(), converter=to_tuple_converter)
    must_exist: bool = field(default=False, kw_only=True)
    search_parents: bool = field(default=False, kw_only=True)
    allow_unknown: bool = field(default=False, kw_only=True)
    use_commands_as_keys: bool = field(default=True, kw_only=True)

    _config: Optional[dict[str, Any]] = field(default=None, init=False, repr=False)
    "Loaded configuration structure (to be loaded by subclassed ``_load_config`` method)."

    @abstractmethod
    def _load_config(self, path: Path) -> dict[str, Any]:
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
    def config(self) -> dict[str, Any]:
        if self._config is not None:
            return self._config

        assert isinstance(self.path, Path)
        for parent in self.path.parents:
            candidate = parent / self.path.name
            if candidate.exists():
                try:
                    self._config = self._load_config(candidate)
                except Exception as e:
                    msg = getattr(type(e), "__name__", "")
                    with suppress(IndexError):
                        exception_msg = e.args[0]
                        if msg:
                            msg += ": "
                        msg += exception_msg
                    raise CycloptsError(msg=msg) from e
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

    @property
    def source(self) -> str:
        return str(self.path)

    def __call__(self, apps: list["App"], commands: tuple[str, ...], arguments: "ArgumentCollection"):
        config: dict[str, Any] = self.config
        try:
            for key in chain(self.root_keys, commands if self.use_commands_as_keys else ()):
                config = config[key]
        except KeyError:
            return

        to_add = []
        for option_key, option_value in config.items():
            if self.use_commands_as_keys:
                if option_key in apps[-1]:  # Check if it's a command.
                    continue
            else:
                if option_key in apps[0]:
                    continue

            for subkeys, value in _walk_leaves(option_value):
                cli_option_name = "--" + ".".join(chain((option_key,), subkeys))
                complete_keyword = "".join(f"[{k}]" for k in itertools.chain(self.root_keys, (option_key,), subkeys))

                try:
                    argument, remaining_keys, _ = arguments.match(cli_option_name)
                except ValueError:
                    if self.allow_unknown or apps[-1]._meta_parent:
                        continue
                    else:
                        meta_arguments = _meta_arguments(apps)
                        try:
                            meta_arguments.match(cli_option_name)
                        except ValueError:
                            raise UnknownOptionError(
                                token=Token(keyword=complete_keyword, source=self.source), argument_collection=arguments
                            ) from None
                        else:
                            continue

                if argument.tokens or argument.field_info.kind is argument.field_info.VAR_KEYWORD:
                    continue

                if any(x.source != str(self.path) for x in argument.tokens):
                    continue

                if not isinstance(value, list):
                    value = (value,)
                value = tuple(str(x) for x in value)

                for i, v in enumerate(value):
                    to_add.append(
                        (
                            argument,
                            Token(keyword=complete_keyword, value=v, source=self.source, index=i, keys=remaining_keys),
                        )
                    )

        for argument, token in to_add:
            argument.append(token)
