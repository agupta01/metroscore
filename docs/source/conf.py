# ruff: noqa: INP001
"""
Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import logging
import os
import sys
from datetime import datetime

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

sys.path.insert(0, os.path.abspath("../../"))

from metroscore import VERSION, VERSION_SHORT  # noqa: E402

# -- Project information -----------------------------------------------------

project = "metroscore"
copyright = f"{datetime.today().year}, Arunav Gupta"
author = "Arunav Gupta"
version = VERSION_SHORT
release = VERSION

# mock import all required + optional dependency packages because readthedocs
# does not have them installed
autodoc_mock_imports = [
    "geopandas",
    "matplotlib",
    "osmnx",
    "networkx",
    "numpy",
    "pandas",
    "scipy",
    "shapely",
    "sklearn",
]

# linkcheck for stackoverflow gets HTTP 403 in CI environment
linkcheck_ignore = [r"https://stackoverflow\.com/.*"]

# type annotations configuration
autodoc_typehints = "description"
napoleon_use_param = True
napoleon_use_rtype = False
typehints_document_rtype = True
typehints_use_rtype = False
typehints_fully_qualified = False

# general configuration and options for HTML output
# see https://www.sphinx-doc.org/en/master/usage/configuration.html
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "myst_parser",
]
myst_heading_anchors = 3
suppress_warnings = ["myst.header"]
html_static_path = ["_static"]
html_theme = "sphinx_rtd_theme"
language = "en"
needs_sphinx = "7"  # same value as pinned in /docs/requirements.txt
root_doc = "index"
# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build"]

source_suffix = [".rst", ".md"]
templates_path: list[str] = []

# -- Hack to get rid of stupid warnings from sphinx_autodoc_typehints --------


class ShutupSphinxAutodocTypehintsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if "Cannot resolve forward reference" in record.msg:
            return False
        return True


logging.getLogger("sphinx.sphinx_autodoc_typehints").addFilter(
    ShutupSphinxAutodocTypehintsFilter()
)
