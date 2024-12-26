import sys
from pathlib import Path

src_deadline_path = str(Path(__file__).parent.parent.parent) + "/src/deadline"
sys.path.insert(0, src_deadline_path)

project = "deadline-cloud-for-unreal-engine"
copyright = "2024, Amazon.com"
author = "Amazon.com"
release = "0.3.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]

templates_path = ["_templates"]
exclude_patterns = []
autodoc_mock_imports = ["unreal", "deadline.client", "deadline.job_attachments", "openjd", "P4"]
autodoc_member_order = "bysource"
autodoc_default_options = {"members": True, "undoc-members": True, "private-members": True}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
