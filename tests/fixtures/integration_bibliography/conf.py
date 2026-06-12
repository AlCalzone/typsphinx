# Sphinx configuration for citation/bibliography integration testing

project = "Bibliography Test Project"
author = "Test Author"
release = "1.0.0"

extensions = [
    "typsphinx",
    "sphinxcontrib.bibtex",
]

bibtex_bibfiles = ["references.bib"]

typst_documents = [
    ("index", "index.typ", "Bibliography Test", "Test Author"),
]
