import typer

import cyclopts

typer_app = typer.Typer()


@typer_app.command()
def foo(favorite_numbers: list[int] | None = None):
    if favorite_numbers is None:
        favorite_numbers = [1, 2, 3]
    print(f"My favorite numbers are: {favorite_numbers}")


print("Typer with arguments:")
typer_app(["--favorite-numbers", "100", "--favorite-numbers", "200"], standalone_mode=False)
# My favorite numbers are: [100, 200]

print("Typer without arguments:")
typer_app([], standalone_mode=False)
# My favorite numbers are: []


cyclopts_app = cyclopts.App()


@cyclopts_app.default()
def foo(favorite_numbers: list[int] | None = None):
    if favorite_numbers is None:
        favorite_numbers = [1, 2, 3]
    print(f"My favorite numbers are: {favorite_numbers}")


print("Cyclopts with arguments:")
cyclopts_app(["--favorite-numbers", "100", "--favorite-numbers", "200"])
# My favorite numbers are: [100, 200]

print("Cyclopts without arguments:")
cyclopts_app([])
# My favorite numbers are: [1, 2, 3]

print("Cyclopts with --empty-favorite-numbers:")
cyclopts_app(["--empty-favorite-numbers"])
# My favorite numbers are: []
