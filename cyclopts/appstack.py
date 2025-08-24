from contextlib import contextmanager
from typing import TYPE_CHECKING, Optional, Sequence, TypeVar

from cyclopts.group_extractors import inverse_groups_from_app
from cyclopts.parameter import Parameter

if TYPE_CHECKING:
    from cyclopts.core import App


V = TypeVar("V")


class AppStack:
    def __init__(self, app):
        # the ``stack`` is guaranteed to have the self-referencing app at the top of the stack.
        self.stack: list[list[App]] = [[app]]

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

        so_far = []
        app_ids = {id(app) for app in apps}
        for app in apps:
            if app._meta_parent is None:
                # Do not include the prior meta-app.
                while so_far and so_far[-1]._meta_parent is not None:
                    so_far.pop()

            so_far.append(app)
            app.app_stack.stack.append(so_far.copy())

            # Also traverse the app's meta app
            meta_app = app
            while (meta_app := meta_app._meta) is not None:
                if id(meta_app) in app_ids:
                    # It will be handled conventionally
                    continue
                meta_subapps = so_far.copy()
                meta_subapps.append(meta_app)
                meta_app.app_stack.stack.append(meta_subapps)
        try:
            yield
        finally:
            for app in apps:
                app.app_stack.stack.pop()

    @property
    def default_parameter(self) -> Parameter:
        """default_parameter has special resolution since it needs to include the command groups in the derivation."""
        cparams = []
        for child_app in self.current_frame:
            if child_app._meta_parent:
                continue
            cparams.extend([group.default_parameter for group in child_app.app_stack.command_groups])
            cparams.append(child_app.default_parameter)

        return Parameter.combine(*cparams)

    @property
    def current_frame(self) -> list["App"]:
        if not self.stack:
            raise ValueError

        return self.stack[-1]

    def resolve(self, attribute, override: Optional[V] = None) -> Optional[V]:
        """Resolve an attribute from the App hierarchy."""
        if override is not None:
            return override

        # `reversed` so that "closer" apps have higher priority.
        for app in reversed(self.current_frame):
            result = getattr(app, attribute)
            if result is not None:
                return result

            # Check parenting meta app(s)
            meta_app = app
            while (meta_app := meta_app._meta_parent) is not None:
                result = getattr(meta_app, attribute)
                if result is not None:
                    return result

        return None

    @property
    def command_groups(self) -> list:
        command_app = self.current_frame[-1]
        try:
            current_app: Optional[App] = self.current_frame[-2]
        except IndexError:
            current_app = None

        while current_app is not None:
            try:
                return next(x for x in inverse_groups_from_app(current_app) if x[0] is command_app)[1]
            except StopIteration:
                current_app = current_app._meta_parent
        return []
