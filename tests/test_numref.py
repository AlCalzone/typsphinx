"""
Tests for :numref: cross-references rendered as native Typst references.

Sphinx's own ``:numref:`` resolution substitutes literal text such as
"Fig. 1" based on ``env.toc_fignumbers`` (HTML-style numbering), which
does not necessarily match the numbers Typst assigns to figure and table
captions. The typst builders therefore convert ``numref`` pending_xref
nodes to native Typst ``ref(label("..."))`` expressions so that the
reference text and the caption numbering agree by construction.
"""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def numref_build(tmp_path_factory):
    """Build the numref_refs fixture project once and return the outdir."""
    srcdir = Path(__file__).parent / "fixtures" / "numref_refs"
    outdir = tmp_path_factory.mktemp("numref_refs") / "_build"
    result = subprocess.run(
        [
            "uv",
            "run",
            "sphinx-build",
            "-b",
            "typst",
            str(srcdir),
            str(outdir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"sphinx-build failed:\nSTDOUT:\n{result.stdout}\n" f"STDERR:\n{result.stderr}"
    )
    return outdir


@pytest.fixture(scope="module")
def numref_output(numref_build):
    """Return the generated index.typ content."""
    return (numref_build / "index.typ").read_text(encoding="utf-8")


class TestNumrefNativeReferences:
    """:numref: should become native Typst ref() calls (figures/tables)."""

    def test_figure_numref_uses_native_ref(self, numref_output):
        """:numref:`fig-example` becomes ref() to the docname-qualified label."""
        assert 'ref(label("index:fig-example"))' in numref_output

    def test_table_numref_uses_native_ref(self, numref_output):
        """:numref:`tbl-example` becomes ref() to the docname-qualified label."""
        assert 'ref(label("index:tbl-example"))' in numref_output

    def test_no_hardcoded_fignumber_text(self, numref_output):
        """Sphinx's substituted "Fig. 1"/"Table 1" text must not appear."""
        assert 'text("Fig. 1")' not in numref_output
        assert 'text("Table 1")' not in numref_output

    def test_figure_label_is_attached(self, numref_output):
        """The figure must carry the (docname-qualified) label the ref() points to."""
        assert "<index:fig-example>" in numref_output

    def test_table_label_is_attached(self, numref_output):
        """The table must carry the (docname-qualified) label the ref() points to."""
        assert "<index:tbl-example>" in numref_output

    def test_explicit_title_keeps_text_substitution(self, numref_output):
        """:numref:`Custom figure %s <fig>` keeps Sphinx's substitution."""
        assert 'text("Custom figure 1")' in numref_output


class TestNumrefCompilation:
    """The generated document must compile, proving the refs resolve."""

    def test_typ_compiles_and_refs_resolve(self, numref_build):
        """Typst fails on unresolved labels, so compiling proves them."""
        typst = pytest.importorskip("typst")

        pdf_path = numref_build / "index.pdf"
        # typst.compile raises on any error, including unresolved
        # ref()/label() pairs
        typst.compile(
            str(numref_build / "index.typ"),
            output=str(pdf_path),
            root=str(numref_build),
        )
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
