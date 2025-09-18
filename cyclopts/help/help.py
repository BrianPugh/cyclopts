import inspect
import sys
from collections.abc import Iterable
from enum import Enum
from functools import lru_cache, partial
from inspect import isclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    Literal,
    Optional,
    Sequence,
    get_args,
    get_origin,
)

from attrs import define, evolve, field

from cyclopts._convert import ITERABLE_TYPES
from cyclopts.annotations import is_union, resolve_annotated
from cyclopts.core import _get_root_module_name
from cyclopts.field_info import signature_parameters
from cyclopts.group import Group
from cyclopts.help.inline_text import InlineText
from cyclopts.help.silent import SILENT
from cyclopts.utils import SortHelper, frozen, resolve_callables

if TYPE_CHECKING:
    from rich.console import RenderableType

    from cyclopts.argument import ArgumentCollection
    from cyclopts.core import App

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import TypeAliasType
else:  # pragma: no cover
    TypeAliasType = None


@lru_cache(maxsize=16)
def docstring_parse(doc: str, format: str):
    """Addon to :func:`docstring_parser.parse` that supports multi-line `short_description`."""
    import docstring_parser

    cleaned_doc = inspect.cleandoc(doc)
    short_description_and_maybe_remainder = cleaned_doc.split("\n\n", 1)

    # Place multi-line summary into a single line.
    # This kind of goes against PEP-0257, but any reasonable CLI command will
    # have either no description, or it will have both a short and long description.
    short = short_description_and_maybe_remainder[0].replace("\n", " ")
    if len(short_description_and_maybe_remainder) == 1:
        cleaned_doc = short
    else:
        cleaned_doc = short + "\n\n" + short_description_and_maybe_remainder[1]

    res = docstring_parser.parse(cleaned_doc)

    # Ensure a short description exists if there's a long description
    assert not res.long_description or res.short_description

    return res


def _text_factory():
    from rich.text import Text

    return Text()


@frozen(kw_only=True)
class HelpEntry:
    """Container for help table entry data."""

    names: tuple[str, ...] = ()
    """Long option names (e.g., "--verbose", "--help")."""

    shorts: tuple[str, ...] = ()
    """Short option names (e.g., "-v", "-h")."""

    description: Optional["RenderableType"] = None
    """Help text description for this entry."""

    required: bool = False
    """Whether this parameter/command is required."""

    sort_key: Any = None
    """Custom sorting key for ordering entries."""

    type: Optional[Any] = None
    """Type annotation of the parameter."""

    choices: Optional[tuple[str, ...]] = None
    """Available choices for this parameter."""

    env_var: Optional[tuple[str, ...]] = None
    """Environment variable names that can set this parameter."""

    default: Optional[str] = None
    """Default value for this parameter to display. None means no default to show."""

    def copy(self, **kwargs):
        return evolve(self, **kwargs)


@define
class HelpPanel:
    """Data container for help panel information."""

    format: Literal["command", "parameter"]
    """Panel format type."""

    title: "RenderableType"
    """The title text displayed at the top of the help panel."""

    description: "RenderableType" = field(factory=_text_factory)
    """Optional description text displayed below the title."""

    entries: list[HelpEntry] = field(factory=list)
    """List of help entries to display (in order) in the panel."""

    def copy(self, **kwargs):
        return evolve(self, **kwargs)

    def _remove_duplicates(self):
        seen, out = set(), []
        for item in self.entries:
            hashable = (item.names, item.shorts)
            if hashable not in seen:
                seen.add(hashable)
                out.append(item)
        self.entries = out

    def _sort(self):
        """Sort entries in-place."""
        if not self.entries:
            return

        if self.format == "command":
            sorted_sort_helper = SortHelper.sort(
                [
                    SortHelper(
                        entry.sort_key,
                        (
                            entry.names[0].startswith("-") if entry.names else False,
                            entry.names[0] if entry.names else "",
                        ),
                        entry,
                    )
                    for entry in self.entries
                ]
            )
            self.entries = [x.value for x in sorted_sort_helper]
        else:
            raise NotImplementedError


def _is_short(s):
    return not s.startswith("--") and s.startswith("-")


def format_usage(
    app: "App",
    command_chain: Iterable[str],
):
    from rich.text import Text

    usage = []
    usage.append("Usage:")

    # If we're at the root level (no command chain), the app has a default_command,
    # and no explicit name was set, derive a better name from sys.argv[0]
    if not command_chain and app.default_command and not app._name:
        # Use the same logic as in App.name property for apps without default_command
        name = Path(sys.argv[0]).name
        if name == "__main__.py":
            name = _get_root_module_name()
        app_name = name
    else:
        app_name = app.name[0]

    usage.append(app_name)
    usage.extend(command_chain)

    for command in command_chain:
        app = app[command]

    if any(app[x].show for x in app._registered_commands):
        usage.append("COMMAND")

    if app.default_command:
        to_show = set()
        for field_info in signature_parameters(app.default_command).values():
            if field_info.kind in (
                field_info.POSITIONAL_ONLY,
                field_info.VAR_POSITIONAL,
                field_info.POSITIONAL_OR_KEYWORD,
            ):
                to_show.add("[ARGS]")
            if field_info.kind in (field_info.KEYWORD_ONLY, field_info.VAR_KEYWORD, field_info.POSITIONAL_OR_KEYWORD):
                to_show.add("[OPTIONS]")
        usage.extend(sorted(to_show))

    return Text(" ".join(usage) + "\n", style="bold")


def _smart_join(strings: Sequence[str]) -> str:
    """Joins strings with a space, unless the previous string ended in a newline."""
    if not strings:
        return ""

    result = [strings[0]]
    for s in strings[1:]:
        if result[-1].endswith("\n"):
            result.append(s)
        else:
            result.append(" " + s)

    return "".join(result)


def format_doc(app: "App", format: str):
    raw_doc_string = app.help

    if not raw_doc_string:
        return SILENT

    parsed = docstring_parse(raw_doc_string, format)

    components: list[str] = []
    if parsed.short_description:
        components.append(parsed.short_description + "\n")

    if parsed.long_description:
        if parsed.short_description:
            components.append("\n")
        components.append(parsed.long_description + "\n")
    return InlineText.from_format(_smart_join(components), format=format, force_empty_end=True)


def _get_choices(type_: type, name_transform: Callable[[str], str]) -> list[str]:
    get_choices = partial(_get_choices, name_transform=name_transform)
    choices = []
    _origin = get_origin(type_)
    if isclass(type_) and issubclass(type_, Enum):
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


def create_parameter_help_panel(
    group: "Group",
    argument_collection: "ArgumentCollection",
    format: str,
) -> HelpPanel:
    from rich.text import Text

    kwargs = {
        "format": "parameter",
        "title": group.name,
        "description": InlineText.from_format(group.help, format=format, force_empty_end=True)
        if group.help
        else Text(),
    }

    help_panel = HelpPanel(**kwargs)

    def help_append(text, style):
        if help_components:
            text = " " + text
        if style:
            help_components.append((text, style))
        else:
            help_components.append(text)

    entries_positional, entries_kw = [], []
    for argument in argument_collection.filter_by(show=True):
        assert argument.parameter.name_transform

        help_components = []
        options = list(argument.names)

        # Add an all-uppercase name if it's an argument
        if argument.index is not None:
            arg_name = options[0].lstrip("-").upper()
            if arg_name != options[0]:
                options = [arg_name, *options]

        short_options, long_options = [], []
        for option in options:
            if _is_short(option):
                short_options.append(option)
            else:
                long_options.append(option)

        help_description = InlineText.from_format(argument.parameter.help, format=format)

        # Prepare choices if needed
        choices = None
        if argument.parameter.show_choices:
            choices_list = _get_choices(argument.hint, argument.parameter.name_transform)
            if choices_list:
                choices = tuple(choices_list)

        # Prepare env_var if needed
        env_var = None
        if argument.parameter.show_env_var and argument.parameter.env_var:
            env_var = tuple(argument.parameter.env_var)

        # Prepare default if needed
        default = None
        if argument.show_default:
            if isclass(argument.hint) and issubclass(argument.hint, Enum):
                default = argument.parameter.name_transform(argument.field_info.default.name)
            else:
                default = str(argument.field_info.default)
            if callable(argument.show_default):
                default = argument.show_default(argument.field_info.default)

        # populate row
        entry = HelpEntry(
            names=tuple(long_options),
            description=help_description,
            shorts=tuple(short_options),
            required=argument.required,
            type=resolve_annotated(argument.field_info.annotation),
            choices=choices,
            env_var=env_var,
            default=default,
        )

        if argument.field_info.is_positional:
            entries_positional.append(entry)
        else:
            entries_kw.append(entry)

    help_panel.entries.extend(entries_positional)
    help_panel.entries.extend(entries_kw)

    return help_panel


def format_command_entries(apps: Iterable["App"], format: str) -> list[HelpEntry]:
    entries = []
    for app in apps:
        if not app.show:
            continue
        short_names, long_names = [], []
        for name in app.name:
            short_names.append(name) if _is_short(name) else long_names.append(name)

        entry = HelpEntry(
            names=tuple(long_names),
            shorts=tuple(short_names),
            description=InlineText.from_format(docstring_parse(app.help, format).short_description, format=format),
            sort_key=resolve_callables(app.sort_key, app),
        )
        if entry not in entries:
            entries.append(entry)
    return entries
