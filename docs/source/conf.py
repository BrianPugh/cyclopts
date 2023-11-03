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

sys.path.insert(0, str(Path("../..").absolute()))


from pythontemplate import __version__

git_repo = git.Repo(".", search_parent_directories=True)  # type: ignore[reportPrivateImportUsage]
git_commit = git_repo.head.commit

# -- Project information -----------------------------------------------------

project = "pythontemplate"
copyright = f"{date.today().year}, YOUR_NAME_HERE"
author = "YOUR_NAME_HERE"

# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags
release = __version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx_rtd_theme",
    "sphinx.ext.autodoc",
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
    "members": True,
    "member-order": "bysource",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}
autoclass_content = "init"

# LinkCode
code_url = f"https://github.com/GIT_USERNAME/GIT_REPONAME/blob/{git_commit}"


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
    if file.parts[0] != "pythontemplate":
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
html_logo = "../../assets/logo_200w.png"
html_favicon = None

html_theme_options = {
    # "analytics_id": "G-XXXXXXXXXX",  # Provided by Google in your dashboard
    # "analytics_anonymize_ip": False,
    "logo_only": False,
    "display_version": False,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "vcs_pageview_mode": "",
    "style_nav_header_background": "white",
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
    "github_user": "GIT_USERNAME",
    "github_repo": "GIT_REPONAME",
    "github_version": "main",
    "conf_py_path": "/docs/source/",
}

html_css_files = [
    "custom.css",
]
