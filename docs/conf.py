#!/usr/bin/env python3

import os

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

extensions = []
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = 'temporal-django'
copyright = '2017, Clover Health Labs, LLC'

version = '0.0.1'
release = version
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

pygments_style = 'sphinx'

if not on_rtd:
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

html_static_path = ['_static']
htmlhelp_basename = 'temporal-djangodoc'
