# Sphinx configuration for cross-document reference integration testing

project = "Cross-Document Reference Test"
author = "Test Author"
release = "1.0.0"

extensions = [
    "typsphinx",
]

typst_documents = [
    ("index", "index.typ", "Cross-Document Reference Test", "Test Author"),
]
