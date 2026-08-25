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


class StoredContentIsSafeTests(TestCase):
    """Scan what is actually shipped, not what the write paths promise.

    This is the enforcement half. The sanitizer only protects the paths that
    call it; this notices when something reached the repo without doing so —
    including a translation PR authored with no human in the loop.
    """

    def test_no_shipped_chapter_or_sermon_body_is_dangerous(self):
        offenders: list[str] = []
        scanned = 0
        files = sorted(CONTENT_ROOT.glob("books/*.json")) + sorted(
            CONTENT_ROOT.glob("sermons/*.json")
        )
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
