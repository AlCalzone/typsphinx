# Sphinx configuration for label attachment integration testing

project = "Label Attachment Test"
author = "Test Author"
release = "1.0.0"

extensions = [
    "typsphinx",
]

typst_documents = [
    ("index", "index.typ", "Label Attachment Test", "Test Author"),
]
