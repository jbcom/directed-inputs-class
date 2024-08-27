import os

project = "Extended Data Types"
author = "Jon Bogaty"
copyright = f"2024, {author}"
version = "0.1.0"

extensions = [
    "autodoc2",
    "sphinx.ext.githubpages",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

autodoc2_packages = [
    "../src/directed_inputs_class",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Default role
default_role = "any"

# HTML output settings
html_theme = "sphinxawesome_theme"
html_static_path = ["_static"]
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")

if os.environ.get("READTHEDOCS", "") == "True":
    html_context = {"READTHEDOCS": True}
else:
    html_context = {
        "display_github": True,
        "github_user": "jbcom",
        "github_repo": "directed-inputs-class",
        "github_version": "main",
    }

html_logo = "_static/logo.webp"

html_permalinks_icon = "<span>⚓</span>"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

nitpick_ignore = [
    ("py:class", "case_insensitive_dict.CaseInsensitiveDict"),
]
