===========
Text Editor
===========
Some CLI programs require users to edit more complex fields in a text editor.
For example, ``git`` may open a text editor for the user when rebasing or editing a commit message.
While not directly related to CLI command parsing, Cyclopts provides :func:`cyclopts.edit` to satisfy this common need.

Here is an example application that mimics ``git commit`` functionality.

.. code-block:: python

   # git.py
   import cyclopts
   from textwrap import dedent
   import sys

   app = cyclopts.App(name="git")

   @app.command
   def commit():
       try:
           response = cyclopts.edit(  # blocks until text editor is closed.
               dedent(  # removes the  leading 4-tab indentation.
                   """\


                   # Please enter the commit message for your changes.Lines starting
                   # with '#' will be ignored, and an empty message aborts the commit.
                   """
               )
           )
       except (cyclopts.EditorDidNotSaveError, cyclopts.EditorDidNotChangeError):
           print("Aborting commit due to empty commit message.")
           sys.exit(1)
       filtered = "\n".join(x for x in response.split("\n") if not x.startswith("#"))
       filtered = filtered.strip()  # remove leading/trailing whitespace.
       print(f"Your commit message: {filtered}")

   if __name__ == "__main__":
       app()

Running ``python git.py commit`` will bring up a text editor with the pre-defined text, and then return the contents of the file.

See :func:`.edit` API page for more advanced usage.
