"""User management commands."""

import time

# Simulate expensive import (e.g., ORM, authentication library)
print("[users.py] Importing user module... (simulating 1s delay)")
time.sleep(1)
print("[users.py] Import complete!")


def create(name: str, email: str, *, admin: bool = False):
    """Create a new user account.

    Parameters
    ----------
    name
        Full name of the user.
    email
        Email address for the account.
    admin
        Grant administrator privileges.
    """
    role = "admin" if admin else "user"
    print(f"Created user: {name} <{email}> ({role})")


def delete(username: str, *, force: bool = False):
    """Delete a user account.

    Parameters
    ----------
    username
        Username to delete.
    force
        Skip confirmation prompt.
    """
    print(f"Deleted user: {username} (force={force})")


def list_users(*, limit: int = 10):
    """List all user accounts.

    Parameters
    ----------
    limit
        Maximum number of users to display.
    """
    print(f"Listing up to {limit} users...")
