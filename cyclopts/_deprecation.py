import warnings
from collections.abc import Callable

DeprecatedHandler = Callable[[str, str, "str | None", "str | None"], None]
"""Signature for a ``deprecated_handler``: ``(kind, name, version, message) -> None``.

``kind`` is ``"command"`` or ``"parameter"``; ``name`` is the command/parameter's
primary CLI name; ``version`` and ``message`` come from the ``deprecated`` field
(see :func:`cyclopts.utils.normalize_deprecated`).
"""


def default_deprecated_handler(kind: str, name: str, version: str | None, message: str | None) -> None:
    """Default ``deprecated_handler``: emits a :class:`DeprecationWarning`.

    Note that Python ignores :class:`DeprecationWarning` by default unless the
    triggering code runs as ``__main__``; configure warning filters (e.g. ``-W
    default::DeprecationWarning``) or ``logging.captureWarnings(True)`` to see
    it reliably, or supply a custom ``deprecated_handler`` (e.g. one that calls
    your own logger) to bypass the warnings-filter system entirely.
    """
    text = f"{kind} {name!r} is deprecated"
    if version:
        text += f" since v{version}"
    if message:
        text += f": {message}"
    warnings.warn(text, DeprecationWarning, stacklevel=2)
