import os
import tempfile
from pathlib import Path
from typing import Sequence, Union


class EditorError(Exception):
    """Root editor-related error."""


class DidNotSaveError(EditorError):
    """User did not save upon exiting."""


class DidNotChangeError(EditorError):
    """User did not edit file contents."""


class EditorNotFoundError(EditorError):
    """Could not find a valid text editor."""


def edit(
    initial_text: str = "",
    *,
    fallback_editors: Sequence[str] = ("nano", "vim", "notepad", "gedit"),
    editor_args: Sequence[str] = (),
    path: Union[str, Path] = "",
    encoding: str = "utf-8",
    save: bool = True,
    required: bool = True,
) -> str:
    """Get text input from a user via their default editor.

    Parameters
    ----------
    initial_text: str
        Initial text to populate the text file with.
    fallback_editors: Sequence[str]
        If the text editor cannot be determined from the environment variable ``EDITOR``, attempt to use these text editors in the order provided.
    editor_args: Sequence[str]
        Additional CLI arguments that are passed along to the editor-launch command.
    path: Union[str, Path]
        If specified, the path to the file that should be opened.
        Text editors typically display this, so a custom path may result in a better user-interface.
        Otherwiser, defaults to a temporary text file.
    encoding: str
        File encoding to use.
    save: bool
        Require the user to save before exiting the editor.
    required: bool
        Require for the saved text to be different from ``initial_text``.

    Raises
    ------
    EditorError
        Base editor error exception. Explicitly raised if editor subcommand
        returned a non-zero exit code.
    EditorNotFoundError
        A suitable text editor could not be found.
    DidNotSaveError
        The user exited the text-editor without saving and ``save=True``.
    DidNotChangeError
        The user did not change the file contents and ``required=True``.

    Returns
    -------
    str
        The resulting text that was saved to the text editor.
    """
    import shutil
    import subprocess

    for editor in (os.environ.get("EDITOR"), *fallback_editors):
        if editor and shutil.which(editor):
            break
    else:
        raise EditorNotFoundError

    if path:
        path = Path(path)
        path.parent.mkdir(exist_ok=True, parents=True)
    else:
        path = Path(tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False).name)
    path.write_text(initial_text, encoding=encoding)

    start_mtime = path.stat().st_mtime

    try:
        subprocess.check_output([editor, path, *editor_args])
        end_mtime = path.stat().st_mtime
        if save and end_mtime <= start_mtime:
            raise DidNotSaveError
        edited_text = path.read_text(encoding=encoding)
    except subprocess.CalledProcessError as e:
        raise EditorError(f"{editor} exited with status {e.returncode}") from e
    finally:
        path.unlink(missing_ok=True)

    if required and edited_text == initial_text:
        raise DidNotChangeError

    return edited_text
