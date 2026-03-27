===========
Random Tips
===========
Improve discoverability by occasionally surfacing tips to users during normal CLI usage.

-----------
Basic Usage
-----------
Use a :ref:`Meta App` to display a random tip after each command invocation.
This keeps tip logic in one place rather than repeating it in every command.

.. code-block:: python

    import random
    import sys
    from typing import Annotated

    from cyclopts import App, Parameter

    app = App()

    tips = [
        "Use 'my-app config --help' to see all configuration options.",
        "Set the MY_APP_DEBUG=1 environment variable for verbose output.",
        "Commands can be abbreviated: 'my-app d' matches 'my-app deploy'.",
        "Suppress tips by setting MY_APP_NO_TIPS=1.",
    ]


    @app.command
    def build():
        """Build the project."""
        print("Building...")


    @app.command
    def deploy():
        """Deploy the project."""
        print("Deploying...")


    @app.meta.default
    def launcher(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        no_tips: Annotated[bool, Parameter(env_var="MY_APP_NO_TIPS", negative="")] = False,
    ):
        app(tokens)
        if not no_tips and random.random() < 0.3:
            print(f"\n💡 Tip: {random.choice(tips)}", file=sys.stderr)


    if __name__ == "__main__":
        app.meta()

.. code-block:: console

   $ python my-app.py build
   Building...

   💡 Tip: Set the MY_APP_DEBUG=1 environment variable for verbose output.

   $ MY_APP_NO_TIPS=1 python my-app.py build
   Building...
