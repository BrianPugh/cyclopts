import arguably
import library_using_arguably  # noqa: F401


@arguably.command
def my_function(name):
    print(f"{name=}")


if __name__ == "__main__":
    arguably.run()
