#!/usr/bin/env python3
"""Eager loading example - all imports happen at startup."""

from commands.ml import predict, train
from commands.reports import generate, schedule

# These imports happen immediately - total ~4.5s delay before CLI is ready
from commands.users import create, delete, list_users

from cyclopts import App

app = App(name="eager-cli", help="Demo CLI with eager imports.")

user_app = App(name="user", help="User management commands.")
user_app.command(create)
user_app.command(delete)
user_app.command(list_users, name="list")

report_app = App(name="report", help="Report generation commands.")
report_app.command(generate)
report_app.command(schedule)

ml_app = App(name="ml", help="Machine learning commands.")
ml_app.command(train)
ml_app.command(predict)

app.command(user_app)
app.command(report_app)
app.command(ml_app)

if __name__ == "__main__":
    app()
