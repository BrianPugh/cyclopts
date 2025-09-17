====
Help
====

A help screen is standard for every CLI application.
Cyclopts by-default adds ``--help`` and ``-h`` flags to the application:

.. code-block:: console

   $ my-application --help
   Usage: my-application COMMAND

   My application short description.

   ╭─ Commands ─────────────────────────────────────────────────────────╮
   │ foo        Foo help string.                                        │
   │ bar        Bar help string.                                        │
   │ --help -h  Display this message and exit.                          │
   │ --version  Display application version.                            │
   ╰────────────────────────────────────────────────────────────────────╯

Cyclopts derives the components of the help string from a variety of sources.
The source resolution order is as follows (as applicable):

1. The ``help`` field in the :meth:`@app.command <cyclopts.App.command>` decorator.

   .. code-block:: python

      app = cyclopts.App()


      @app.command(help="This is the highest precedence help-string for 'bar'.")
      def bar():
          pass

   When registering an :class:`.App` object, supplying ``help`` via the :meth:`@app.command <cyclopts.App.command>` decorator is forbidden to reduce ambiguity and will raise a :exc:`ValueError`. See (2).

2. Via :attr:`.App.help`.

   .. code-block:: python

      app = cyclopts.App(help="This help string has highest precedence at the app-level.")

      sub_app = cyclopts.App(help="This is the help string for the 'foo' subcommand.")
      app.command(sub_app, name="foo")
      app.command(sub_app, name="foo", help="This is illegal and raises a ValueError.")


3. The ``__doc__`` docstring of the registered :meth:`@app.default <cyclopts.App.default>` command.
   Cyclopts parses the docstring to populate short-descriptions and long-descriptions
   at the command-level, as well as at the parameter-level.

   .. code-block:: python

      app = cyclopts.App()
      app.command(cyclopts.App(), name="foo")


      @app.default
      def bar(val1: str):
          """This is the primary application docstring.

          Parameters
          ----------
          val1: str
              This will be parsed for val1 help-string.
          """


      @app["foo"].default  # You can access sub-apps like a dictionary.
      def foo_handler():
          """This will be shown for the "foo" command."""


4. This resolution order, but of the :ref:`Meta App`.

   .. code-block:: python

      app = cyclopts.App()


      @app.meta.default
      def bar():
          """This is the primary application docstring."""

-------------
Markup Format
-------------
While the standard markup language for docstrings in Python is reStructuredText (see `PEP-0287`_), Cyclopts defaults to Markdown for better readability and simplicity.
Cyclopts mostly respects `PEP-0257`_, but has some slight differences for developer ergonomics:

1. The "summary line" (AKA short-description) may actually be multiple lines. Cyclopts will unwrap the first block of text and interpret it as the short description. The first block of text ends at the first double-newline (i.e. a single blank line) is reached.

   .. code-block:: python

      def my_command():
          """
          This entire sentence
          is part of the short description and will
          have all the newlines removed.

          This is the beginning of the long description.
          """

2. If a docstring is provided with a long description, it **must** also have a short description.

By default, Cyclopts parses docstring descriptions as markdown and renders it appropriately.
To change the markup format, set the :attr:`.App.help_format` field accordingly. The different options are described below.

Subapps inherit their parent's :attr:`.App.help_format` unless explicitly overridden. I.e. you only need
to set :attr:`.App.help_format` in your main root application for all docstrings to be parsed appropriately.

^^^^^^^^^
PlainText
^^^^^^^^^
Do not perform any additional parsing, display supplied text as-is.

.. code-block:: python

   from cyclopts import App

   app = App(help_format="plaintext")

   @app.default
   def default():
       """My application summary.

       This is a pretty standard docstring; if there's a really long sentence
       I should probably wrap it because people don't like code that is more
       than 80 columns long.

       In this new paragraph, I would like to discuss the benefits of relaxing 80 cols to 120 cols.
       More text in this paragraph.

       Some new paragraph.
       """

   app()

.. code-block:: text

   Usage: default COMMAND

   My application summary.

   This is a pretty standard docstring; if there's a really long
   sentence
   I should probably wrap it because people don't like code that is
   more
   than 80 columns long.

   In this new paragraph, I would like to discuss the benefits of
   relaxing 80 cols to 120 cols.
   More text in this paragraph.

   Some new paragraph.

   ╭─ Commands ─────────────────────────────────────────────────────╮
   │ --help,-h  Display this message and exit.                      │
   │ --version  Display application version.                        │
   ╰────────────────────────────────────────────────────────────────╯

Most noteworthy, is **no additional text reflow is performed**; newlines are presented as-is.

^^^^
Rich
^^^^
Displays text as `Rich Markup`_.

.. note::

      Newlines are interpreted literally.

.. code-block:: python

   from cyclopts import App

   app = App(help_format="rich")

   @app.default
   def default():
      """Rich can display colors like [red]red[/red] easily.

      However, I cannot be bothered to figure out how to show that in documentation.
      """

   app()

.. raw:: html

   <div class="highlight-default notranslate">
         <pre style="font-family: 'JetBrains Mono', 'Fira Code', Monaco, Consolas, monospace;">Usage: default COMMAND

   Rich can display colors like <span style="color: #ff6666">red</span> easily.

   ╭─ Commands ───────────────────────────────────────────────────────╮
   │ <span style="color: #66b3ff">--help -h  </span>Display this message and exit.                        │
   │ <span style="color: #66b3ff">--version  </span>Display application version.                          │
   ╰──────────────────────────────────────────────────────────────────╯</pre>
   </div>

^^^^^^^^^^^^^^^^
ReStructuredText
^^^^^^^^^^^^^^^^
ReStructuredText can be enabled by setting `help_format` to "restructuredtext" or "rst".

.. code-block:: python

   app = App(help_format="restructuredtext")  # or "rst"

   @app.default
   def default():
       """My application summary.

       We can do RST things like have **bold text**.
       More words in this paragraph.

       This is a new paragraph with some bulletpoints below:

       * bullet point 1.
       * bullet point 2.
       """

   app()


Resulting help:

.. raw:: html

   <div class="highlight-default notranslate">
         <pre style="font-family: 'JetBrains Mono', 'Fira Code', Monaco, Consolas, monospace;">Usage: default COMMAND

   My application summary.

   We can do RST things like have <span style="font-weight: bold">bold text</span>. More words in this
   paragraph.

   This is a new paragraph with some bulletpoints below:

   1. bullet point 1.
   2. bullet point 2.

   ╭─ Commands ──────────────────────────────────────────────────────────╮
   │ <span style="color: #66b3ff">--help -h  </span>Display this message and exit.                           │
   │ <span style="color: #66b3ff">--version  </span>Display application version.                             │
   ╰─────────────────────────────────────────────────────────────────────╯
   </pre></div>

Under most circumstances, plaintext (without any additional markup) looks prettier and reflows better when interpreted as restructuredtext (or markdown, for that matter).

^^^^^^^^^
Markdown
^^^^^^^^^
Markdown is the default parsing behavior of Cyclopts, so `help_format` won't need to be explicitly set. It's another popular markup language that Cyclopts can render.

.. code-block:: python

   app = App(help_format="markdown")  # or "md"
   # or don't supply help_format at all; markdown is default.


   @app.default
   def default():
       """My application summary.

       We can do markdown things like have **bold text**.
       [Hyperlinks work as well.](https://cyclopts.readthedocs.io)
       """

Resulting help:

.. raw:: html

   <div class="highlight-default notranslate">
         <pre style="font-family: 'JetBrains Mono', 'Fira Code', Monaco, Consolas, monospace;">Usage: default COMMAND

   My application summary.

   We can do markdown things like have <span style="font-weight: bold">bold text</span>. <a href="https://cyclopts.readthedocs.io" style="color: #66b3ff">Hyperlinks work as well</a>.

   ╭─ Commands ──────────────────────────────────────────────────────────╮
   │ <span style="color: #66b3ff">--help -h  </span>Display this message and exit.                           │
   │ <span style="color: #66b3ff">--version  </span>Display application version.                             │
   ╰─────────────────────────────────────────────────────────────────────╯
   </pre></div>

----------
Help Flags
----------
The default ``--help`` flags can be changed to different name(s) via the ``help_flags`` parameter.

.. code-block:: python

   app = cyclopts.App(help_flags="--show-help")
   app = cyclopts.App(help_flags=["--send-help", "--send-help-plz", "-h"])

To disable the help-page entirely, set ``help_flags`` to an empty string or iterable.

.. code-block:: python

   app = cyclopts.App(help_flags="")
   app = cyclopts.App(help_flags=[])

--------------------
Help Customization
--------------------
For advanced customization of help screen appearance, including custom formatters,
styled panels, and dynamic column layouts, see :ref:`Help Customization`.


.. _PEP-0257: https://peps.python.org/pep-0257/
.. _PEP-0287: https://peps.python.org/pep-0287/
.. _Rich Markup: https://rich.readthedocs.io/en/stable/markup.html
