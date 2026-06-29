"""Shared helper functions and constants for the argument package."""

import sys
from collections.abc import Callable, Iterable, Iterator
from contextlib import suppress
from enum import Enum, Flag
from functools import partial
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypeVar, get_args, get_origin

if TYPE_CHECKING:
    from cyclopts.argument._argument import Argument

F = TypeVar("F", bound=Flag)

from cyclopts._convert import convert_enum_flag
from cyclopts.annotations import (
    ITERABLE_TYPES,
    is_class_and_subclass,
    is_union,
    resolve_annotated,
)
from cyclopts.field_info import (
    KEYWORD_ONLY,
    POSITIONAL_ONLY,
    POSITIONAL_OR_KEYWORD,
    VAR_KEYWORD,
    VAR_POSITIONAL,
    FieldInfo,
)
from cyclopts.parameter import Parameter

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import TypeAliasType
else:  # pragma: no cover
    TypeAliasType = None

PARAMETER_SUBKEY_BLOCKER = Parameter(
    name=None,
    alias=None,
    converter=None,  # pyright: ignore
    validator=None,
    accepts_keys=None,
    env_var=None,
)

KIND_PARENT_CHILD_REASSIGNMENT = {
    (POSITIONAL_OR_KEYWORD, POSITIONAL_OR_KEYWORD): POSITIONAL_OR_KEYWORD,
    (POSITIONAL_OR_KEYWORD, POSITIONAL_ONLY): POSITIONAL_ONLY,
    (POSITIONAL_OR_KEYWORD, KEYWORD_ONLY): KEYWORD_ONLY,
    (POSITIONAL_OR_KEYWORD, VAR_POSITIONAL): VAR_POSITIONAL,
    (POSITIONAL_OR_KEYWORD, VAR_KEYWORD): VAR_KEYWORD,
    (POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD): POSITIONAL_ONLY,
    (POSITIONAL_ONLY, POSITIONAL_ONLY): POSITIONAL_ONLY,
    (POSITIONAL_ONLY, KEYWORD_ONLY): None,
    (POSITIONAL_ONLY, VAR_POSITIONAL): VAR_POSITIONAL,
    (POSITIONAL_ONLY, VAR_KEYWORD): None,
    (KEYWORD_ONLY, POSITIONAL_OR_KEYWORD): KEYWORD_ONLY,
    (KEYWORD_ONLY, POSITIONAL_ONLY): None,
    (KEYWORD_ONLY, KEYWORD_ONLY): KEYWORD_ONLY,
    (KEYWORD_ONLY, VAR_POSITIONAL): None,
    (KEYWORD_ONLY, VAR_KEYWORD): VAR_KEYWORD,
    (VAR_POSITIONAL, POSITIONAL_OR_KEYWORD): POSITIONAL_ONLY,
    (VAR_POSITIONAL, POSITIONAL_ONLY): POSITIONAL_ONLY,
    (VAR_POSITIONAL, KEYWORD_ONLY): None,
    (VAR_POSITIONAL, VAR_POSITIONAL): VAR_POSITIONAL,
    (VAR_POSITIONAL, VAR_KEYWORD): None,
    (VAR_KEYWORD, POSITIONAL_OR_KEYWORD): KEYWORD_ONLY,
    (VAR_KEYWORD, POSITIONAL_ONLY): None,
    (VAR_KEYWORD, KEYWORD_ONLY): KEYWORD_ONLY,
    (VAR_KEYWORD, VAR_POSITIONAL): None,
    (VAR_KEYWORD, VAR_KEYWORD): VAR_KEYWORD,
}


def get_choices_from_hint(type_: type, name_transform: Callable[[str], str]) -> list[str]:
    """Extract completion choices from a type hint.

    Recursively extracts choices from Literal types, Enum types, and Union types.

    Parameters
    ----------
    type_ : type
        Type annotation to extract choices from.
    name_transform : Callable[[str], str]
        Function to transform choice names (e.g., for case conversion).

    Returns
    -------
    list[str]
        List of choice strings extracted from the type hint.
    """
    get_choices = partial(get_choices_from_hint, name_transform=name_transform)
    choices = []
    _origin = get_origin(type_)
    if isinstance(type_, type) and is_class_and_subclass(type_, Enum):
        choices.extend(name_transform(x) for x in type_.__members__)
    elif is_union(_origin):
        inner_choices = [get_choices(inner) for inner in get_args(type_)]
        for x in inner_choices:
            if x:
                choices.extend(x)
    elif _origin is Literal:
        choices.extend(str(x) for x in get_args(type_))
    elif _origin in ITERABLE_TYPES:
        args = get_args(type_)
        if len(args) == 1 or (_origin is tuple and len(args) == 2 and args[1] is Ellipsis):
            choices.extend(get_choices(args[0]))
    elif _origin is Annotated:
        choices.extend(get_choices(resolve_annotated(type_)))
    elif TypeAliasType is not None and isinstance(type_, TypeAliasType):
        choices.extend(get_choices(type_.__value__))
    return choices


def startswith(string, prefix):
    def normalize(s):
        return s.replace("_", "-")

    return normalize(string).startswith(normalize(prefix))


def missing_keys_factory(
    get_field_info: Callable[[Any], dict[str, FieldInfo]],
) -> Callable[["Argument", dict[str, Any]], list[str]]:
    def inner(argument: "Argument", data: dict[str, Any]) -> list[str]:
        provided_keys = set(data)
        field_info = get_field_info(argument.hint)
        return [k for k, v in field_info.items() if (v.required and k not in provided_keys)]

    return inner


def enum_flag_from_dict(
    enum_type: type[F],
    data: dict[str, bool],
    name_transform: Callable[[str], str],
) -> F:
    """Convert a dictionary of boolean flags to a Flag enum value.

    Parameters
    ----------
    enum_type : type[F]
        The Flag enum type to convert to.
    data : dict[str, bool]
        Dictionary mapping flag names to boolean values.

    Returns
    -------
    F
        The combined flag value.
    """
    return convert_enum_flag(enum_type, (k for k, v in data.items() if v), name_transform)


def is_short_flag(flag: str) -> bool:
    """Return :obj:`True` for a single-letter flag like ``-e`` (not ``--env`` or ``-`` alone)."""
    return len(flag) == 2 and flag[0] == "-" and flag[1] != "-"


def _is_root_namespace(names: str | Iterable[str] | None) -> bool:
    """Return :obj:`True` if the parameter surfaces at the root CLI namespace.

    A root-namespace parameter has an **undotted** long flag (e.g. ``--env``). This
    covers genuine top-level command parameters as well as fields promoted to the root
    via ``Parameter(name="*")`` or PEP 692 unpacking (``--name``), while excluding dotted
    nested fields such as ``--user.name``.
    """
    if isinstance(names, str):  # Defensive: resolved names are always a tuple at this point.
        names = (names,)
    return any(n.startswith("--") and "." not in n for n in (names or ()))


def reserve_explicit_shorts(argument: "Argument", used_short_aliases: set[str]) -> None:
    """Phase 1a: reserve every explicitly-provided short flag into ``used_short_aliases``.

    Runs for *every* argument as the tree is built (independent of eligibility), so that
    auto-generation (phase 2, deferred until the whole tree is known) avoids user-supplied
    shorts regardless of parameter ordering. At this point no auto short has been appended
    yet, so any single-letter flag present is necessarily user-provided.
    """
    cparam = argument.parameter
    for flag in (*(cparam.name or ()), *(cparam.alias or ())):
        if is_short_flag(flag):
            used_short_aliases.add(flag)


def is_short_alias_eligible(argument: "Argument", immediate_parameter: Parameter) -> bool:
    """Phase 1b: pure predicate for whether this argument should receive an auto-generated short flag.

    Auto shorts apply to opted-in (``short_alias``), **input-binding** parameters only
    (scalars, dicts, enum flags) — never to promoted containers whose fields become child
    options. They apply only to **root-namespace** parameters (an undotted long flag). A
    field that stays namespaced (e.g. ``--user.name``) never gets one — ``short_alias`` on
    such a field is inert; flatten it to the root namespace via ``name="*"`` to expose it.
    """
    cparam = argument.parameter

    if not cparam.short_alias:
        return False

    # An explicitly-provided alias or name suppresses auto-generation: the user has taken
    # manual control of this parameter's flags, so Cyclopts only uses what they supplied.
    # The checks deliberately differ:
    #   - ``name`` uses ``immediate_parameter._provided_args`` (the user's own annotation),
    #     because Cyclopts always re-injects a resolved ``name`` into ``cparam`` — so
    #     ``"name" in cparam._provided_args`` is always True and useless here.
    #   - ``alias`` uses ``cparam.alias`` *truthiness* rather than ``_provided_args``:
    #     internal subkey combining (``PARAMETER_SUBKEY_BLOCKER``) injects ``alias=None``,
    #     which pollutes ``cparam._provided_args`` with a spurious ``"alias"``. Truthiness
    #     ignores that ``None`` while still catching a real alias from a global
    #     ``App(default_parameter=Parameter(alias=...))``.
    # (``name="*"`` flattening sets ``name`` on a container, excluded below anyway; its
    # promoted children carry no explicit ``name`` and remain eligible.)
    if "name" in immediate_parameter._provided_args or "alias" in immediate_parameter._provided_args or cparam.alias:
        return False

    # Root-namespace only. A field that stays namespaced (e.g. ``--user.name``) never gets
    # a short, even with ``short_alias=True`` set directly on it; flatten it via ``name="*"``.
    if not _is_root_namespace(cparam.name):
        return False

    # Only parameters that bind CLI input directly get a short; containers do not.
    if argument._accepts_keywords and not argument._enum_flag_type:
        return False

    return True


def generate_short_alias(
    argument: "Argument",
    used_short_aliases: set[str],
) -> tuple[str, ...] | None:
    """Phase 2: generate the auto short flag(s) for an argument deemed eligible by phase 1.

    Deferred until every parameter's explicit short has been reserved, so an earlier
    parameter's auto short can never shadow a later parameter's explicit ``alias``.

    Returns the generated short name(s) to append to the argument's name as standalone
    flags (so they surface globally, e.g. ``-e``, never dotted like ``-u.name``), or
    :obj:`None`. Mutates ``used_short_aliases`` to reserve claimed letters.
    """
    cparam = argument.parameter
    field_info = argument.field_info

    short = None
    short_alias = cparam.short_alias
    if callable(short_alias):
        # Hand the callable a read-only snapshot so it cannot mutate the internal
        # collision-tracking set and corrupt assignment for later parameters.
        short = short_alias(field_info, frozenset(used_short_aliases))
    elif short_alias and field_info.kind not in (POSITIONAL_ONLY, VAR_POSITIONAL):
        # A boolean that already defaults to True would only get a no-op positive short
        # (the meaningful off-switch ``--no-flag`` is long-only), so skip auto-generation
        # and leave the letter free for a parameter that can actually use it.
        if argument.hint is bool and field_info.default is True:
            return None
        # Derive the letter from the transformed CLI name (not the raw python identifier)
        # so it stays consistent with the long flag (``--my-flag`` -> ``-m``, ``_foo`` -> ``-f``).
        transformed = cparam.name_transform(field_info.names[0])
        if transformed:
            letter = transformed[0].lower()
            for candidate in (f"-{letter}", f"-{letter.upper()}"):
                if candidate not in used_short_aliases:
                    short = candidate
                    break

    if not short:
        return None
    if isinstance(short, str):
        shorts = (short,)
    else:
        try:
            shorts = tuple(short)
        except TypeError:
            raise TypeError(
                f"Parameter.short_alias callable must return a str, an iterable of str, or None; got {short!r}."
            ) from None
    # The callable is custom logic, but it still must produce single-letter short flags
    # (e.g. ``-e``) — anything else would be silently appended as a long flag or, worse, a
    # positional name. Fail loudly instead, mirroring the field-level str rejection.
    for s in shorts:
        if not isinstance(s, str) or not is_short_flag(s):
            raise ValueError(
                f"Parameter.short_alias callable must return single-letter short flags like '-e'; got {s!r}."
            )
    # Drop any short already claimed by an earlier parameter (first-wins), so a
    # callable that ignores ``used_short_aliases`` can't create duplicate flags.
    shorts = tuple(s for s in shorts if s not in used_short_aliases)
    if not shorts:
        return None
    used_short_aliases.update(shorts)
    return shorts


def extract_docstring_help(f: Callable) -> dict[tuple[str, ...], Parameter]:
    from docstring_parser import parse_from_object

    with suppress(AttributeError):
        f = f.func  # pyright: ignore[reportFunctionMemberAccess]

    result = {}

    # For classes, walk through MRO  to include base class fields.
    # parse_from_object only extracts docstrings from the **immediate** class's source code,
    # not from inherited fields.
    # From docstring_parser docs:
    #
    #    When given a class, only the attribute docstrings of that class are parsed, not its
    #    inherited classes. This is a design decision. Separate calls to this function
    #    should be performed to get attribute docstrings of parent classes.
    if mro := getattr(f, "__mro__", None):
        # Process base classes first (reversed MRO order), so derived classes can override
        # their parent's docstrings if they redefine the same field with a new docstring.
        for base_class in reversed(mro[:-1]):  # Exclude 'object'
            try:
                parsed = parse_from_object(base_class)
                for dparam in parsed.params:
                    result[tuple(dparam.arg_name.split("."))] = Parameter(help=dparam.description)
            except (TypeError, AttributeError):
                # Some base classes may not have parseable docstrings (e.g., built-in classes)
                continue
    else:
        # For functions/callables (original behavior)
        try:
            parsed = parse_from_object(f)
            for dparam in parsed.params:
                result[tuple(dparam.arg_name.split("."))] = Parameter(help=dparam.description)
        except (TypeError, AttributeError):
            # parse_from_object may fail for some callables
            pass

    return result


def resolve_parameter_name_helper(elem):
    if elem.endswith("*"):
        elem = elem[:-1].rstrip(".")
    if elem and not elem.startswith("-"):
        elem = "--" + elem
    return elem


def resolve_parameter_name(*argss: tuple[str, ...]) -> tuple[str, ...]:
    """Resolve parameter names by combining and formatting multiple tuples of strings.

    Parameters
    ----------
    *argss
        Each tuple represents a group of parameter name components.

    Returns
    -------
    tuple[str, ...]
        A tuple of resolved parameter names.
    """
    argss = tuple(x for x in argss if x)

    if len(argss) == 0:
        return ()
    elif len(argss) == 1:
        return tuple("*" if x == "*" else resolve_parameter_name_helper(x) for x in argss[0])

    out = []
    for a1 in argss[0]:
        a1 = resolve_parameter_name_helper(a1)
        for a2 in argss[1]:
            if a2.startswith("-") or not a1:
                out.append(a2)
            else:
                out.append(a1 + "." + a2)

    return resolve_parameter_name(tuple(out), *argss[2:])


def walk_leaves(
    d,
    parent_keys: tuple[str, ...] | None = None,
) -> Iterator[tuple[tuple[str, ...], Any]]:
    if parent_keys is None:
        parent_keys = ()

    if isinstance(d, dict):
        for key, value in d.items():
            current_keys = parent_keys + (key,)
            if isinstance(value, dict):
                yield from walk_leaves(value, current_keys)
            else:
                yield current_keys, value
    else:
        yield (), d


def to_cli_option_name(*keys: str) -> str:
    return "--" + ".".join(keys)
