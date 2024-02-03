project = 'deadline-cloud-for-unreal-engine'
copyright = '2023, AWS Thinkbox'
author = 'AWS Thinkbox'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon']

templates_path = ['_templates']
exclude_patterns = []
autodoc_mock_imports = ["unreal", "deadline.client", "deadline.job_attachments"]
autodoc_member_order = 'bysource'
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "private-members": True
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']