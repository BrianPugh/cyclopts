"""Tab completion for :meth:`.App.interactive_shell` via the stdlib ``readline`` module.

The bash/zsh/fish generators handle command names, option names, static choices,
and paths in the generated script; only :attr:`.Parameter.completer` values come
from Python. The interactive shell has no script, so this module produces the
static candidates in Python and merges in the dynamic ones.
"""

import glob
import re
import shlex
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from cyclopts.completion._base import CompletionAction, get_completion_action, visible_commands
from cyclopts.completion._engine import Slot, _exc, debug, dynamic_candidates, resolve_slot
from cyclopts.field_info import VAR_KEYWORD

if TYPE_CHECKING:
    from cyclopts import App


def split_line(line: str) -> tuple[list[str], str] | None:
    """Split ``line`` into words, the last being the (possibly empty) word under the cursor.

    An unterminated quote is closed for the caller (``--path 'my fi`` completes ``my fi``);
    the second element is that quote (``""`` when the last word is unquoted).
    Returns ``None`` only when the line cannot be tokenized at all.
    """
    for quote in ("", "'", '"'):
        try:
            words = shlex.split(line + quote)
        except ValueError:
            continue
        if not line or (not quote and line[-1].isspace()):
            words.append("")
        return words, quote
    return None


def _shell_escape(text: str, quote: str) -> str:
    """Escape ``text`` so it continues a word typed inside ``quote`` (``""`` for an unquoted word)."""
    if quote == "'":
        return text.replace("'", "'\\''")
    if quote == '"':
        return re.sub(r'(["\\$`])', r"\\\1", text)
    return re.sub(r"([^\w@%+=:,./-])", r"\\\1", text)


def _static_candidates(slot: Slot) -> list[str]:
    root = slot.app
    command_names = [name for rc in visible_commands(slot.command_app) for name in rc.names]
    flags = (*root.help_flags, *root.version_flags)

    if slot.option_name:
        return [
            *(
                name
                for a in slot.arguments
                if a.show and a.field_info.kind is not VAR_KEYWORD and not a.is_positional_only()
                for name in a.names
            ),
            *(name for name in command_names if name.startswith("-")),
            *flags,
        ]

    candidates = []
    if not slot.unused:
        candidates += [name for name in command_names if not name.startswith("-")]
        if not slot.prior and root.app_stack.overrides.get("remap_flags"):
            # ``interactive_shell`` accepts the bare word (``help`` for ``--help``) at the root.
            candidates += [flag[2:] for flag in flags if root._is_remappable_flag(flag)]
    if slot.active is None:
        return candidates
    candidates += slot.active.get_choices(force=True) or ()
    if get_completion_action(slot.active.hint) is CompletionAction.FILES:
        # ponytail: no ``~`` expansion; readline inserts the literal path.
        incomplete = slot.incomplete
        stem = incomplete.rpartition("/")[2]
        directory = incomplete[: len(incomplete) - len(stem)]
        for path in sorted(Path(directory or ".").glob(glob.escape(stem) + "*")):
            candidates.append(directory + path.name + ("/" if path.is_dir() else ""))
    return candidates


def complete_line(app: "App", line: str) -> list[str]:
    """Prefix-filtered replacements for the whitespace-delimited word at the end of ``line``.

    readline's word boundary is whitespace, so for ``delete 'my f`` it replaces only ``f``.
    Each replacement is that word plus the candidate's remaining characters, escaped for the
    quoting context the user is already in, and closed unless it names a directory (so the
    user can keep typing into it). For ``--opt=va`` the word already carries ``--opt=``.
    """
    split = split_line(line)
    if split is None:
        return []
    words, quote = split
    slot = resolve_slot(app, words)
    if slot is None:
        return []
    text = re.split(r"[ \t\n]", line)[-1]
    candidates = _static_candidates(slot) + [value for value, _ in dynamic_candidates(slot)]
    matches = dict.fromkeys(c for c in candidates if c.startswith(slot.incomplete))
    return [
        text + _shell_escape(c[len(slot.incomplete) :], quote) + ("" if c.endswith("/") else quote) for c in matches
    ]


def make_readline_completer(app: "App", readline) -> Callable[[str, int], str | None]:
    """Build a ``readline.set_completer``-compatible callback for ``app``.

    CPython's readline module clears ``rl_completion_append_character`` (so
    ``rlcompleter`` can offer ``obj.`` continuations) and exposes no way to set
    it, so the space after a completed word is appended here. Directories get
    none so the user can keep typing into them.
    """
    matches: list[str] = []

    def completer(text: str, state: int) -> str | None:
        if state == 0:
            try:
                matches[:] = [
                    m if m.endswith("/") else m + " "
                    for m in complete_line(app, readline.get_line_buffer()[: readline.get_endidx()])
                ]
            except Exception as e:  # readline discards exceptions silently; keep them visible in debug mode.
                debug(f"readline completion failed: {_exc(e)}")
                matches.clear()
        return matches[state] if state < len(matches) else None

    return completer


@contextmanager
def readline_completion(app: "App", readline) -> Iterator[None]:
    """Install tab completion for ``app`` on ``readline``, restoring the previous state on exit."""
    previous_completer = readline.get_completer()
    previous_delims = readline.get_completer_delims()
    readline.set_completer(make_readline_completer(app, readline))
    # Whitespace-only delimiters so ``--opt=va`` and ``dir/fi`` reach the completer whole.
    readline.set_completer_delims(" \t\n")
    # libedit (macOS) speaks a different binding syntax than GNU readline.
    if "libedit" in (readline.__doc__ or ""):
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
    try:
        yield
    finally:
        readline.set_completer(previous_completer)
        readline.set_completer_delims(previous_delims)
