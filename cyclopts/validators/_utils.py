from collections.abc import Iterator, Mapping, Sequence
from collections.abc import Set as AbstractSet
from typing import Any


def iter_container_elements(value: Any) -> Iterator[Any] | None:
    """Yield the elements a per-element validator should recurse into.

    Cyclopts converts container-annotated parameters into concrete ``list``,
    ``tuple``, ``set``, ``frozenset``, and ``dict`` objects, and hands the
    **whole** container to the parameter's validator. Validators use this helper
    so every container kind recurses uniformly.

    Mappings yield their **values**; a mapping's keys are not validated. This
    matches how ``**kwargs`` parameters are validated elsewhere in Cyclopts.

    Returns
    -------
    Iterator | None
        An iterator over the elements to validate, or :obj:`None` if ``value``
        is not a container (i.e. it should be validated as a scalar).

    Raises
    ------
    TypeError
        If ``value`` is a :class:`str`, which is a :class:`~collections.abc.Sequence`
        but never a valid container of values to validate.
    """
    if isinstance(value, Mapping):
        return iter(value.values())
    if isinstance(value, Sequence | AbstractSet):
        if isinstance(value, str):
            raise TypeError
        return iter(value)
    return None
