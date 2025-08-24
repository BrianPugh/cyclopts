from contextlib import contextmanager
from copy import copy
from typing import TYPE_CHECKING, Sequence

from cyclopts.parameter import Parameter

if TYPE_CHECKING:
    from cyclopts.core import App


class AppStack:
    def __init__(self):
        self.stack = []

    @contextmanager
    def __call__(self, apps: Sequence["App"]):
        apps = list(apps)

        if not apps:
            try:
                yield
            finally:
                pass
            return

        assert len(apps) >= 1

        app_ids = {id(app) for app in apps}
        for i, app in enumerate(apps):
            subapps = copy(apps[: i + 1])
            app.app_stack.stack.append(subapps)

            # Also traverse the app's meta app
            meta_app = app
            while (meta_app := meta_app._meta) is not None:
                if id(meta_app) in app_ids:
                    continue
                meta_subapps = subapps.copy()
                meta_subapps.append(meta_app)
                meta_app.app_stack.stack.append(meta_subapps)
        try:
            yield
        finally:
            for app in apps:
                app.app_stack.stack.pop()

    @property
    def default_parameter(self) -> Parameter:
        from .core import _get_command_groups  # TODO: cleanup

        if not self.stack:
            raise ValueError("AppStack.default_parameter must be accessed within app_stack context manager.")

        apps = self.stack[-1]
        cparams = []
        parent_app = None
        for child_app in apps:
            if child_app._meta_parent:
                continue
            # Resolve command-groups
            if parent_app is not None:  # The previous app might not strictly be a direct parent; could be a meta app.
                groups = _get_command_groups(parent_app, child_app)
                cparams.extend([group.default_parameter for group in groups])
            cparams.append(child_app.default_parameter)
            parent_app = child_app

        return Parameter.combine(*cparams)
