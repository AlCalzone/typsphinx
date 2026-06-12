"""
Post-transforms for the Typst builders.

This module maps sphinxcontrib-bibtex citations to Typst's native citation
system instead of letting Sphinx resolve them into plain docutils nodes:

- ``:cite:`` role ``pending_xref`` nodes become :class:`typst_cite` nodes,
  which the translator renders as ``cite(label("KEY"))``
- ``.. bibliography::`` directive nodes become a raw Typst
  ``bibliography(...)`` call referencing the configured ``.bib`` file(s),
  which Typst reads natively

sphinxcontrib-bibtex is entirely optional: all imports are guarded, and the
transform does nothing unless cite nodes are present in the document.
"""

import ast
from typing import Any

from docutils import nodes
from sphinx import addnodes
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util import logging

logger = logging.getLogger(__name__)


class typst_cite(nodes.Inline, nodes.Element):  # noqa: N801 (docutils node)
    """Placeholder for a native Typst citation.

    Created only for the typst builders by :class:`TypstCitationTransform`;
    other builders never see this node. The ``keys`` attribute holds the
    list of BibTeX citation keys.
    """


def _escape_string(text: str) -> str:
    """Escape text for use inside a Typst string literal."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


class TypstCitationTransform(SphinxPostTransform):
    """Convert sphinxcontrib-bibtex citations to Typst-native forms.

    Runs before Sphinx's ``ReferencesResolver`` (priority 10) and before
    sphinxcontrib-bibtex's ``BibliographyTransform`` (priority 5), so both
    the cite ``pending_xref`` nodes and the ``bibliography`` placeholder
    node are still intact.
    """

    default_priority = 1
    builders = ("typst", "typstpdf")

    def run(self, **kwargs: Any) -> None:
        self._convert_citations()
        self._convert_bibliographies()

    def _convert_citations(self) -> None:
        """Replace cite-domain pending_xref nodes with typst_cite nodes."""
        for node in list(self.document.findall(addnodes.pending_xref)):
            if node.get("refdomain") != "cite":
                continue
            keys = [
                key.strip()
                for key in node.get("reftarget", "").split(",")
                if key.strip()
            ]
            if keys:
                node.replace_self(typst_cite("", keys=keys))

    def _convert_bibliographies(self) -> None:
        """Replace bibliography directive nodes with Typst bibliography() calls."""
        try:
            from sphinxcontrib.bibtex.nodes import bibliography as bibliography_node
        except ImportError:
            return

        for node in list(self.document.findall(bibliography_node)):
            call = self._bibliography_call(node)
            if call:
                node.replace_self(nodes.raw("", call, format="typst"))
            else:
                node.parent.remove(node)

    def _bibliography_call(self, node: nodes.Element) -> str:
        """Build the Typst ``bibliography(...)`` call for a bibliography node.

        The ``.bib`` files come from the ``bibtex_bibfiles`` configuration;
        the builder copies them into the output directory, so they are
        referenced with root-relative Typst paths (``"/file.bib"``).
        """
        bibfiles = list(getattr(self.config, "bibtex_bibfiles", None) or [])
        if not bibfiles:
            logger.warning(
                "bibliography directive found but bibtex_bibfiles is empty; "
                "dropping it from the Typst output",
                location=node,
                type="typst",
            )
            return ""

        sources = ", ".join(f'"/{_escape_string(bibfile)}"' for bibfile in bibfiles)
        if len(bibfiles) > 1:
            sources = f"({sources})"

        # sphinxcontrib-bibtex lists only cited entries by default; the
        # ":all:" option (filter expression "True") lists every entry,
        # which maps to Typst's "full: true".
        full = "true" if self._lists_all_entries(node) else "false"

        # Note: the citation style is approximated. bibtex's default
        # "alpha"/"plain" styles number alphabetically, while Typst's
        # default "ieee" numbers in citation order.
        return f'bibliography({sources}, title: none, full: {full}, style: "ieee")\n\n'

    def _lists_all_entries(self, node: nodes.Element) -> bool:
        """Whether the bibliography directive used ``:all:`` (list everything)."""
        try:
            from sphinxcontrib.bibtex.directives import BibliographyKey

            domain = self.env.get_domain("cite")
            key = BibliographyKey(docname=node["docname"], id_=node["ids"][0])
            filter_ = domain.bibliographies[key].filter_
            return ast.unparse(filter_).strip() == "True"
        except Exception:
            return False
