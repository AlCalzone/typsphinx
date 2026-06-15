"""
Integration tests for cross-document references.

A reference from one document to a target in another document must become an
internal Typst label link (the master document compiles everything into a
single PDF), not a dead URL pointing at the generated output file
(e.g. link("chapter2.typ#anchor")).

Labels are qualified with the docname (e.g. <chapter2:anchor>) because Sphinx
ids are only unique per document, while Typst requires document-unique labels.
"""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def crossdoc_project_dir():
    """Return the path to the integration_crossdoc_refs test project."""
    return Path(__file__).parent / "fixtures" / "integration_crossdoc_refs"


@pytest.fixture
def temp_build_dir(tmp_path):
    """Provide a temporary directory for build output."""
    return tmp_path / "_build"


def build(project_dir, build_dir, builder="typst"):
    """Run sphinx-build for the given project and return the result."""
    result = subprocess.run(
        [
            "uv",
            "run",
            "sphinx-build",
            "-b",
            builder,
            str(project_dir),
            str(build_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"sphinx-build failed:\nSTDOUT:\n{result.stdout}\n" f"STDERR:\n{result.stderr}"
    )
    return result


class TestCrossDocumentReferences:
    """Cross-document :ref:/:doc: links resolve to internal Typst labels."""

    def test_crossdoc_ref_does_not_link_to_output_file(
        self, crossdoc_project_dir, temp_build_dir
    ):
        """:ref: to another document must not produce a file URL."""
        build(crossdoc_project_dir, temp_build_dir)

        content = (temp_build_dir / "chapter1.typ").read_text()

        # The broken output was: link("chapter2.typ#chapter2-section", ...)
        assert 'link("chapter2.typ' not in content

    def test_crossdoc_ref_uses_docname_qualified_label(
        self, crossdoc_project_dir, temp_build_dir
    ):
        """:ref: to another document links to a docname-qualified label."""
        build(crossdoc_project_dir, temp_build_dir)

        content = (temp_build_dir / "chapter1.typ").read_text()

        assert "link(<chapter2:chapter2-section>" in content

    def test_crossdoc_doc_role_links_to_document_label(
        self, crossdoc_project_dir, temp_build_dir
    ):
        """:doc: references link to a label marking the target document."""
        build(crossdoc_project_dir, temp_build_dir)

        chapter1 = (temp_build_dir / "chapter1.typ").read_text()
        chapter2 = (temp_build_dir / "chapter2.typ").read_text()

        assert "link(<chapter2>" in chapter1
        # The target document carries the matching anchor
        assert "<chapter2>" in chapter2

    def test_target_document_emits_qualified_anchor(
        self, crossdoc_project_dir, temp_build_dir
    ):
        """The referenced target emits the docname-qualified label."""
        build(crossdoc_project_dir, temp_build_dir)

        content = (temp_build_dir / "chapter2.typ").read_text()

        assert "<chapter2:chapter2-section>" in content

    def test_same_document_ref_links_to_label(
        self, crossdoc_project_dir, temp_build_dir
    ):
        """:ref: within the same document also uses the qualified label."""
        build(crossdoc_project_dir, temp_build_dir)

        content = (temp_build_dir / "chapter2.typ").read_text()

        assert "link(<chapter2:chapter2-section>" in content

    def test_crossdoc_ref_from_nested_document(
        self, crossdoc_project_dir, temp_build_dir
    ):
        """A nested document normalises ../ paths back to the docname."""
        build(crossdoc_project_dir, temp_build_dir)

        content = (temp_build_dir / "sub" / "extra.typ").read_text()

        # The broken output was: link("../chapter2.typ#chapter2-section", ...)
        assert 'link("../chapter2.typ' not in content
        assert "link(<chapter2:chapter2-section>" in content

    def test_crossdoc_refs_compile_to_pdf(self, crossdoc_project_dir, temp_build_dir):
        """The typstpdf builder compiles the project; all labels resolve."""
        result = build(crossdoc_project_dir, temp_build_dir, builder="typstpdf")

        assert (temp_build_dir / "index.pdf").exists()
        # typstpdf logs compilation failures instead of failing the build
        assert "Failed to compile" not in result.stdout
        assert "Failed to compile" not in result.stderr

        # Under typstpdf, get_target_uri appends .pdf - must not leak either
        chapter1 = (temp_build_dir / "chapter1.typ").read_text()
        assert 'link("chapter2.pdf' not in chapter1
