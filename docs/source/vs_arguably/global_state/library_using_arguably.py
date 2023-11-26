import arguably


@arguably.command
def some_library_function(name):
    print(f"{name=}")


if __name__ == "__main__":
    arguably.run()
