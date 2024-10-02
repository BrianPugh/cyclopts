import functools
import inspect
import sys
from collections.abc import Iterable, Iterator, MutableMapping
from typing import Any, Literal, Optional, Sequence, Tuple, Union

# fmt: off
if sys.version_info >= (3, 10):
    def signature(f: Any) -> inspect.Signature:
        return inspect.signature(f, eval_str=True)
else:
    def signature(f: Any) -> inspect.Signature:
        return inspect.signature(f)
# fmt: on

if sys.version_info >= (3, 10):
    from sys import stdlib_module_names
else:
    # Copied from python3.11 sys.stdlib_module_names
    stdlib_module_names = frozenset(
        {
            "abc",
            "aifc",
            "antigravity",
            "argparse",
            "array",
            "ast",
            "asynchat",
            "asyncio",
            "asyncore",
            "atexit",
            "audioop",
            "base64",
            "bdb",
            "binascii",
            "bisect",
            "builtins",
            "bz2",
            "cProfile",
            "calendar",
            "cgi",
            "cgitb",
            "chunk",
            "cmath",
            "cmd",
            "code",
            "codecs",
            "codeop",
            "collections",
            "colorsys",
            "compileall",
            "concurrent",
            "configparser",
            "contextlib",
            "contextvars",
            "copy",
            "copyreg",
            "crypt",
            "csv",
            "ctypes",
            "curses",
            "dataclasses",
            "datetime",
            "dbm",
            "decimal",
            "difflib",
            "dis",
            "distutils",
            "doctest",
            "email",
            "encodings",
            "ensurepip",
            "enum",
            "errno",
            "faulthandler",
            "fcntl",
            "filecmp",
            "fileinput",
            "fnmatch",
            "fractions",
            "ftplib",
            "functools",
            "gc",
            "genericpath",
            "getopt",
            "getpass",
            "gettext",
            "glob",
            "graphlib",
            "grp",
            "gzip",
            "hashlib",
            "heapq",
            "hmac",
            "html",
            "http",
            "idlelib",
            "imaplib",
            "imghdr",
            "imp",
            "importlib",
            "inspect",
            "io",
            "ipaddress",
            "itertools",
            "json",
            "keyword",
            "lib2to3",
            "linecache",
            "locale",
            "logging",
            "lzma",
            "mailbox",
            "mailcap",
            "marshal",
            "math",
            "mimetypes",
            "mmap",
            "modulefinder",
            "msilib",
            "msvcrt",
            "multiprocessing",
            "netrc",
            "nis",
            "nntplib",
            "nt",
            "ntpath",
            "nturl2path",
            "numbers",
            "opcode",
            "operator",
            "optparse",
            "os",
            "ossaudiodev",
            "pathlib",
            "pdb",
            "pickle",
            "pickletools",
            "pipes",
            "pkgutil",
            "platform",
            "plistlib",
            "poplib",
            "posix",
            "posixpath",
            "pprint",
            "profile",
            "pstats",
            "pty",
            "pwd",
            "py_compile",
            "pyclbr",
            "pydoc",
            "pydoc_data",
            "pyexpat",
            "queue",
            "quopri",
            "random",
            "re",
            "readline",
            "reprlib",
            "resource",
            "rlcompleter",
            "runpy",
            "sched",
            "secrets",
            "select",
            "selectors",
            "shelve",
            "shlex",
            "shutil",
            "signal",
            "site",
            "smtpd",
            "smtplib",
            "sndhdr",
            "socket",
            "socketserver",
            "spwd",
            "sqlite3",
            "sre_compile",
            "sre_constants",
            "sre_parse",
            "ssl",
            "stat",
            "statistics",
            "string",
            "stringprep",
            "struct",
            "subprocess",
            "sunau",
            "symtable",
            "sys",
            "sysconfig",
            "syslog",
            "tabnanny",
            "tarfile",
            "telnetlib",
            "tempfile",
            "termios",
            "textwrap",
            "this",
            "threading",
            "time",
            "timeit",
            "tkinter",
            "token",
            "tokenize",
            "tomllib",
            "trace",
            "traceback",
            "tracemalloc",
            "tty",
            "turtle",
            "turtledemo",
            "types",
            "typing",
            "unicodedata",
            "unittest",
            "urllib",
            "uu",
            "uuid",
            "venv",
            "warnings",
            "wave",
            "weakref",
            "webbrowser",
            "winreg",
            "winsound",
            "wsgiref",
            "xdrlib",
            "xml",
            "xmlrpc",
            "zipapp",
            "zipfile",
            "zipimport",
            "zlib",
            "zoneinfo",
        }
    )


class SentinelMeta(type):
    def __repr__(cls) -> str:
        return f"<{cls.__name__}>"

    def __bool__(cls) -> Literal[False]:
        return False


class Sentinel(metaclass=SentinelMeta):
    pass


class UNSET(Sentinel):
    """No data was provided."""


def record_init(target: str):
    """Class decorator that records init argument names as a tuple to ``target``."""

    def decorator(cls):
        original_init = cls.__init__
        function_signature = signature(original_init)

        @functools.wraps(original_init)
        def new_init(self, *args, **kwargs):
            bound = function_signature.bind(self, *args, **kwargs)
            original_init(self, *args, **kwargs)
            # Circumvent frozen protection.
            object.__setattr__(self, target, tuple(k for k, v in bound.arguments.items() if v is not self))

        cls.__init__ = new_init
        return cls

    return decorator


class ParameterDict(MutableMapping):
    """A dictionary implementation that can handle mutable ``inspect.Parameter`` as keys."""

    def __init__(self, store: Optional[dict[inspect.Parameter, Any]] = None):
        self.store = {}
        self.reverse_mapping = {}
        if store is not None:
            for k, v in store.items():
                self[k] = v

    def _param_key(self, param: inspect.Parameter) -> tuple:
        if not isinstance(param, inspect.Parameter):
            raise TypeError(f"Key must be an inspect.Parameter; got {type(param)}.")
        return (param.name, param.kind, param.annotation)

    def __getitem__(self, key: inspect.Parameter) -> Any:
        return self.store[self._param_key(key)]

    def __setitem__(self, key: inspect.Parameter, value: Any) -> None:
        processed_key = self._param_key(key)
        self.store[processed_key] = value
        self.reverse_mapping[processed_key] = key

    def __delitem__(self, key: inspect.Parameter) -> None:
        processed_key = self._param_key(key)
        del self.store[processed_key]
        del self.reverse_mapping[processed_key]

    def __iter__(self) -> Iterator[inspect.Parameter]:
        return iter(self.reverse_mapping.values())

    def __len__(self) -> int:
        return len(self.store)

    def __repr__(self) -> str:
        inner = []
        for key, value in self.store.items():
            inner.append(f"Parameter(name={key[0]!r}, kind={key[1]}, annotation={key[2]}): {value}")
        return "{" + ", ".join(inner) + "}"

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, inspect.Parameter):
            raise TypeError(f"Key must be an inspect.Parameter; got {type(key)}.")
        return self._param_key(key) in self.store

    def setdefault(self, key: inspect.Parameter, default: Any = None) -> Any:
        processed_key = self._param_key(key)
        if processed_key not in self.store:
            self.reverse_mapping[processed_key] = key
        return self.store.setdefault(processed_key, default)

    def get(self, key: inspect.Parameter, default: Any = None):
        try:
            return self[key]
        except KeyError:
            return default

    def clear(self):
        self.store.clear()
        self.reverse_mapping.clear()


def is_iterable(obj) -> bool:
    return isinstance(obj, Iterable) and not isinstance(obj, str)


def to_tuple_converter(value: Union[None, Any, Iterable[Any]]) -> tuple[Any, ...]:
    """Convert a single element or an iterable of elements into a tuple.

    Intended to be used in an ``attrs.Field``. If :obj:`None` is provided, returns an empty tuple.
    If a single element is provided, returns a tuple containing just that element.
    If an iterable is provided, converts it into a tuple.

    Parameters
    ----------
    value: Optional[Union[Any, Iterable[Any]]]
        An element, an iterable of elements, or None.

    Returns
    -------
    Tuple[Any, ...]: A tuple containing the elements.
    """
    if value is None:
        return ()
    elif is_iterable(value):
        return tuple(value)
    else:
        return (value,)


def to_list_converter(value: Union[None, Any, Iterable[Any]]) -> list[Any]:
    return list(to_tuple_converter(value))


def optional_to_tuple_converter(value: Union[None, Any, Iterable[Any]]) -> Optional[tuple[Any, ...]]:
    """Convert a string or Iterable or None into an Iterable or None.

    Intended to be used in an ``attrs.Field``.
    """
    if value is None:
        return None

    if not value:
        return ()

    return to_tuple_converter(value)


def default_name_transform(s: str):
    """Converts a python identifier into a CLI token.

    Performs the following operations (in order):

    1. Convert the string to all lowercase.
    2. Replace ``_`` with ``-``.
    3. Strip any leading/trailing ``-`` (also stripping ``_``, due to point 2).

    Intended to be used with :attr:`App.name_transform` and :attr:`Parameter.name_transform`.

    Parameters
    ----------
    s: str
        Input python identifier string.

    Returns
    -------
    str
        Transformed name.
    """
    return s.lower().replace("_", "-").strip("-")


def grouper(iterable: Sequence, n: int) -> Iterator[Tuple[Any, ...]]:
    """Collect data into non-overlapping fixed-length chunks or blocks.

    https://docs.python.org/3/library/itertools.html#itertools-recipes
    """
    if len(iterable) % n:
        raise ValueError(f"{iterable!r} is not divisible by {n}.")
    iterators = [iter(iterable)] * n
    return zip(*iterators)
