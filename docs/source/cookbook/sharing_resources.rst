=================
Sharing Resources
=================
Whether :ref:`Command Chaining` or using an :meth:`Interactive Shell <cyclopts.App.interactive_shell>`, it is common to instantiate expensive-to-create resources (such as a DB connection) and share them amongst commands in the same session.

.. code-block:: python
