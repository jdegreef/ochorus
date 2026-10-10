"""The sanitizer is a trust boundary — these tests are what keep it one.

Three jobs:

1. **Hostile input is neutralised** by both profiles. Every case here is a real
   XSS shape, not a formality.
2. **Legitimate biography markup survives.** ``clean_bio_html`` exists because
   the chapter allowlist would unwrap 323 ``<aside class="prayer">`` callouts,
   478 ``<cite>`` attributions and 7 internal links across 172 files. Anyone who
   "simplifies" the two profiles into one deletes a feature silently, so that
   loss is asserted here directly.
3. **The stored corpus is clean.** The profiles only help at the write paths
   that call them, and a new write path can forget — the way four of them had.
   :class:`StoredContentIsSafeTests` scans every shipped row instead of trusting
   the call sites, so a dangerous construct fails the build wherever it entered.

Note the deliberate absence of a `Model.save()` hook. Sanitizing on save would
make the invariant structural, but BeautifulSoup round-trips character entities
(``&quot;`` → ``"``), which renders identically and so is invisible, yet
rewrites 743 of the 3,033 stored rows the first time each is re-saved. A deploy
that silently rewrites a quarter of the library is worse than the problem. See
library/sanitize.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from django.test import TestCase

from library.sanitize import clean_bio_html, clean_fragment

CONTENT_ROOT = Path(__file__).resolve().parent / "fixtures" / "content"
BIO_ROOT = Path(__file__).resolve().parent / "migrations" / "data"

# Constructs that must never reach a column the reader renders with {@html}.
# Deliberately shallow and syntactic: this is a tripwire over shipped data, not
# a parser. A false positive here is cheap; a miss is stored XSS.
DANGEROUS = (
    (re.compile(r"<\s*script\b", re.I), "<script>"),
    (re.compile(r"<\s*iframe\b", re.I), "<iframe>"),
    (re.compile(r"<\s*object\b", re.I), "<object>"),
    (re.compile(r"<\s*embed\b", re.I), "<embed>"),
    (re.compile(r"<\s*form\b", re.I), "<form>"),
    (re.compile(r"<\s*svg\b", re.I), "<svg>"),
    (re.compile(r"<\s*style\b", re.I), "<style>"),
    (re.compile(r"\son[a-z]+\s*=", re.I), "an on* event handler"),
    (re.compile(r"javascript\s*:", re.I), "a javascript: URL"),
    (re.compile(r"srcdoc\s*=", re.I), "srcdoc="),
)

ATTACKS = [
    "<script>alert(1)</script><p>ok</p>",
    '<p onclick="alert(1)">click</p>',
    "<img src=x onerror=alert(1)>",
    '<iframe src="https://evil.test"></iframe>',
    '<object data="evil.swf"></object>',
    "<svg><use href='#x'/></svg>",
    '<style>body{display:none}</style>',
    '<form action="https://evil.test"><input name="pw"></form>',
    '<p style="position:fixed;inset:0;z-index:9999">overlay</p>',
    '<a href="javascript:alert(1)">x</a>',
    '<a href="data:text/html,<script>alert(1)</script>">x</a>',
    # An allowlisted illustration still loses every attribute but its own.
    '<img src="/illustrations/a/b.webp" alt="x" onerror="alert(1)">',
    '<figure><img src="javascript:alert(1)" alt="x"></figure>',
]


def _dangerous_findings(html: str) -> list[str]:
    return [label for pattern, label in DANGEROUS if pattern.search(html)]


class SanitizerNeutralisesAttacksTests(TestCase):
    def test_chapter_profile_neutralises_every_attack(self):
        for attack in ATTACKS:
            with self.subTest(attack=attack):
                self.assertEqual(_dangerous_findings(clean_fragment(attack)), [])

    def test_bio_profile_neutralises_every_attack(self):
        for attack in ATTACKS:
            with self.subTest(attack=attack):
                self.assertEqual(_dangerous_findings(clean_bio_html(attack)), [])

    def test_chapter_profile_keeps_no_attributes_at_all(self):
        """The measured corpus has zero attributes, and the profile keeps it so."""
        out = clean_fragment('<p class="x" id="y" data-z="1" title="t">text</p>')
        self.assertEqual(out, "<p>text</p>")

    def test_unsafe_url_schemes_are_dropped_but_text_survives(self):
        for href in (
            "javascript:alert(1)",
            "data:text/html,<b>x</b>",
            "vbscript:msgbox(1)",
            "//evil.test/phish",  # scheme-relative inherits the page's scheme
        ):
            with self.subTest(href=href):
                out = clean_bio_html(f'<a href="{href}">read</a>')
                self.assertNotIn("href", out)
                self.assertIn("read", out)

    def test_sanitizing_is_idempotent(self):
        """A second pass must be a no-op, or repeated writes would churn content."""
        for raw in ATTACKS + ['<aside class="prayer">p</aside><cite>A</cite>']:
            with self.subTest(raw=raw):
                for clean in (clean_fragment, clean_bio_html):
                    once = clean(raw)
                    self.assertEqual(clean(once), once)


class BiographyMarkupSurvivesTests(TestCase):
    """Guards the reason the two profiles are separate."""

    def test_prayer_callouts_survive_with_their_class(self):
        for value in ("prayer", "prayer answered"):
            with self.subTest(value=value):
                out = clean_bio_html(f'<aside class="{value}">Lord, teach us.</aside>')
                self.assertEqual(out, f'<aside class="{value}">Lord, teach us.</aside>')

    def test_unknown_aside_class_is_dropped_but_the_aside_stays(self):
        out = clean_bio_html('<aside class="injected-style">text</aside>')
        self.assertEqual(out, "<aside>text</aside>")

    def test_pull_quote_attribution_and_internal_links_survive(self):
        out = clean_bio_html(
            '<blockquote>Prayer is the mightier.</blockquote>'
            '<cite>Susanna Wesley</cite>'
            '<a href="/authors/susanna-wesley/">her page</a>'
        )
        self.assertIn("<cite>Susanna Wesley</cite>", out)
        self.assertIn('<a href="/authors/susanna-wesley/">', out)

    def test_chapter_profile_would_destroy_biography_markup(self):
        """Why the profiles must not be merged — stated as an assertion."""
        bio = '<aside class="prayer">p</aside><cite>A</cite><a href="/x/">l</a>'
        stripped = clean_fragment(bio)
        for tag in ("<aside", "<cite", "<a "):
            self.assertNotIn(tag, stripped)


ILLUSTRATIONS_ROOT = (
    Path(__file__).resolve().parents[2] / "frontend" / "static" / "illustrations"
)
_IMG = re.compile(r"<img\b[^>]*>", re.I)
_ATTR = re.compile(r'([a-z]+)=(?:"([^"]*)"|\'([^\']*)\')', re.I)


class IllustrationMarkupTests(TestCase):
    """In-book images: the one place the chapter profile keeps attributes."""

    SRC = "/illustrations/the-princess-and-the-goblin/goblins.webp"

    def test_a_figure_survives_with_only_its_own_attributes(self):
        out = clean_fragment(
            f'<figure class="x"><img src="{self.SRC}" alt="The goblins" width="454" '
            'height="600" style="x" srcset="https://evil.test/a.png 2x" title="t">'
            '<figcaption id="c">The goblins <em>fell</em> back.</figcaption></figure>'
        )
        self.assertEqual(
            out,
            '<figure><img alt="The goblins" decoding="async" height="600" '
            f'loading="lazy" src="{self.SRC}" width="454"/>'
            "<figcaption>The goblins <em>fell</em> back.</figcaption></figure>",
        )

    def test_an_image_from_anywhere_else_is_dropped(self):
        for src in (
            "https://evil.test/x.webp",
            "//evil.test/x.webp",
            "images/col01.jpg",  # a Gutenberg relative path
            "/covers/x.webp",
            "/illustrations/a/../../b.webp",
            "/illustrations/a/b.svg",
            "/illustrations/A/b.webp",
            "data:image/png;base64,AAAA",
        ):
            with self.subTest(src=src):
                self.assertNotIn("<img", clean_fragment(f'<img src="{src}" alt="x">'))

    def test_an_image_without_alt_text_is_dropped(self):
        for alt in ("", "   "):
            with self.subTest(alt=alt):
                self.assertEqual(clean_fragment(f'<img src="{self.SRC}" alt="{alt}">'), "")

    def test_nonsense_dimensions_are_dropped_not_kept(self):
        out = clean_fragment(f'<img src="{self.SRC}" alt="x" width="100%" height="99999">')
        self.assertNotIn("width", out)
        self.assertNotIn("height", out)

    def test_a_figure_without_a_usable_image_cleans_as_it_always_did(self):
        """Imports that never had allowlisted images must not change."""
        raw = (
            '<figure><img src="images/col01.jpg" alt="x">'
            "<figcaption>She ran.</figcaption></figure><p>Text.</p>"
        )
        self.assertEqual(clean_fragment(raw), "She ran.<p>Text.</p>")
        self.assertEqual(clean_fragment("<figcaption>stray</figcaption>"), "stray")

    def test_both_profiles_allow_illustrations(self):
        raw = f'<figure><img src="{self.SRC}" alt="x"></figure>'
        self.assertEqual(clean_bio_html(raw), clean_fragment(raw))
        self.assertIn("<img", clean_bio_html(raw))

    def test_illustrations_are_idempotent(self):
        raw = (
            f'<figure><img src="{self.SRC}" alt=\'Said "hi" &amp; left\' width="10">'
            "<figcaption>c</figcaption></figure>"
        )
        once = clean_fragment(raw)
        self.assertEqual(clean_fragment(once), once)


class GutenbergInternalLinkTests(TestCase):
    """`class="pginternal"` is not evidence about what a link IS.

    Project Gutenberg puts it on every internal link — TOC page numbers, the
    "Contents" return links, and the author's own cross-references alike — so
    the drop selector that once matched it deleted prose. `<a>` is outside the
    chapter allowlist, so a cross-reference must lose its TAG and keep its TEXT,
    exactly as any other anchor does; navigation must lose both.

    Three kinds wear the class in PG #29296 (`ministry-of-intercession`): the
    "Contents" toclinks beside each chapter heading, the table of contents' page
    numbers, and Murray's own cross-references. The third kind is what this
    pins — six of them shipped as bare `()` and six more as headings that
    vanished entirely (decompose emptied the `<h4>`, then the empty-block rule
    swept it away), and `corrections.py` still carries the string pairs that
    repaired them.
    """

    def test_cross_reference_keeps_its_text_like_any_other_anchor(self):
        marked = '<p>May God discover this to us. (<a class="pginternal" href="#nt.A">Note A.</a>)</p>'
        plain = '<p>May God discover this to us. (<a href="#nt.A">Note A.</a>)</p>'
        self.assertEqual(clean_fragment(marked), clean_fragment(plain))
        self.assertEqual(
            clean_fragment(marked),
            "<p>May God discover this to us. (Note A.)</p>",
        )

    def test_a_heading_that_is_only_a_cross_reference_survives(self):
        """The second symptom: an emptied block was then swept as an empty one."""
        out = clean_fragment(
            '<h4><a class="pginternal" href="#nt.A">NOTE A, Chap. VI. p. 73</a></h4>'
            "<p>The word of God.</p>"
        )
        self.assertEqual(out, "<h4>NOTE A, Chap. VI. p. 73</h4><p>The word of God.</p>")

    def test_navigation_links_lose_their_text_too(self):
        for nav in (
            '<a class="pginternal" href="#toc">Contents</a>',
            '<a class="pginternal" href="#toc">Table of Contents</a>',
            '<a class="pginternal" href="#toc">CONTENTS.</a>',
            '<a class="pginternal" href="#pg73">73</a>',  # a TOC page number
            '<a class="pginternal" id="nt.A"></a>',  # a bare anchor target
        ):
            with self.subTest(nav=nav):
                self.assertEqual(clean_fragment(f"<p>before{nav}after</p>"),
                                 "<p>beforeafter</p>")

    def test_bare_footnote_markers_are_still_dropped(self):
        """The other half of the predicate — what must NOT start leaking.

        Gutenberg spells a footnote marker as an internal link too, and its note
        body does not survive the import, so a kept marker is an orphan digit
        mid-sentence. `scripts/audit_keep_predicates.py` measured the exposure:
        nineteen `[1]`…`[19]` in `the-life-of-trust`, five bare letters in
        `separation-and-service`.
        """
        for marker in ("[1]", "[19]", "(3)", "A", "d", "I", "7.", "°", "*", "†"):
            with self.subTest(marker=marker):
                out = clean_fragment(
                    f'<p>a work of faith<a class="pginternal" href="#Footnote_1">'
                    f"{marker}</a> and prayer.</p>"
                )
                self.assertEqual(out, "<p>a work of faith and prayer.</p>")

    def test_a_transcribers_corrected_word_stays_in_the_sentence(self):
        """`the-life-of-trust` wraps the corrected word itself in the anchor."""
        out = clean_fragment(
            '<p>at the <a class="pginternal" href="#corrections">commencement</a> '
            "of the work</p>"
        )
        self.assertEqual(out, "<p>at the commencement of the work</p>")

    def test_the_epub_twin_of_a_corrected_word_does_not_double_it(self):
        """PG #65066 ships each transcriber correction once per output format.

        The blanket drop deleted the epub twin as a side effect of its class;
        the drop selector now removes it for the right reason, so Brainerd's
        diary does not read "means I had in view.view.".
        """
        out = clean_fragment(
            "<p>means I had in "
            '<span class="htmlonly"><ins class="correction">view.</ins></span>'
            '<span class="epubonly"><a class="pginternal" href="#c_16.1">'
            '<ins class="correction">view.</ins></a></span></p>'
        )
        self.assertEqual(out, "<p>means I had in view.</p>")

    def test_a_chapter_heading_that_is_only_a_toclink_still_goes(self):
        """Nothing above resurrects the "Contents" chrome beside each heading."""
        out = clean_fragment(
            '<h2>CHAPTER VI<small class="toclink">'
            '<a class="pginternal" href="#toc">Contents</a></small></h2>'
        )
        self.assertEqual(out, "<h2>CHAPTER VI</h2>")


class NoteSelectorTests(TestCase):
    """`[class*=note i]` was the second selector matching two vocabularies.

    Written for CCEL's footnote apparatus, it also substring-matched Gutenberg's
    own `class="note"` — which Gutenberg uses for CONTENT. It had been deleting
    `holy-in-christ`'s seven `NOTE A.`–`NOTE G.` endnote headings (leaving ch33
    as 42 KB of prose with bare `<hr/>`s and no headings at all) and, unnoticed
    until the corpus was measured, the SCRIPTURE TEXT of four Edwards sermons,
    so each opened mid-argument with no text.

    The two vocabularies never collide on one class value, which is what makes
    the fix a rule rather than a guess — so both halves are pinned here from the
    measured corpus. If a transcriber ever does collide, this is what fails.
    """

    # Measured over the CCEL corpus: 576 matched elements, 8 shapes, all of them
    # genuine footnote apparatus that must keep being dropped.
    CCEL_APPARATUS = (
        "NoteRef", "Footnote", "Note", "mnote",
        "footer_note", "footnotes", "footnotes-hr",
    )
    # `footnotes` is in the CCEL tuple above and deliberately not repeated here.
    # Gutenberg's own chrome — transcriber's notes and footnote blocks. Dropped
    # as before: the markers pointing into them are dropped too, so keeping the
    # blocks would orphan the note text.
    PG_CHROME = (
        "tnote", "tnotes", "trans_note", "transnote", "notebox",
        "footnote", "footnote pgbrk", "footnotes",
    )

    def test_ccel_footnote_apparatus_is_still_dropped(self):
        for value in self.CCEL_APPARATUS:
            with self.subTest(value=value):
                out = clean_fragment(f'<p>prose<span class="{value}">x</span></p>')
                self.assertEqual(out, "<p>prose</p>")

    def test_gutenberg_note_chrome_is_still_dropped(self):
        for value in self.PG_CHROME:
            with self.subTest(value=value):
                out = clean_fragment(f'<p>prose</p><div class="{value}">x</div>')
                self.assertEqual(out, "<p>prose</p>")

    def test_gutenbergs_own_note_headings_survive(self):
        """`holy-in-christ` ch33 — a heading and its subheading, both kept."""
        out = clean_fragment(
            '<h3 class="note"><a id="note_A">NOTE A.</a></h3>'
            '<h4 class="note">Holiness as Proprietorship.</h4>'
            "<p>The word rendered holy.</p>"
        )
        self.assertEqual(
            out,
            "<h3>NOTE A.</h3><h4>Holiness as Proprietorship.</h4>"
            "<p>The word rendered holy.</p>",
        )

    def test_a_sermons_scripture_text_survives(self):
        """`selected-sermons-edwards` sets each sermon's TEXT as `p.note`."""
        out = clean_fragment(
            '<p class="note">1 Cor. i. 29-31.—That no flesh should glory in his '
            "presence.</p><p>Those Christians to whom the apostle wrote.</p>"
        )
        self.assertIn("That no flesh should glory in his presence.", out)

    def test_a_wrapper_and_its_nested_match_do_not_crash(self):
        """One selector matches a wrapper AND what it wraps.

        CCEL's `div.footnotes` holds a `span.mnote`; both answer
        `[class*=note i]`, and `select` hands back both. Decomposing the wrapper
        detaches the inner one, and a decomposed tag has no `attrs` — so a
        keep-predicate that asks it anything raises `AttributeError`. The
        unconditional `decompose()` this replaced never had to care. Found by
        running the corpus, not by reading the code.
        """
        out = clean_fragment(
            "<p>prose</p>"
            '<div class="footnotes">'
            '<span class="mnote">3 Literally, "is greatly blasphemed."</span>'
            '<div class="footer_note">4 A second note.</div>'
            "</div>"
        )
        self.assertEqual(out, "<p>prose</p>")

    def test_a_layout_token_beside_the_semantic_one_still_counts_as_content(self):
        """Token membership, not whole-attribute equality.

        Gutenberg combines a semantic token with a layout one — `footnote pgbrk`
        is in the measured vocabulary — so `class="note pgbrk"` is the same
        content as `class="note"`. Comparing the whole attribute went on
        deleting these.
        """
        for value in ("note pgbrk", "note c009", "pgbrk note"):
            with self.subTest(value=value):
                out = clean_fragment(f'<h3 class="{value}">NOTE A.</h3><p>b</p>')
                self.assertEqual(out, "<h3>NOTE A.</h3><p>b</p>")

    def test_a_second_note_ish_token_puts_it_back_on_the_apparatus_side(self):
        for value in ("note footnote", "note mnote", "notes", "note-ref"):
            with self.subTest(value=value):
                out = clean_fragment(f'<p>prose</p><h4 class="{value}">x</h4>')
                self.assertEqual(out, "<p>prose</p>")

    def test_a_note_classed_footnote_marker_is_still_a_marker(self):
        """Gutenberg spells a marker `<sup class="note">1</sup>` too.

        `sup` is allowlisted, so keeping one leaves an orphan digit mid-sentence
        with its note body dropped — the identical failure `_is_pg_navigation`
        prevents on the sibling selector, so both predicates share the test.
        """
        for marker in ('<sup class="note">1</sup>',
                       '<a class="note" href="#f1">[1]</a>',
                       '<sup class="note">°</sup>'):
            with self.subTest(marker=marker):
                out = clean_fragment(f"<p>a work of faith{marker} and labour</p>")
                self.assertEqual(out, "<p>a work of faith and labour</p>")

    def test_class_given_as_a_string_is_read_as_tokens(self):
        """A programmatically-set `class` is a str, not a token list.

        `_scrub_attrs` has always guarded that; a predicate that forgets drops
        the content it was written to keep.
        """
        from bs4 import BeautifulSoup

        from library.sanitize import clean_html

        doc = BeautifulSoup("<div><h3>NOTE A.</h3></div>", "lxml").div
        doc.h3["class"] = "note"  # a string, the way bs4 stores an assignment
        self.assertEqual(clean_html(doc), "<h3>NOTE A.</h3>")

    def test_an_ancestors_drop_beats_a_descendants_keep(self):
        """The whole of the keep contract, stated as a test.

        One selector matches a wrapper and what it wraps; the wrapper goes
        first, taking the keep-candidate with it. Right for apparatus — a
        Gutenberg `p.note` inside CCEL's `div.footnotes` is apparatus — but it
        is the shape a future ambiguous wrapper would fail in, so it is pinned
        rather than left to be rediscovered.
        """
        out = clean_fragment(
            '<div class="footnotes"><p class="note">inside apparatus</p></div>'
            "<p>prose</p>"
        )
        self.assertEqual(out, "<p>prose</p>")


class KeepPredicateRegistryTests(TestCase):
    """Every qualified selector must still BE a drop selector.

    `drop_furniture` looks its predicate up by selector string, so a predicate
    registered under a selector that is not in `DROP_SELECTORS` is dead code
    that silently qualifies nothing — and the element it was meant to rescue
    goes on being deleted. A typo in either list is invisible without this.
    """

    def test_every_keep_predicate_qualifies_a_live_drop_selector(self):
        from library.sanitize import DROP_SELECTORS, KEEP_PREDICATES

        self.assertEqual(
            sorted(set(KEEP_PREDICATES) - set(DROP_SELECTORS)),
            [],
            "a keep-predicate is registered under a selector that is not in "
            "DROP_SELECTORS, so it never runs",
        )

    def test_no_module_outside_the_sanitizer_iterates_the_bare_list(self):
        """The importers must borrow the PASS, not the list.

        `import_ccel`, `build_ignatius` and `build_serious_call` each run this
        pre-pass, and two selectors are only correct when their keep-predicate
        runs with them — a bare `for sel in DROP_SELECTORS` loop over-drops
        exactly where a transcriber's markup is ambiguous, which is how a
        Gutenberg heading gets deleted by a CCEL rule. The previous version of
        this test asserted the difference on a fragment and so could not have
        caught an importer rotting back; this reads the modules.
        """
        import library

        root = Path(library.__file__).resolve().parent
        offenders = [
            str(path.relative_to(root))
            for path in sorted(root.rglob("*.py"))
            if path.name not in {"sanitize.py", "ingest.py", "tests_sanitize.py"}
            and re.search(r"for\s+\w+\s+in\s+DROP_SELECTORS", path.read_text())
        ]
        self.assertEqual(
            offenders,
            [],
            "these iterate DROP_SELECTORS directly and so skip KEEP_PREDICATES; "
            "call sanitize.drop_furniture() instead",
        )


class StoredContentIsSafeTests(TestCase):
    """Scan what is actually shipped, not what the write paths promise.

    This is the enforcement half. The sanitizer only protects the paths that
    call it; this notices when something reached the repo without doing so —
    including a translation PR authored with no human in the loop.
    """

    def test_no_shipped_content_body_is_dangerous(self):
        # Every per-work fixture the reader renders with {@html}, not an
        # enumerated books+sermons list: a NEW content type carrying a
        # ``body_html`` (articles were the first) must be covered the moment its
        # fixtures land, without anyone remembering to widen this glob. Files
        # with no ``body_html`` rows (authors.json, plans.json) are scanned and
        # harmlessly skipped by the guard below — the same "close the class, not
        # the instance" reasoning tests_rls and the content-source coverage use.
        offenders: list[str] = []
        scanned = 0
        files = sorted(CONTENT_ROOT.rglob("*.json"))
        self.assertTrue(files, "no content fixtures found — has the layout moved?")
        for path in files:
            for row in json.loads(path.read_text()):
                body = (row.get("fields") or {}).get("body_html")
                if not body:
                    continue
                scanned += 1
                for label in _dangerous_findings(body):
                    offenders.append(f"{path.name}: {label}")
        self.assertEqual(
            offenders,
            [],
            "Dangerous HTML is shipped in content the reader renders with "
            "{@html}:\n  " + "\n  ".join(sorted(set(offenders))),
        )
        self.assertGreater(scanned, 0, "scanned no bodies — the glob is wrong")

    def test_every_shipped_illustration_exists_and_is_described(self):
        """An `<img>` in a shipped body must name a committed file, with alt text.

        The sanitizer only checks the path's SHAPE; this checks the file is
        really there, so a typo is a failed build rather than a broken picture
        on a prerendered page.
        """
        problems: list[str] = []
        for path in sorted(CONTENT_ROOT.rglob("*.json")):
            for row in json.loads(path.read_text()):
                body = (row.get("fields") or {}).get("body_html") or ""
                for tag in _IMG.findall(body):
                    attrs = {m[0].lower(): m[1] or m[2] for m in _ATTR.findall(tag)}
                    src = attrs.get("src", "")
                    if not src.startswith("/illustrations/"):
                        problems.append(f"{path.name}: not an illustration path: {src!r}")
                    elif not (ILLUSTRATIONS_ROOT.parent / src.lstrip("/")).is_file():
                        problems.append(f"{path.name}: missing file {src}")
                    if not attrs.get("alt", "").strip():
                        problems.append(f"{path.name}: no alt text on {src}")
        self.assertEqual(problems, [], "\n  ".join(["Broken illustrations:", *problems]))

    def test_no_shipped_author_biography_is_dangerous(self):
        offenders: list[str] = []
        files = sorted(BIO_ROOT.rglob("*.html"))
        self.assertTrue(files, "no biography files found — has the layout moved?")
        for path in files:
            for label in _dangerous_findings(path.read_text()):
                offenders.append(f"{path.name}: {label}")
        self.assertEqual(
            offenders,
            [],
            "Dangerous HTML is shipped in biographies:\n  "
            + "\n  ".join(sorted(set(offenders))),
        )

    def test_shipped_biographies_use_only_allowlisted_markup(self):
        """A tag outside the bio profile means a write path skipped sanitizing."""
        from library.sanitize import BIO_ALLOWED_TAGS

        seen: set[str] = set()
        for path in sorted(BIO_ROOT.rglob("*.html")):
            seen.update(
                m.group(1).lower()
                for m in re.finditer(r"<\s*([a-zA-Z][\w-]*)", path.read_text())
            )
        self.assertEqual(
            sorted(seen - BIO_ALLOWED_TAGS),
            [],
            "Biographies contain tags the sanitizer would strip — the file and "
            "the allowlist disagree about what a biography may contain.",
        )
