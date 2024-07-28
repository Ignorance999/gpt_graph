# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "gpt_graph"
copyright = "2024, Ignorance999 @github"
author = "Ignorance999 @github"
release = "v0.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
# html_theme = 'alabaster'
html_static_path = ["_static"]
html_css_files = [
    "custom.css",
]

# %%
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))
sys.path.insert(0, os.path.abspath("."))

extensions = [
    "sphinx.ext.autodoc",  # Include documentation from docstrings
    "sphinx.ext.viewcode",  # Include links to source code
    "sphinx.ext.autosummary",
    "sphinx_ignore_ext",
    #'autoapi.extension',
    "myst_parser",
]
# autoapi_dirs = [
#    '../../gpt_graph',
# ]
# autoapi_options = ['members', 'undoc-members', 'private-members', 'special-members']
# autoapi_ignore = ['**/_*/']

# Add these lines to enable autosummary
autosummary_generate = True
# add_module_names = False

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
