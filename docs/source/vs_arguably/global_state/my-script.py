import arguably
import library_using_arguably


@arguably.command
def my_function(name):
    print(f"{name=}")


if __name__ == "__main__":
    arguably.run()
