"""To prevent circular dependencies, this module should never import anything else from Cyclopts."""

import functools
import inspect
import sys
from collections.abc import Iterable, Iterator
from contextlib import suppress
from operator import itemgetter
from typing import TYPE_CHECKING, Any, Literal, Optional, Sequence, Tuple, Union

from attrs import field, frozen

# fmt: off

# https://threeofwands.com/attra-iv-zero-overhead-frozen-attrs-classes/
if TYPE_CHECKING:
    from json import JSONDecodeError

    from attrs import frozen
else:
    from attrs import define

    frozen = functools.partial(define, unsafe_hash=True)

if sys.version_info >= (3, 10):  # pragma: no cover
    def signature(f: Any) -> inspect.Signature:
        return inspect.signature(f, eval_str=True)
else:  # pragma: no cover
    def signature(f: Any) -> inspect.Signature:
        return inspect.signature(f)
# fmt: on

if sys.version_info >= (3, 10):  # pragma: no cover
    from sys import stdlib_module_names
else:  # pragma: no cover
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
    def __new__(cls):
        raise ValueError("Sentinel objects are not intended to be instantiated. Subclass instead.")


class UNSET(Sentinel):
    """Special sentinel value indicating that no data was provided. **Do not instantiate**."""


def record_init(target: str):
    """Class decorator that records init argument names as a tuple to ``target``."""

    def decorator(cls):
        original_init = cls.__init__
        function_signature = signature(original_init)
        param_names = tuple(name for name in function_signature.parameters if name != "self")

        @functools.wraps(original_init)
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            # Circumvent frozen protection.
            object.__setattr__(self, target, tuple(param_names[i] for i in range(len(args))) + tuple(kwargs))

        cls.__init__ = new_init
        return cls

    return decorator


def is_iterable(obj) -> bool:
    if isinstance(obj, (list, tuple, set, dict)):  # Fast path for common types
        return True
    return not isinstance(obj, str) and isinstance(obj, Iterable)


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


def is_option_like(token: str) -> bool:
    """Checks if a token looks like an option.

    Namely, negative numbers are not options, but a token like ``--foo`` is.
    """
    with suppress(ValueError):
        complex(token)
        return False
    return token.startswith("-")


def is_builtin(obj: Any) -> bool:
    return getattr(obj, "__module__", "").split(".")[0] in stdlib_module_names


def resolve_callables(t, *args, **kwargs):
    """Recursively resolves callable elements in a tuple.

    Returns an object that "looks like" the input, but with all callable's invoked
    and replaced with their return values. Positional and keyword elements will be
    passed along to each invocation.
    """
    if isinstance(t, type(Sentinel)):
        return t

    if callable(t):
        return t(*args, **kwargs)
    elif is_iterable(t):
        resolved = []
        for element in t:
            if isinstance(element, type(Sentinel)):
                resolved.append(element)
            elif callable(element):
                resolved.append(element(*args, **kwargs))
            elif is_iterable(element):
                resolved.append(resolve_callables(element, *args, **kwargs))
            else:
                resolved.append(element)
        return tuple(resolved)
    else:
        return t


@frozen
class SortHelper:
    key: Any
    fallback_key: Any = field(converter=to_tuple_converter)
    value: Any

    @staticmethod
    def sort(entries: Sequence["SortHelper"]) -> list["SortHelper"]:
        user_sort_key = []
        ordered_no_user_sort_key = []
        no_user_sort_key = []

        for entry in entries:
            if entry.key in (UNSET, None):
                no_user_sort_key.append((entry.fallback_key, entry))
            elif is_iterable(entry.key) and entry.key[0] in (UNSET, None):
                ordered_no_user_sort_key.append((entry.key[1:] + entry.fallback_key, entry))
            else:
                user_sort_key.append(((entry.key, entry.fallback_key), entry))

        user_sort_key.sort(key=itemgetter(0))
        ordered_no_user_sort_key.sort(key=itemgetter(0))
        no_user_sort_key.sort(key=itemgetter(0))

        combined = user_sort_key + ordered_no_user_sort_key + no_user_sort_key
        return [x[1] for x in combined]


def json_decode_error_verbosifier(decode_error: "JSONDecodeError", context: int = 20) -> str:
    """Not intended to be a super robust implementation, but robust enough to be helpful.

    Parameters
    ----------
    context: int
        Number of surrounding-character context
    """
    lines = decode_error.doc.splitlines()
    line = lines[decode_error.lineno - 1]

    error_index = decode_error.colno - 1  # colno is 1-indexed
    start = error_index - context
    if start <= 0:
        start = 0
        prefix_ellipsis = ""
        segment_error_index = error_index
    else:
        prefix_ellipsis = "... "
        segment_error_index = error_index - start

    end = error_index + context
    if end >= len(line):
        end = len(line) + 1
        suffix_ellipsis = ""
    else:
        suffix_ellipsis = " ..."

    segment = line[start:end]
    carat_pointer = " " * (len(prefix_ellipsis) + segment_error_index) + "^"

    response = (
        f"JSONDecodeError:\n    {prefix_ellipsis}{segment}{suffix_ellipsis}\n    {carat_pointer}\n{str(decode_error)}"
    )
    return response
