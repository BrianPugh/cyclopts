import os
from pathlib import Path
from typing import Any, List, Optional, get_args


def _is_path(type_) -> bool:
    from cyclopts._convert import resolve

    if type_ is Path:
        return True

    for inner_type in get_args(type_):
        inner_type = resolve(inner_type)
        if _is_path(inner_type):
            return True

    return False


def env_var_split(
    type_: Any,
    val: str,
    *,
    delimiter: Optional[str] = None,
):
    """Type-dependent environment variable value splitting.

    Performs splitting when:

    * The ``type_`` is some variant of ``Iterable[pathlib.Path]`` objects.
      If Windows, split on ``;``, otherwise split on ``:``.

    * Otherwise, if the ``type_`` is an ``Iterable``, split on whitespace.
      Leading/trailing whitespace of each output element will be stripped.

    Is the default value for :attr:`cyclopts.App.env_var_split`.

    Parameters
    ----------
    type_: type
        Type hint that we will eventually coerce into.
    val: str
        String to split.
    delimiter: Optional[str]
        Delimiter to split ``val`` on.
        If ``None``, defaults to whitespace.

    Returns
    -------
    list[str]
        List of individual tokens.
    """
    from cyclopts._convert import token_count
    from cyclopts.parameter import get_hint_parameter

    count, consume_all = token_count(type_)
    type_ = get_hint_parameter(type_)[0]

    if count > 1 or consume_all:
        if _is_path(type_):
            return val.split(os.pathsep)
        else:
            return val.split(delimiter)
    else:
        return [val]
