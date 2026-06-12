"""
Sphinx post-transforms for the Typst builders.

This module converts ``:numref:`` pending_xref nodes into native Typst
references. Sphinx's own resolution substitutes literal text such as
"Fig. 1" computed from ``env.toc_fignumbers`` (HTML-style numbering),
which does not necessarily match the numbers the Typst template and
counters assign to figure and table captions. Emitting a native Typst
``ref(label("..."))`` instead lets Typst render the reference text
itself, so the reference and the caption numbering agree by
construction (Typst's default supplements "Figure"/"Table" also match
Sphinx's default ``numfig_format``).
"""

from typing import Any, Optional

from docutils import nodes
from sphinx import addnodes
from sphinx.transforms.post_transforms import SphinxPostTransform

#: Figure types that the Typst translator emits as labelled, captioned
#: ``figure(...)`` elements, i.e. targets Typst's ``ref()`` can resolve.
REFABLE_FIGTYPES = ("figure", "table")


class typst_ref(nodes.Inline, nodes.Element):  # noqa: N801 (docutils convention)
    """A native Typst reference, emitted as ``ref(label("<target>"))``."""


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

        Returns the label id if the target is a captioned figure or
        table (i.e. an element the translator emits with an attached
        Typst label), or ``None`` to fall back to Sphinx's default
        resolution.
        """
        labels = self.env.domaindata.get("std", {}).get("labels", {})
        if reftarget not in labels:
            return None
        docname, labelid = labels[reftarget][0], labels[reftarget][1]
        fignumbers = self.env.toc_fignumbers.get(docname, {})
        for figtype in REFABLE_FIGTYPES:
            if labelid in fignumbers.get(figtype, {}):
                return labelid
        return None
