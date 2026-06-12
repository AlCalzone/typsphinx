# Minimal Sphinx configuration for inline/substitution image testing

project = "Inline Images Test"
author = "Test Author"
release = "1.0.0"

extensions = [
    "typsphinx",
]

typst_documents = [
    ("index", "index.typ", "Inline Images Test", "Test Author"),
]
