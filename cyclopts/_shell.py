"""Interactive shell backing :meth:`cyclopts.App.interactive_shell`.

Imported lazily: ``readline`` mutates :func:`input` for the whole process, so programs
that merely import cyclopts should not pay for it.
"""

import traceback
from collections.abc import Collection
from typing import TYPE_CHECKING, Any

from cyclopts.exceptions import CycloptsError

try:
    # Makes arrow keys and history work inside the shell.
    import readline
except ImportError:  # pragma: no cover
    # Not available on windows
    readline = None

if TYPE_CHECKING:
    from cyclopts.core import App
    from cyclopts.protocols import Dispatcher


def _get_line_buffer() -> str:
    # typeshed guards ``get_line_buffer`` behind ``sys.platform != "win32"``;
    # ``readline`` is ``None`` on Windows anyway, so this branch never runs there.
    return readline.get_line_buffer() if readline else ""  # pyright: ignore[reportAttributeAccessIssue]


def run_shell(
    app: "App",
    *,
    prompt: str,
    quit_words: Collection[str],
    dispatcher: "Dispatcher",
    parse_kwargs: dict[str, Any],
) -> None:
    """Read lines until a quit word, EOF, or Ctrl-C on an empty line.

    Must be called inside the caller's ``app_stack`` override context.
    """
    # libedit (macOS) keeps reporting the previous line from ``get_line_buffer`` until
    # new text is typed, so an interrupted buffer equal to the last seen line means the
    # line was actually empty. GNU readline reports "" directly.
    previous_line = ""
    while True:
        try:
            user_input = input(prompt)
        except EOFError:  # pragma: no cover
            break
        except KeyboardInterrupt:
            print()
            line_buffer = _get_line_buffer()
            if line_buffer in ("", previous_line):
                break
            previous_line = line_buffer
            continue
        previous_line = user_input + "\n"

        try:
            tokens = app._normalize_tokens(user_input)
        except CycloptsError:
            # Already reported (respecting ``exit_on_error``); keep the shell running.
            continue
        if not tokens:
            continue
        if tokens[0] in quit_words:
            break

        # Keep the exception handlers inside the token ``app_stack`` context so that
        # context-sensitive settings (e.g. ``error_console``) resolve from the invoked
        # subcommand rather than the root app.
        with app.app_stack(tokens):
            try:
                command, bound, ignored = app.parse_args(tokens, **parse_kwargs)
                result = dispatcher(command, bound, ignored)
                app._handle_result_action(result, fallback="print_non_int_return_int_as_exit_code")
            except CycloptsError:
                # Upstream ``parse_args`` already printed the error
                pass
            except KeyboardInterrupt:
                if not app.suppress_keyboard_interrupt:
                    raise
                print()
            except Exception:
                app.error_console.print(traceback.format_exc(), markup=False, highlight=False, soft_wrap=True)
