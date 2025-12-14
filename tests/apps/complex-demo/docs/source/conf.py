"""Sphinx configuration for Complex CLI documentation."""

import sys
from pathlib import Path

# Add the complex-demo directory to sys.path so we can import complex_app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

project = "Complex CLI"
copyright = "2024, Cyclopts"
author = "Cyclopts"

extensions = [
    "cyclopts.ext.sphinx",
    "sphinx.ext.autodoc",
]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "alabaster"
html_static_path = ["_static"]

# Suppress warnings about missing static paths
html_static_path = []
