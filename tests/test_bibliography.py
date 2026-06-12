"""
Integration tests for citation and bibliography support (sphinxcontrib-bibtex).

With sphinxcontrib-bibtex enabled, the typst builders should map:

- ``:cite:`` / ``:cite:p:`` roles to native Typst ``cite(label("KEY"))`` calls
- the ``.. bibliography::`` directive to a native Typst ``bibliography(...)`` call
- the configured ``.bib`` files must be copied next to the generated .typ files

sphinxcontrib-bibtex is an optional test dependency; these tests are skipped
when it is not installed.
"""

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("sphinxcontrib.bibtex")


@pytest.fixture(scope="module")
def bibliography_project_dir():
    """Return the path to the integration_bibliography test project."""
    return Path(__file__).parent / "fixtures" / "integration_bibliography"


@pytest.fixture(scope="module")
def built_project(bibliography_project_dir, tmp_path_factory):
    """Build the bibliography project once and return (build_dir, result)."""
    build_dir = tmp_path_factory.mktemp("bibliography") / "_build"
    result = subprocess.run(
        [
            "uv",
            "run",
            "sphinx-build",
            "-b",
            "typst",
            str(bibliography_project_dir),
            str(build_dir),
        ],
        capture_output=True,
        text=True,
    )
    return build_dir, result


class TestBibliographyBuild:
    """Building a project that uses sphinxcontrib-bibtex citations."""

    def test_build_succeeds_without_warnings(self, built_project):
        """The build must succeed and not emit warnings for cite nodes."""
        _build_dir, result = built_project
        assert result.returncode == 0, (
            f"sphinx-build failed:\nSTDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
        assert (
            "unknown node type" not in result.stderr
        ), f"translator hit unknown nodes:\n{result.stderr}"
        assert (
            "WARNING" not in result.stderr
        ), f"build emitted warnings:\n{result.stderr}"

    def test_citations_use_native_typst_cite(self, built_project):
        """:cite:/:cite:p: roles must become native Typst cite() calls."""
        build_dir, _result = built_project
        content = (build_dir / "index.typ").read_text(encoding="utf-8")
        assert 'cite(label("knuth1984"))' in content
        assert 'cite(label("lamport1994"))' in content

    def test_bibliography_directive_uses_native_typst_bibliography(self, built_project):
        """The bibliography directive must become a Typst bibliography() call."""
        build_dir, _result = built_project
        content = (build_dir / "index.typ").read_text(encoding="utf-8")
        assert 'bibliography("/references.bib"' in content

    def test_bib_file_copied_to_output(self, built_project):
        """The configured .bib file must be available in the output directory."""
        build_dir, _result = built_project
        bib_file = build_dir / "references.bib"
        assert bib_file.exists(), ".bib file should be copied to the output dir"
        assert "knuth1984" in bib_file.read_text(encoding="utf-8")

    @pytest.mark.integration
    def test_output_compiles_to_pdf(self, built_project):
        """The generated .typ file (with citations) must compile with Typst."""
        import typst

        build_dir, _result = built_project
        index_typ = build_dir / "index.typ"
        pdf_output = build_dir / "index.pdf"

        typst.compile(str(index_typ), output=str(pdf_output))

        assert pdf_output.exists(), "PDF file was not created"
        with open(pdf_output, "rb") as f:
            assert f.read(4) == b"%PDF", "Generated file is not a valid PDF"
