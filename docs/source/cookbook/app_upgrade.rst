===========
App Upgrade
===========

It's best practice for users to install python-based CLIs via pipx_, where each application gets it's own python virtual environment.
Whether done via ``pipx`` or standard ``pip``, updating your application can be done via the ``upgrade`` command. i.e.:

.. code-block:: console

   $ pipx upgrade mypackage

If you would like your CLI application to be able to upgrade itself, you can add the following command to your application:

.. code-block:: python

   import mypackage
   import subprocess
   import sys


   @app.command
   def upgrade():
       """Update mypackage to latest stable version."""
       old_version = mypackage.__version__
       subprocess.check_output([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
       subprocess.check_output([sys.executable, "-m", "pip", "install", "--upgrade", "mypackage"])
       res = subprocess.run([sys.executable, "-m", "mypackage", "--version"], stdout=subprocess.PIPE, check=True)
       new_version = res.stdout.decode().strip()
       if old_version == new_version:
           print(f"mypackage up-to-date (v{new_version}).")
       else:
           print(f"mypackage updated from v{old_version} to v{new_version}.")

``sys.executable`` points to the currently used python interpreter's path; if your package was installed via pipx, then it points to the python interpreter in it's respective virtual environment.

.. _pipx: https://github.com/pypa/pipx
