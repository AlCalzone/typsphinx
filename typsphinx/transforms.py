"""
Sphinx post-transforms for the Typst builders.

These transforms rewrite cross-reference and citation nodes into native
Typst constructs before Sphinx's own resolution runs, so the references and
the numbering/citations Typst renders agree by construction:

- ``:numref:`` ``pending_xref`` nodes become :class:`typst_ref` nodes, which
  the translator renders as ``ref(label("<target>"))`` (so Typst itself emits
  "Figure N"/"Table N" matching its own caption numbering, instead of
  Sphinx's HTML-style ``env.toc_fignumbers`` text).
- ``:cite:`` role ``pending_xref`` nodes become :class:`typst_cite` nodes,
  which the translator renders as ``cite(label("KEY"))``.
- ``.. bibliography::`` directive nodes become a raw Typst ``bibliography(...)``
  call referencing the configured ``.bib`` file(s), which Typst reads natively.

sphinxcontrib-bibtex is entirely optional: its imports are guarded, and the
citation transform does nothing unless cite nodes are present.
"""

import ast
from typing import Any, Optional

from docutils import nodes
from sphinx import addnodes
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util import logging

from typsphinx.translator import make_label

logger = logging.getLogger(__name__)

#: Figure types that the Typst translator emits as labelled, captioned
#: ``figure(...)`` elements, i.e. targets Typst's ``ref()`` can resolve.
REFABLE_FIGTYPES = ("figure", "table")


def _escape_string(text: str) -> str:
    """Escape text for use inside a Typst string literal."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


class typst_ref(nodes.Inline, nodes.Element):  # noqa: N801 (docutils convention)
    """A native Typst reference, emitted as ``ref(label("<target>"))``."""


class typst_cite(nodes.Inline, nodes.Element):  # noqa: N801 (docutils node)
    """Placeholder for a native Typst citation.

    Created only for the typst builders by :class:`TypstCitationTransform`;
    other builders never see this node. The ``keys`` attribute holds the
    list of BibTeX citation keys.
    """


class TypstNumrefTransform(SphinxPostTransform):
    """Convert ``numref`` pending_xref nodes to native Typst references.

    Runs only for the typst builders, with a priority below Sphinx's
    ReferencesResolver (priority 10) so the pending_xref nodes are still
    intact and no number text has been substituted yet.
    """

    default_priority = 5
    builders = ("typst", "typstpdf")

    def run(self, **kwargs: Any) -> None:
        for node in list(self.document.findall(addnodes.pending_xref)):
            if node.get("refdomain") != "std" or node.get("reftype") != "numref":
                continue
            if node.get("refexplicit"):
                # Explicit titles (":numref:`Custom %s <target>`") carry
                # a user-defined format string that native Typst refs
                # cannot reproduce; leave them to Sphinx's resolution.
                continue
            target = self._resolve_target(node.get("reftarget", ""))
            if target is not None:
                node.replace_self(typst_ref("", target=target))

    def _resolve_target(self, reftarget: str) -> Optional[str]:
        """Resolve a numref target to the label the translator attaches.

        Returns the docname-qualified label if the target is a captioned
        figure or table (i.e. an element the translator emits with an
        attached Typst label), or ``None`` to fall back to Sphinx's default
        resolution. The label is qualified with the *target's* docname (a
        numref may point into another document) so it matches the qualified
        label the translator emits for that figure/table.
        """
        labels = self.env.domaindata.get("std", {}).get("labels", {})
        if reftarget not in labels:
            return None
        docname, labelid = labels[reftarget][0], labels[reftarget][1]
        fignumbers = self.env.toc_fignumbers.get(docname, {})
        for figtype in REFABLE_FIGTYPES:
            if labelid in fignumbers.get(figtype, {}):
                return make_label(docname, labelid)
        return None


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
