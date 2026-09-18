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

# The two selectors qualified by KEEP_PREDICATES, named because each string is
# needed in two places and a typo between them would silently un-qualify the
# rule rather than fail.
NOTE_SELECTOR = "[class*=note i]"
PGINTERNAL_SELECTOR = "[class*=pginternal]"

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
    # markers left bare digits mid-sentence. Qualified — see KEEP_PREDICATES.
    NOTE_SELECTOR,
    "[class*=pg-boilerplate]",
    # Qualified too — see KEEP_PREDICATES.
    PGINTERNAL_SELECTOR,
    # Gutenberg's transcriber-correction markup ships the corrected word TWICE —
    # `<span class="htmlonly">view.</span><span class="epubonly"><a
    # class="pginternal">view.</a></span>` — one copy per output format. The web
    # reader wants the htmlonly copy, so the epub twin must go, or Brainerd's
    # diary reads "means I had in view.view.". The blanket pginternal drop hid
    # this by deleting the twin for the wrong reason.
    #
    # DROPPING is safe only because the twin always survives: this rule deletes
    # text, so a source that emitted the `epubonly` copy ALONE would lose it.
    # `scripts/audit_keep_predicates.py` measured the corpus — PG #65066 is the only
    # source using this markup, and its 49 `epubonly` spans are 49 `htmlonly`
    # pairs, none unpaired. Exact class, not a substring: this diff exists
    # because substring class matching over-matches, and `epubonly` needs no
    # slack.
    ".epubonly",
    # Some Gutenberg editions set an ornamental "CHAPTER N" line as its own
    # `<div class="chaptertitle">`, ABOVE the real `<h2>` title — the reader
    # already numbers chapters, so left in it opens every body "CHAPTER 1 …".
    # Qualified (see KEEP_PREDICATES): dropped only when the div is a bare
    # chapter/part/book label, never when it carries a real title.
    ".chaptertitle",
    "[id*=navbar]", "[id*=toc]",
]

# A `.chaptertitle` (or similar) whose whole text is just "CHAPTER 3" / "PART II"
# / "Book One" is furniture the reader re-derives; anything else is a real title.
_BARE_CHAPTER_LABEL = re.compile(
    r"^(?:chapter|part|book)\b\.?(?:\s+(?:[\divxlcdm]+|one|two|three|four|five|"
    r"six|seven|eight|nine|ten|eleven|twelve))?\.?$",
    re.I,
)


def _is_not_bare_chapter_label(el: Tag) -> bool:
    """Keep the element unless its entire text is a bare chapter-number label."""
    return not _BARE_CHAPTER_LABEL.match(el.get_text(" ", strip=True))

# Project Gutenberg puts `class="pginternal"` on EVERY internal link, so the
# class says nothing about what the link IS. Three kinds wear it: the TOC's page
# numbers, the "Contents" return links beside each chapter heading, and the
# author's own cross-references — Murray's "(Note A.)" pointing at his endnotes.
# A blanket drop selector deleted all three *with their text*, which is how
# `ministry-of-intercession` lost six `(Note A.)`…`(Note F.)` references to bare
# `()` and, where the anchor was a heading's only child, all six of its
# `NOTE A, Chap. VI.` headings (decompose emptied the <h4>, then the empty-block
# rule below swept it away). Those shipped rows were repaired by hand in #1561
# and #1562; this is the root cause, so it stops happening to the next import.
# Decide by the link's TEXT instead: navigation has none worth keeping, a
# cross-reference is prose.
# "Contents" / "Table of Contents", with or without a trailing period.
_PG_NAV_TEXT = re.compile(r"^(?:table\s+of\s+)?contents\.?$", re.I)
# A whole link that is only a mark: a table-of-contents page number ("73"), or a
# footnote marker — a bracketed number ("[1]"), a bare letter ("A") or a symbol
# ("°"), with or without brackets and a trailing period. The apparatus these
# point at does not survive the import, so keeping one leaves an orphan digit
# mid-sentence — which is what the drop selector was right about.
# `scripts/audit_keep_predicates.py` measured them: nineteen `[1]`…`[19]` markers in
# `the-life-of-trust`, five bare letters in `separation-and-service`, seven `°`
# in `selected-sermons-edwards`. Note the anchors on both ends of the pattern —
# a real cross-reference ("Note A.", "ch. 3", "p. xxix") carries a word, and is
# prose.
_PG_MARK_TEXT = re.compile(
    r"""^ [\[(]? \s*        # an optional opening bracket
        (?: \d+             # a page or footnote number: 73, 1, 19
          | [^\W\d_]        # exactly one letter: A, d, I
          | [^\w\s]{1,2}    # one or two symbols: °, *, †
        ) \s* [\])]? \.? $""",
    re.X,
)


# Gutenberg's OWN use of `class="note"` — the exact token, lowercase, and the
# one value in either transcriber's vocabulary that marks CONTENT rather than
# apparatus. `NoteSelectorTests.CCEL_APPARATUS` / `.PG_CHROME` hold the measured
# vocabularies (they fail the build; a comment cannot), and
# `scripts/audit_keep_predicates.py --rule note` is the corpus measurement.
#
# What the bare token carries: `holy-in-christ`'s seven `NOTE A.`–`NOTE G.`
# endnote headings and their subheadings, and — the one nobody had noticed —
# the SCRIPTURE TEXT of four Edwards sermons, so every one of them opened
# mid-argument with no text at all.
def _class_tokens(el: Tag) -> list[str]:
    """`class` as a token list, however the parser spelled it.

    BeautifulSoup gives a token list for parsed HTML but a bare string for a
    `class` set programmatically (and for the xml parser) — `_scrub_attrs` has
    always guarded that, and a predicate that forgets silently drops content.
    """
    raw = el.get("class") or []
    return raw if isinstance(raw, list) else str(raw).split()


def _is_gutenberg_note_content(el: Tag) -> bool:
    """True for an element the note selector matches but must NOT drop.

    Two conditions, and both are load-bearing:

    * the bare lowercase token `note` is present and NO OTHER token is itself
      note-ish. Token membership, not whole-attribute equality — Gutenberg
      combines a semantic token with a layout one (`footnote pgbrk` is in the
      measured vocabulary), so `class="note pgbrk"` is the same content as
      `class="note"` and equality would go on deleting it. The second half
      keeps `note footnote` on the apparatus side, and CCEL's capitalised
      `Note`/`NoteRef`/`Footnote` and lowercase `mnote` never match at all.
    * the element is not a bare MARK. Gutenberg also spells a footnote marker
      `<sup class="note">1</sup>`, and `sup` is allowlisted, so keeping one
      leaves an orphan digit mid-sentence with its note body dropped — the
      identical failure `_is_pg_navigation` exists to prevent, so it shares the
      same test.
    """
    tokens = _class_tokens(el)
    if "note" not in tokens or any("note" in t.lower() for t in tokens if t != "note"):
        return False
    return not _PG_MARK_TEXT.match(el.get_text(" ", strip=True))


def _is_pg_cross_reference(el: Tag) -> bool:
    """The keep half of :func:`_is_pg_navigation` — prose, not chrome."""
    return not _is_pg_navigation(el)


def _is_pg_navigation(el: Tag) -> bool:
    """True for a `pginternal` element that is chrome rather than prose.

    A bare page number or footnote marker, a "Contents" nav word, or no text at
    all. Anything else is the author's own cross-reference — or, in
    `the-life-of-trust`, a transcriber's corrected word sitting in the middle of
    Müller's sentence — and keeps its text.

    The empty case changes nothing for an `<a>`, which is outside both allowlists
    and unwraps to its (empty) text anyway. It is here for the tag that is IN
    one: an empty `<sup class="pginternal">` would otherwise survive as markup.
    """
    text = el.get_text(" ", strip=True)
    return not text or bool(_PG_MARK_TEXT.match(text) or _PG_NAV_TEXT.match(text))


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


# A drop selector whose match is not, by itself, proof of furniture: the
# predicate says which matches to KEEP, and everything else it matches is
# decomposed as before.
#
# Two selectors need one, for the same reason — each is a substring match
# written against ONE transcriber's class vocabulary, and each also matches
# another transcriber's legitimate prose. Both were found by measuring the
# corpus (`scripts/audit_keep_predicates.py`), not by reading the selector, and
# both had been silently deleting text for as long as they had existed. A third
# substring selector in the list above is a candidate for the same treatment the
# day someone measures it.
KEEP_PREDICATES = {
    NOTE_SELECTOR: _is_gutenberg_note_content,
    PGINTERNAL_SELECTOR: _is_pg_cross_reference,
    ".chaptertitle": _is_not_bare_chapter_label,
}


def drop_furniture(node: Tag) -> None:
    """Remove page furniture from `node`, in place — the whole drop policy.

    The importers run this pre-pass too (`import_ccel`, `build_ignatius`,
    `build_serious_call`), and they must get the SAME policy the sanitizer
    applies, which is why they call this rather than iterating `DROP_SELECTORS`
    themselves — `tests_sanitize` fails the build if one rots back to a bare
    loop.

    One rule the callers can't see: where a selector matches both a wrapper and
    something inside it, the wrapper is decomposed first and takes the inner
    element with it, so an ancestor's drop beats a descendant's keep.
    """
    for sel in DROP_SELECTORS:
        keep = KEEP_PREDICATES.get(sel)
        for el in node.select(sel):
            # `select` snapshots the tree, and one selector routinely matches
            # both a wrapper and what it wraps — CCEL's `div.footnotes` holds a
            # `span.mnote`, and both answer the note selector. Decomposing the
            # wrapper takes the descendant with it, leaving a decomposed tag in
            # this list; asking one anything raises. So an ancestor's drop wins
            # over a descendant's keep — right for apparatus, and the whole of
            # the contract (see the docstring).
            if el.decomposed or (keep is not None and keep(el)):
                continue
            el.decompose()


def _clean(node: Tag, *, allowed: set[str], allow_bio_attrs: bool) -> str:
    drop_furniture(node)
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
