# Sphinx configuration for numref cross-reference testing

project = "Numref Test"
author = "Test Author"
release = "1.0.0"

extensions = [
    "typsphinx",
]

# :numref: requires numbered figures
numfig = True

typst_documents = [
    ("index", "index.typ", "Numref Test", "Test Author"),
]
