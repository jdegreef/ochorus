"""The blocks a quote's `paragraph` index counts, as the reader serves them.

`Quote.paragraph` is `body.children[p]` — the 0-indexed top-level child the
reader's `?p=` jump lands on — counted AFTER `annotate_references`, the one
transform the chapter and sermon serializers apply to `body_html`. Two places
need that exact count and must never disagree: the context endpoint, which
shows a quote's paragraph, and `tests_quotes.QuoteResolutionTests`, which
gates every seeded quote against it. So it lives once, here.
"""

from __future__ import annotations


def served_block_texts(body_html: str) -> list[str]:
    """Each top-level block of the served body, as whitespace-collapsed text."""
    from bs4 import BeautifulSoup

    from .scripture import annotate_references

    root = BeautifulSoup(f"<div>{annotate_references(body_html)}</div>", "lxml").div
    return [" ".join(k.get_text().split()) for k in root.find_all(recursive=False)]
