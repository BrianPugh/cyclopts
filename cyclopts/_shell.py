"""Interactive shell backing :meth:`cyclopts.App.interactive_shell`.

Imported lazily: ``readline`` mutates :func:`input` for the whole process, so programs
that merely import cyclopts should not pay for it.
"""

import cmd
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


def get_line_buffer() -> str:
    """Text currently typed at the prompt, or ``""`` where ``readline`` is unavailable."""
    # typeshed guards ``get_line_buffer`` behind ``sys.platform != "win32"``;
    # ``readline`` is ``None`` on Windows anyway, so this branch never runs there.
    return readline.get_line_buffer() if readline else ""  # pyright: ignore[reportAttributeAccessIssue]


class Shell(cmd.Cmd):
    """Dispatches every line to the wrapped :class:`App`.

    :meth:`onecmd` is overridden wholesale so :mod:`cmd`'s own dispatch (``do_*`` methods,
    ``help``/``?``/``!`` shortcuts, ``identchars`` splitting) never intercepts a user command.
    """

    def __init__(
        self,
        app: "App",
        *,
        prompt: str,
        quit_words: Collection[str],
        dispatcher: "Dispatcher",
        parse_kwargs: dict[str, Any],
    ):
        # An empty ``completekey`` leaves readline's default tab behavior untouched.
        super().__init__(completekey="")
        self.prompt = prompt
        self.app = app
        self.quit_words = quit_words
        self.dispatcher = dispatcher
        self.parse_kwargs = parse_kwargs
        # libedit (macOS) keeps reporting the previous line from ``get_line_buffer`` until
        # new text is typed, so an interrupted buffer equal to the last seen line means the
        # line was actually empty. GNU readline reports "" directly.
        self.previous_line = ""
        self.interrupted_in_command = False

    def onecmd(self, line: str) -> bool:
        # ``cmdloop`` substitutes the literal word ``EOF`` on Ctrl-D.
        if line == "EOF":
            return True
        try:
            tokens = self.app._normalize_tokens(line)
        except CycloptsError:
            # Already reported (respecting ``exit_on_error``); keep the shell running.
            return False
        if not tokens:
            return False
        if tokens[0] in self.quit_words:
            return True

        # Keep the exception handlers inside the token ``app_stack`` context so that
        # context-sensitive settings (e.g. ``error_console``) resolve from the invoked
        # subcommand rather than the root app.
        with self.app.app_stack(tokens):
            try:
                command, bound, ignored = self.app.parse_args(tokens, **self.parse_kwargs)
                result = self.dispatcher(command, bound, ignored)
                self.app._handle_result_action(result, fallback="print_non_int_return_int_as_exit_code")
            except CycloptsError:
                # Upstream ``parse_args`` already printed the error
                pass
            except KeyboardInterrupt:
                if not self.app.suppress_keyboard_interrupt:
                    self.interrupted_in_command = True
                    raise
                print()
            except Exception:
                self.app.error_console.print(traceback.format_exc(), markup=False, highlight=False, soft_wrap=True)
        return False

    def postcmd(self, stop: bool, line: str) -> bool:
        self.previous_line = line + "\n"
        return stop

    def run(self) -> None:
        """Run the shell until a quit word, EOF, or Ctrl-C on an empty line."""
        while True:
            try:
                self.cmdloop()
                return
            except KeyboardInterrupt:
                if self.interrupted_in_command:
                    raise
                # ``cmd.Cmd`` does not catch Ctrl-C; clear the typed line, or exit when empty.
                print()
                line_buffer = get_line_buffer()
                if line_buffer in ("", self.previous_line):
                    return
                self.previous_line = line_buffer
