import arguably


@arguably.command
def ec2__start_instances(*instances):
    """Start instances.

    Args:
        *instances: {instance}s to start
    """
    for inst in instances:
        print(f"Starting {inst}")


@arguably.command
def ec2__stop_instances(*instances):
    """Stop instances.

    Args:
        *instances: {instance}s to stop
    """
    for inst in instances:
        print(f"Stopping {inst}")


if __name__ == "__main__":
    arguably.run()

from cyclopts import App

app = App()
app.command(ec2 := App(name="ec2"))


@ec2.command
def start_instances(*instances):
    """Start instances.

    Args:
        *instances: {instance}s to start
    """
    for inst in instances:
        print(f"Starting {inst}")


@ec2.command
def stop_instances(*instances):
    """Stop instances.

    Args:
        *instances: {instance}s to stop
    """
    for inst in instances:
        print(f"Stopping {inst}")


if __name__ == "__main__":
    app()
