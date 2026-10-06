=============
AI Assistants
=============
LLM coding assistants have seen far more Typer and Click code than Cyclopts code, so they tend to carry over habits that Cyclopts does not need: ``Parameter(help=...)`` instead of docstrings, ``Parameter(name=[...])`` instead of :attr:`~.Parameter.alias`, hand-written ``--version`` callbacks, and so on.
Cyclopts ships a short idiom sheet in the `Agent Skills <https://agentskills.io>`_ format that corrects these.
Once installed, the assistant loads it automatically whenever a task involves Cyclopts.

----------
Installing
----------
The `skills <https://github.com/vercel-labs/skills>`_ CLI detects which agents are installed (Claude Code, Codex, Cursor, GitHub Copilot, OpenCode, and many more) and installs into each:

.. code-block:: console

   $ npx skills add BrianPugh/cyclopts

Without Node, the ``cyclopts`` CLI can install the bundled copy itself.
The default destination is Claude Code's user-wide skills directory; ``--project`` targets the current repository, and ``--dest`` targets any directory:

.. code-block:: console

   $ cyclopts skill install
   $ cyclopts skill install --project
   $ cyclopts skill install --dest ~/.codex/skills/cyclopts

For tools that read a single rules file rather than a skills directory, print the skill and redirect it:

.. code-block:: console

   $ cyclopts skill show >> AGENTS.md

--------
llms.txt
--------
The documentation site publishes an `llms.txt <https://llmstxt.org>`_ index and a single-file concatenation of every page, for pointing an assistant at the docs directly:

* https://cyclopts.readthedocs.io/en/latest/llms.txt
* https://cyclopts.readthedocs.io/en/latest/llms-full.txt
