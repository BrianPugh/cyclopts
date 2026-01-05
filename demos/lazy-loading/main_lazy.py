#!/usr/bin/env python3
"""Lazy loading example - imports deferred until command execution."""

from cyclopts import App

# No command imports here!

app = App(name="lazy-cli", help="Demo CLI with lazy imports.")

user_app = App(name="user", help="User management commands.")
user_app.command("commands.users:create")
user_app.command("commands.users:delete")
user_app.command("commands.users:list_users", name="list")

report_app = App(name="report", help="Report generation commands.")
report_app.command("commands.reports:generate")
report_app.command("commands.reports:schedule")

ml_app = App(name="ml", help="Machine learning commands.")
ml_app.command("commands.ml:train")
ml_app.command("commands.ml:predict")

app.command(user_app)
app.command(report_app)
app.command(ml_app)

if __name__ == "__main__":
    app()
