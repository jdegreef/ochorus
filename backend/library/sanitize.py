"""The HTML sanitizer — the trust boundary behind every `{@html}` in the reader.

The reader renders stored content HTML directly (`Reader.svelte`, the chapter
page, `AuthorBioCard`), so whatever reaches these columns is what executes in a
reader's browser. Everything written to `Chapter.body_html`, `Sermon.body_html`,
`Author.bio_html` or `AuthorTranslation.bio_html` must come through here first.

Two profiles, because the two kinds of prose legitimately differ:

* :func:`clean_fragment` — chapter and sermon bodies. A narrow structural
  allowlist and **no attributes at all**. Imported book text needs nothing more,
  and the measured corpus agrees: across 3,033 stored rows there is not one
  attribute.

* :func:`clean_bio_html` — author biographies, which are authored (by the
  `write-biography` skill), not imported, and use three constructs the chapter
  profile has no reason to allow: ``<aside class="prayer">`` callouts,
  ``<cite>`` pull-quote attribution, and internal ``<a href="/authors/…">``
  links. Running the chapter profile over a biography would unwrap 323 asides,
  478 cites and 7 links across 172 files — deleting a feature, silently.

Both profiles are *value* sanitizers: they take HTML in and return safe HTML.
They are deliberately not wired into ``Model.save()``. That is tempting — it
would make the invariant structural — but BeautifulSoup round-trips character
entities (``&quot;`` becomes ``"``), which renders identically and is therefore
invisible, yet rewrites 743 of the 3,033 stored rows the first time each is
re-saved. A deploy that silently rewrites a quarter of the library is a worse
outcome than the one being prevented, so sanitizing happens at the write paths,
and `tests_sanitize.py` is what keeps them honest: it scans every stored row for
dangerous constructs, so a write path that forgets fails the build.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

# --- chapter / sermon profile ----------------------------------------------

# Tags kept in chapter bodies; everything else is unwrapped (text kept) or
# decomposed (dropped entirely — see DROP_SELECTORS).
ALLOWED_TAGS = {
    "p", "h2", "h3", "h4", "blockquote",
    "em", "strong", "i", "b", "br", "hr",
    "ul", "ol", "li", "sup",
}

# --- biography profile ------------------------------------------------------

# The chapter set plus the three constructs biographies actually use.
BIO_ALLOWED_TAGS = ALLOWED_TAGS | {"aside", "cite", "a"}

# `class` survives only on <aside>, and only these values — the callout styles
# the reader has CSS for. An arbitrary class is a styling hook, not content.
BIO_ASIDE_CLASSES = {"prayer", "prayer answered"}

# Schemes permitted in a biography link. A bare path ("/authors/…") is the only
# form in use today; https is allowed for citing a source. Everything else —
# `javascript:`, `data:`, `vbscript:` — is what this list exists to exclude.
BIO_URL_SCHEMES = {"https", "http"}

# Elements removed wholesale (chrome, page furniture, footnote machinery).
DROP_SELECTORS = [
    "script", "style", "nav", "header", "footer", "form", "button",
    "[class*=pagenum]", "[class*=pageno]", "[class*=page-num]",
    # CCEL marks a print page break with <span class="pb">17</span>. Left in,
    # the number lands mid-sentence (or alone at the top of a chapter) in a
    # reflowable reader. Exact selector — "pb" is too short to substring-match.
    "span.pb",
    "[class*=navbar i]", "[class*=toolbar i]",
    # CCEL's whole footnote apparatus: the note text (`class="Footnote"`) plus
    # the superscript markers that point at it (`Note`, `NoteRef`, `mnote`).
    # `i` = case-insensitive — a case-sensitive `[class*=footnote]` missed the
    # capitalised classes entirely and inlined note text into the prose
    # ("desires knowledge 2 Aristotle, Metaphysics, i. 1. ; but"), while the
    # markers left bare digits mid-sentence.
    "[class*=note i]",
    "[class*=pg-boilerplate]", "[class*=pginternal]",
    "[id*=navbar]", "[id*=toc]",
]

_PAGE_MARKER = re.compile(r"\[p\s*[ivxlcdm0-9]+\s*\]", re.I)
_WS = re.compile(r"\s+")


def _safe_bio_href(value: str) -> str | None:
    """The href to keep, or ``None`` to drop the attribute.

    Root-relative paths pass (the only form in the corpus). An absolute URL
    passes only on an allowlisted scheme. Anything else — including
    ``javascript:``/``data:`` and a scheme-relative ``//host`` that inherits the
    page's scheme — is dropped, leaving an inert ``<a>`` around its text.
    """
    href = (value or "").strip()
    if href.startswith("/") and not href.startswith("//"):
        return href
    scheme = urlparse(href).scheme.lower()
    return href if scheme in BIO_URL_SCHEMES else None


def _scrub_attrs(tag: Tag, *, allow_bio_attrs: bool) -> None:
    """Strip every attribute, keeping only the biography profile's two."""
    if not allow_bio_attrs:
        tag.attrs = {}
        return

    kept: dict[str, str] = {}
    if tag.name == "aside":
        raw = tag.get("class") or []
        # BeautifulSoup gives `class` as a token list; the reader's CSS keys off
        # the whole string ("prayer answered"), so compare the joined form.
        value = " ".join(raw) if isinstance(raw, list) else str(raw)
        if value in BIO_ASIDE_CLASSES:
            kept["class"] = value
    elif tag.name == "a":
        href = _safe_bio_href(tag.get("href", ""))
        if href:
            kept["href"] = href
    tag.attrs = kept


def _clean(node: Tag, *, allowed: set[str], allow_bio_attrs: bool) -> str:
    for sel in DROP_SELECTORS:
        for el in node.select(sel):
            el.decompose()
    for tag in node.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
        else:
            _scrub_attrs(tag, allow_bio_attrs=allow_bio_attrs)
    html = node.decode_contents() if isinstance(node, Tag) else str(node)
    html = _PAGE_MARKER.sub("", html)
    html = _WS.sub(" ", html)
    # Drop blocks left empty — including spacer paragraphs whose only content is
    # a <br> (CCEL uses <p><br/></p> for vertical space; in a reflowable reader
    # that renders as a ragged gap).
    html = re.sub(r"<(p|h2|h3|h4|blockquote|li)>(?:\s|<br\s*/?>)*</\1>", "", html)
    return html.strip()


def clean_html(node: Tag) -> str:
    """Reduce a parsed content node to safe, attribute-free HTML."""
    return _clean(node, allowed=ALLOWED_TAGS, allow_bio_attrs=False)


def clean_fragment(html: str) -> str:
    """Clean a raw HTML fragment string (re-parses it; non-mutating to caller)."""
    wrapper = BeautifulSoup(f"<div>{html}</div>", "lxml").div
    return clean_html(wrapper)


def clean_bio_html(html: str) -> str:
    """Clean an author biography fragment.

    As :func:`clean_fragment`, but keeps ``<aside>``/``<cite>``/``<a>`` and the
    two attributes a biography needs. Everything else — every other tag, every
    other attribute, every unsafe URL scheme — is removed exactly as above.
    """
    wrapper = BeautifulSoup(f"<div>{html}</div>", "lxml").div
    return _clean(wrapper, allowed=BIO_ALLOWED_TAGS, allow_bio_attrs=True)
