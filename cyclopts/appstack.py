from contextlib import contextmanager
from copy import copy
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from .core import App


@contextmanager
def app_stack(apps: Sequence["App"]):
    apps = list(apps)

    if not apps:
        try:
            yield
        finally:
            pass
        return

    # apps = _sort_apps(apps)
    assert len(apps) >= 1

    app_ids = {id(app) for app in apps}
    for i, app in enumerate(apps):
        # subapps = [x for x in apps[:i+1] if x._meta_parent is None]
        subapps = copy(apps[: i + 1])
        app._app_stack.append(subapps)

        # Also traverse the app's meta app
        meta_app = app
        while (meta_app := meta_app._meta) is not None:
            if id(meta_app) in app_ids:
                continue
            meta_subapps = subapps.copy()
            meta_subapps.append(meta_app)
            meta_app._app_stack.append(meta_subapps)
    try:
        yield
    finally:
        for app in apps:
            app._app_stack.pop()
