import errno
import itertools
import os
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from contextlib import suppress
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Sequence, Union

from attrs import define, field

from cyclopts.argument import ArgumentCollection
from cyclopts.exceptions import CycloptsError, UnknownOptionError
from cyclopts.token import Token
from cyclopts.utils import is_iterable, to_tuple_converter

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


def _meta_arguments(apps: Sequence["App"]) -> ArgumentCollection:
    argument_collection = ArgumentCollection()
    for i, app in enumerate(apps):
        if app._meta is None:
            continue
        argument_collection.extend(app._meta.assemble_argument_collection(apps=apps[:i]))
    return argument_collection


class CacheKey:
    """Abstraction to quickly check if a file needs to be read again.

    If a newly instantiated ``CacheKey`` doesn't equal a previously instantiated ``CacheKey``,
    then the file needs to be re-read.
    """

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path).absolute()
        if self.path.exists():
            stat = self.path.stat()
            self._mtime = stat.st_mtime
            self._size = stat.st_size
        else:
            self._mtime = None
            self._size = None

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return self._mtime == other._mtime and self._size == other._size and self.path == other.path


def to_cli_option_name(*keys: str) -> str:
    return "--" + ".".join(keys)


def update_argument_collection(
    config: dict,
    source: str,
    arguments: ArgumentCollection,
    apps: Optional[Sequence["App"]] = None,
    *,
    root_keys: Iterable[str],
    allow_unknown: bool,
):
    """Updates an argument collection if it doesn't already have tokens.

    Note: it feels bad that we're passing in ``apps`` here.
    """
    meta_arguments = _meta_arguments(apps or ())

    do_not_update = {}

    for option_key, option_value in config.items():
        for subkeys, value in _walk_leaves(option_value):
            cli_option_name = to_cli_option_name(option_key, *subkeys)
            complete_keyword = "".join(f"[{k}]" for k in itertools.chain(root_keys, (option_key,), subkeys))

            try:
                meta_arguments.match(cli_option_name)
            except ValueError:
                pass
            else:
                continue

            try:
                argument, remaining_keys, _ = arguments.match(cli_option_name)
            except ValueError:
                if allow_unknown:
                    continue
                if apps and apps[-1]._meta_parent:
                    # We're currently in the meta-app portion of the launch process,
                    # so MOST supplied options will be unmatched, as we haven't gotten
                    # to the actual command processing yet.
                    continue
                raise UnknownOptionError(
                    token=Token(keyword=complete_keyword, source=source), argument_collection=arguments
                ) from None

            if do_not_update.setdefault(id(argument), bool(argument.tokens)):
                # If this argument already has tokens on **first** access, then skip it.
                # Allows us to add multiple tokens to an argument from a **single** source (config file).
                continue

            # Convert all values to strings, so that the Cyclopts engine can process them.
            # This may (eventually) result in converting back to the original dtype.
            if not is_iterable(value):
                value = (value,)
            for i, v in enumerate(value):
                # TODO: is this index correct? If the source value is a list, it should probably be different
                if v is None:
                    # Pass ``None`` as an implicit_value so it certainly gets interpreted as ``None`` later.
                    token = Token(
                        keyword=complete_keyword, implicit_value=None, source=source, index=i, keys=remaining_keys
                    )
                else:
                    # Convert the value back into a string, so it can be re-converted.
                    token = Token(keyword=complete_keyword, value=str(v), source=source, index=i, keys=remaining_keys)
                argument.append(token)


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

    _config_cache_key: Optional[CacheKey] = field(default=None, init=False, repr=False)
    "Conditions under which ``_config`` was loaded."

    @abstractmethod
    def _load_config(self, path: Path) -> dict[str, Any]:
        """Load the config dictionary from path.

        Do **not** do any downstream caching; ``ConfigFromFile`` handles caching.

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
        assert isinstance(self.path, Path)
        for parent in self.path.parents:
            candidate = parent / self.path.name
            if candidate.exists():
                cache_key = CacheKey(candidate)
                if self._config_cache_key == cache_key:
                    return self._config or {}

                try:
                    self._config = self._load_config(candidate)
                    self._config_cache_key = cache_key
                except CycloptsError:
                    raise
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

    def __call__(self, apps: list["App"], commands: tuple[str, ...], arguments: ArgumentCollection):
        config: dict[str, Any] = self.config.copy()
        try:
            for key in chain(self.root_keys, commands if self.use_commands_as_keys else ()):
                config = config[key]
        except KeyError:
            return

        # Ignore keys that represent subcommands
        command_app = apps[-1] if self.use_commands_as_keys else apps[0]
        config = {k: v for k, v in config.items() if k not in command_app}

        assert isinstance(self.path, Path)
        source = str(self.path.absolute())

        update_argument_collection(
            config, source, arguments, apps, root_keys=self.root_keys, allow_unknown=self.allow_unknown
        )
