# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------
import importlib
import inspect
import sys
from datetime import date
from pathlib import Path

import git
from sphinx.application import Sphinx
from sphinx.ext.autodoc import Options

from cyclopts import __version__

sys.path.insert(0, str(Path("../..").absolute()))


git_repo = git.Repo(".", search_parent_directories=True)  # type: ignore[reportPrivateImportUsage]
git_commit = git_repo.head.commit

# -- Project information -----------------------------------------------------

project = "cyclopts"
copyright = f"{date.today().year}, Brian Pugh"
author = "Brian Pugh"

# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags
release = __version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx_rtd_theme",
    "sphinx_rtd_dark_mode",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.linkcode",
    "sphinx_copybutton",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

smartquotes = False

# user starts in light mode
default_dark_mode = False

# Myst
myst_enable_extensions = [
    "linkify",
]

# Intersphinx
intersphinx_mapping = {
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "python": ("https://docs.python.org/3", None),
    "rich": ("https://rich.readthedocs.io/en/stable/", None),
    "typing_extensions": ("https://typing-extensions.readthedocs.io/en/latest/", None),
    "pytest": ("https://docs.pytest.org/en/latest", None),
}

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc
autodoc_default_options = {
    "member-order": "bysource",
    "undoc-members": False,
    "exclude-members": "__weakref__",
}
autoclass_content = "both"

# LinkCode
code_url = f"https://github.com/BrianPugh/cyclopts/blob/{git_commit}"


def linkcode_resolve(domain, info):
    """Link code to github.

    Modified from:
        https://github.com/python-websockets/websockets/blob/778a1ca6936ac67e7a3fe1bbe585db2eafeaa515/docs/conf.py#L100-L134
    """
    # Non-linkable objects from the starter kit in the tutorial.
    if domain == "js":
        return

    if domain != "py":
        raise ValueError("expected only Python objects")

    if not info.get("module"):
        # Documented via py:function::
        return

    mod = importlib.import_module(info["module"])
    if "." in info["fullname"]:
        objname, attrname = info["fullname"].split(".")
        obj = getattr(mod, objname)
        try:
            # object is a method of a class
            obj = getattr(obj, attrname)
        except AttributeError:
            # object is an attribute of a class
            return None
    else:
        obj = getattr(mod, info["fullname"])

    try:
        file = inspect.getsourcefile(obj)
        lines = inspect.getsourcelines(obj)
    except TypeError:
        # e.g. object is a typing.Union
        return None
    if file is None:
        return None
    file = Path(file).resolve().relative_to(git_repo.working_dir)
    if file.parts[0] != "cyclopts":
        # e.g. object is a typing.NewType
        return None
    start, end = lines[1], lines[1] + len(lines[0]) - 1

    return f"{code_url}/{file}#L{start}-L{end}"


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_title = project
html_logo = "../../assets/logo_512w.png"
html_favicon = "../../assets/favicon-192.png"

html_theme_options = {
    "logo_only": True,
    "version_selector": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "vcs_pageview_mode": "",
    "style_nav_header_background": "#F7E5B9",
    # Toc options
    "collapse_navigation": True,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
}

html_context = {
    # Github options
    "display_github": True,
    "github_user": "BrianPugh",
    "github_repo": "cyclopts",
    "github_version": "main",
    "conf_py_path": "/docs/source/",
}

html_css_files = [
    "custom.css",
]


# --- Other Custom Stuff


def simplify_exception_signature(
    app: Sphinx, what: str, name: str, obj, options: Options, signature, return_annotation
):
    # Check if the object is an exception and modify the signature
    if what == "exception" and isinstance(obj, type) and issubclass(obj, BaseException):
        return ("", None)  # Return an empty signature and no return annotation


def remove_attrs_methods(app, what, name, obj, options, lines):
    lines[:] = [line for line in lines if not line.startswith("Method generated by attrs for")]


def setup(app: Sphinx):
    app.connect("autodoc-process-signature", simplify_exception_signature)
    app.connect("autodoc-process-docstring", remove_attrs_methods)
