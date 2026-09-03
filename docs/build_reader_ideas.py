#!/usr/bin/env python3
"""Build docs/reader_ideas.html — a print-ready brief of 20 reader-experience ideas.

Matches the house style of docs/ideas.html by reusing its exact <style> block
(embedded Fraunces/Hanken fonts and all), so the two documents look identical.
Run:  python3 docs/build_reader_ideas.py
"""
from __future__ import annotations
import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "ideas.html"          # borrow its <style> + embedded fonts
OUT = HERE / "reader_ideas.html"


def head_from_ideas() -> str:
    """Return everything from <!doctype ...> up to and including </style>."""
    doc = SRC.read_text(encoding="utf-8")
    end = doc.index("</style>") + len("</style>")
    return doc[:end]


# ── Content ────────────────────────────────────────────────────────────────
# Each idea: (title, what, why, watch, prompt)
CATEGORIES = [
    ("A", "Mobile — the phone reader", [
        (
            "Touch swipe to turn pages",
            "A horizontal drag on the prose to turn pages in paged mode — the gesture every phone reader reaches for.",
            "Paging today is tap-zone + edge-arrow + keyboard only; on a phone the missing swipe is the single most “unfinished” feeling.",
            "Respect RTL; rubber-band at book/chapter ends; don’t fight the vertical scroll of scroll-mode.",
            "In the Ochorus chapter reader (frontend/src/routes/books/[slug]/[order]/+page.svelte, paged-mode code ~186-358) add a horizontal touch-drag handler that turns the page: follow the finger with a translateX on the prose container, snap to prev/next page on release past a threshold or on a fast flick, and rubber-band at the first/last page of the book and chapter. Make it RTL-aware, and leave scroll mode untouched.",
        ),
        (
            "Reveal chrome from focus mode without a keyboard",
            "A swipe-down from the top (or a centre tap) briefly summons the reader chrome and “Aa” controls, then re-hides.",
            "Focus mode hides everything and needs Esc to exit — which phones don’t have, so it becomes a one-way door.",
            "Keep the existing Esc path for laptops; the summoned chrome should auto-dismiss so it doesn’t clutter reading.",
            "Ochorus focus mode (readerUi.svelte.ts + the reader in +page.svelte) hides all chrome and relies on Esc, which phones lack. Add a touch affordance: a short swipe-down from the top edge, or a tap in the dead-centre of the text, summons the reader chrome and Aa button for a few seconds and then fades them out again. Keep Esc working for keyboards.",
        ),
        (
            "Fix the breadcrumb blackout on 360px phones",
            "Give the smallest phones a compact single-line “which book / chapter” label instead of nothing.",
            "The context block is hidden sm:block, so sub-640px phones lose all sense of where they are in the book.",
            "Must not steal vertical space from the text; a single truncating line is enough.",
            "On the narrowest phones the Ochorus reader header hides the breadcrumb context entirely (hidden sm:block; see observeTitle in the chapter +page.svelte ~689-696). Add a compact single-line location label for sub-640px viewports — e.g. “Book Title · Chapter”, truncated with ellipsis — so phone readers always know where they are without adding vertical bulk.",
        ),
        (
            "Thumb-reachable reading controls",
            "Audit prev/next, bookmark and Aa against a 44px minimum and bias the primary reading actions toward the bottom of the screen.",
            "One-handed phone reading lives in the lower third; controls parked at the top are a stretch away.",
            "Don’t collide with the safe-area / home indicator; keep the tap targets from overlapping page-turn zones.",
            "Audit the Ochorus reader’s interactive controls (chapter prev/next, bookmark toggle, Aa/settings) in the chapter +page.svelte for one-handed phone use: ensure every tap target is ≥ 44px, and move the primary reading actions within thumb reach of the bottom of the screen (respecting env(safe-area-inset-bottom)). Take before/after screenshots at 390px width.",
        ),
        (
            "Opt-in tap-to-page-down in scroll mode",
            "A clearly-labelled setting: tap the bottom third of the screen to advance one screenful in scroll mode.",
            "Edge-tap chapter-turn was rightly removed as a footgun, but many phone readers still want *some* tap rhythm.",
            "Ship it OFF by default and behind an explicit toggle — the removed version was a footgun precisely because it was implicit.",
            "Add an opt-in reading preference to Ochorus (readerPrefs.svelte.ts + ReaderControls.svelte) called something like “Tap to page down”, default off. When on, tapping the bottom third of the screen in scroll mode scrolls one screenful (with a small overlap). Keep it clearly a setting — the earlier implicit edge-tap chapter-turn was removed as a phone footgun (see the comment near onArticleClick).",
        ),
        (
            "Chapter-complete confirmation",
            "When a chapter reaches 100%, a subtle haptic plus the next-chapter CTA animating in makes finishing feel rewarding.",
            "Completing a chapter is a genuine devotional milestone; on mobile it currently passes silently.",
            "Fire the haptic once per chapter, gated on user activation; keep it optional for people who dislike vibration.",
            "In the Ochorus reader, when a chapter’s reading progress reaches 100% (progress.ts), give a small completion moment on mobile: a brief navigator.vibrate() haptic (guarded by user-activation and a preference) and a gentle animate-in of the existing next-chapter CTA. Fire it at most once per chapter.",
        ),
    ]),
    ("B", "Tablet — the underserved middle", [
        (
            "Two-column spread on landscape tablets",
            "Let a landscape tablet show a real two-page book spread, not one narrow column in a sea of margin.",
            "The two-column spread is gated at 1024px, so most tablets — portrait, and even many landscape — never see it.",
            "Portrait tablets should stay single-column; base the switch on width *and* orientation, not width alone.",
            "Ochorus gates its paged two-column spread at TWO_COL_MIN = 1024px (chapter +page.svelte). Make it orientation-aware so a landscape tablet gets the two-page spread while portrait tablets stay single-column — e.g. enable two columns when the available width clears a lower threshold in landscape. Verify on iPad-sized viewports in both orientations.",
        ),
        (
            "Sensible default measure on tablets",
            "Pick a device-class-aware default column width so a tablet reads like a page, not a stretched phone.",
            "At “normal” width a tablet can render a phone-width column floating in whitespace — it feels unfinished.",
            "Only change the *default*; users who set a measure themselves keep their choice.",
            "Ochorus derives its default reading layout by viewport (readerPrefs.svelte.ts ~134-137) but the default measure (34/42/52rem) can leave a tablet with a phone-width column in a sea of margin. Choose a tablet-appropriate default measure so the text fills the page comfortably, without overriding a measure the user has explicitly chosen.",
        ),
        (
            "Split view: pin the TOC or notes beside the text",
            "On ≥768px, let the table of contents (or a notes list) pin open alongside the text instead of sliding over it.",
            "Tablets have the room for study reading; a persistent panel turns the reader into a desk, not just a page.",
            "Collapse gracefully back to the existing slide-over drawer on phones; don’t crush the measure below readable.",
            "Ochorus’s TocDrawer.svelte (and a future notes panel) currently slides over the reader. On viewports ≥ 768px, add a “pin” mode that docks the drawer beside the article as a persistent column, reflowing the prose measure, and collapses back to the slide-over on phones. Good for study reading on a tablet.",
        ),
        (
            "Stylus (Apple Pencil) highlighting",
            "Detect a pen pointer and let a pen-drag create a highlight directly, skipping the selection bar.",
            "On an iPad, dragging a stylus across text is the natural highlight gesture; routing it through the text-select UI is friction.",
            "Only treat pointerType === 'pen' this way; finger selection and the selection bar stay exactly as they are.",
            "In Ochorus’s selection/highlight machinery (readerText.svelte.ts + marks.svelte.ts), detect pointerType === 'pen' and let a pen-drag across the prose create a highlight directly in the current colour, bypassing the tap-select + SelectionBar flow. Leave finger and mouse selection untouched. Test with an Apple Pencil on iPad.",
        ),
    ]),
    ("C", "Laptop & desktop", [
        (
            "A keyboard-shortcut sheet (press ?)",
            "Surface the reader’s shortcuts — arrows to page, Esc to exit focus, and any j/k, b, l, / bindings — in a “?” overlay.",
            "Power readers on laptops will use shortcuts they can discover; hidden keys help no one.",
            "Keep the sheet itself dismissible with Esc or ?; don’t swallow keys while a text field is focused.",
            "Add a keyboard-shortcut help overlay to the Ochorus reader, opened with “?” and closed with Esc. List the reader’s existing bindings (←/→ page turn, Esc focus-mode, listen/search/bookmark if bound) pulled from the chapter +page.svelte key handler. While it’s open, suppress page-turn keys the same way the Aa panel does (readerUi.panelOpen).",
        ),
        (
            "Column-aware click-to-page in two-column mode",
            "Clicking the right column advances; make paged-mode click zones understand the current spread instead of a fixed outer 15%.",
            "On a laptop the natural gesture is clicking the page you’ve finished; a fixed edge zone ignores the two-column layout.",
            "Don’t hijack clicks on links, highlights, or the scripture/define popovers.",
            "Ochorus’s paged-mode click zones are a fixed outer 15% left/right (onArticleClick in the chapter +page.svelte ~572-582). Make them column-aware in two-column spreads: a click in the right column pages forward, the left column pages back, while clicks on links, existing highlights, and scripture/define triggers pass through untouched.",
        ),
        (
            "Hover-preview scripture references",
            "On pointer devices, a hover-intent preview of a scripture ref — the tap/click behaviour stays for touch.",
            "Cross-referencing while reading on a laptop is smoother by hover than by click-and-dismiss.",
            "Hover-intent only on fine pointers; never on coarse/touch, where hover is unreliable.",
            "Ochorus wraps Bible references with a tappable ScripturePopover (readerText.svelte.ts ~115-126). On fine-pointer devices only (pointer: fine), add a hover-intent preview so hovering a reference shows the popover after a short delay, while preserving the existing click/tap behaviour for touch. Don’t enable hover on coarse pointers.",
        ),
        (
            "An extra-wide measure for big displays",
            "Add a wider measure step (or true two-column on large desktop) for readers who want the page to fill a big screen.",
            "52rem “wide” can still feel like a narrow ribbon on a 27″ display.",
            "Keep the comfortable defaults; this is an extra step for people who ask for it, not a new default.",
            "Extend Ochorus’s measure options (readerPrefs.svelte.ts MEASURE ~37-47, exposed in ReaderControls.svelte) with an extra-wide step for large displays — or wire up a true two-column scroll layout at very large widths — without changing the existing narrow/normal/wide defaults.",
        ),
    ]),
    ("D", "Cross-device & reading depth", [
        (
            "Sync bookmarks to the account",
            "Fold bookmarks into the account sync so they follow the reader across devices, like highlights and progress already do.",
            "Highlights and progress sync; bookmarks are device-local — the one jarring inconsistency in an otherwise synced reader.",
            "Reuse the marks/progress tombstone-union merge; don’t lose local bookmarks on first sync or on sign-out.",
            "Bookmarks in Ochorus are explicitly device-local (bookmarks.svelte.ts ~11-13 notes account-sync “can follow the marks/progress pattern later”). Add them to readingSync.ts using the same tombstone/union merge as marks and progress, so bookmarks sync across devices for signed-in users. Preserve existing local bookmarks on first sync and keep them out of the sign-out wipe.",
        ),
        (
            "Stemming / fuzzy in-book search",
            "Normalise the in-book index so “praying” finds “prayer” before escalating to server search.",
            "Search is literal-substring, so common devotional word-forms miss each other — a real gap in this prose.",
            "Keep it fast and client-side; light stemming/normalisation, not a heavyweight index.",
            "Ochorus’s in-book search (SearchDrawer.svelte) is literal substring, so “praying” won’t match “prayer”. Add light client-side normalisation/stemming to the paragraph index (fold case, strip common suffixes, or a small stemmer) so word-forms match, while keeping the existing “escalate to server search” link as the fallback.",
        ),
        (
            "A notes & highlights panel inside the reader",
            "A per-book “my marks” panel: every highlight and note, tap to jump, with export.",
            "Readers annotate these classics heavily; a review surface turns the reader from a page into a study tool.",
            "Reuse the drawer pattern (see #9 pin mode on tablets); keep it in sync with live highlight edits.",
            "Add a notes/highlights review panel to the Ochorus reader: a per-book list of all highlights and notes (from marks.svelte.ts) with their text and colour, tap-to-jump to the paragraph, and an export. Present it as a drawer like TocDrawer/SearchDrawer, and on tablets let it use the pinned side-panel mode.",
        ),
        (
            "Prefer real narration audio where it exists",
            "A book-level audio field and a toggle to play human narration when available, falling back to TTS.",
            "TTS follow-along is excellent, but real narration is a step-change for commute and eyes-closed listening.",
            "Fall back cleanly to TTS per-book; keep the media-session + sleep-timer controls you already have.",
            "Ochorus’s Listen feature is Web-Speech TTS only (listen.svelte.ts, ListenBar.svelte). Add an optional per-book narration-audio source and, when present, let the Listen UI prefer human narration over TTS — reusing the existing follow-along highlight, OS media-session and sleep-timer controls — and fall back to TTS when no audio exists.",
        ),
        (
            "“Continue where you left off” across devices",
            "When a book opens and the account’s synced position is ahead of this device, offer a one-tap jump.",
            "The synced position already exists; surfacing the divergence closes the loop on cross-device reading.",
            "Only prompt on a meaningful gap; don’t nag when the two positions are effectively the same.",
            "Ochorus already syncs reading position (readingSync.ts + progress.ts). When a book opens and the account’s last synced position is meaningfully ahead of this device’s local position, show a dismissible “Continue where you left off on your other device” banner that jumps to the synced paragraph. Suppress it when the positions are effectively equal.",
        ),
        (
            "Auto-scroll / teleprompter reading",
            "A gentle, speed-adjustable auto-scroll independent of TTS — hands-free reading on a propped-up phone or tablet.",
            "Great for a device on a stand; reuses the paragraph-position machinery already in the reader.",
            "Pause on touch and on TTS; expose a simple speed control and remember it.",
            "Add an auto-scroll (“teleprompter”) mode to the Ochorus scroll-mode reader: a gentle, speed-adjustable continuous scroll independent of TTS, with a start/stop and speed control in the reader chrome. Pause on user touch and while TTS is playing, and persist the chosen speed in readerPrefs.",
        ),
    ]),
]

INTRO_CALLOUT_K = "The one finding that shapes the list"
INTRO_CALLOUT = (
    "The Ochorus reader is already <strong>unusually capable</strong> — three themes, measure / leading / "
    "typeface controls, TTS with follow-along, highlights and notes, a Kindle-style paged mode, offline reading "
    "and cross-device sync. So this list deliberately skips the basics you already have and targets real gaps. "
    "Three of them read as <strong>broken or half-done</strong> rather than merely missing — no swipe-to-turn on "
    "phones (#1), bookmarks that don’t follow you across devices (#15), and a search that can’t match "
    "“praying” to “prayer” (#16). Start there."
)

WAVES = [
    ("Wave 1 — Fix what feels broken",
     "#1 swipe-to-turn, #15 bookmark sync, #16 search stemming.",
     "These three read as broken or half-done today, not merely absent — the fastest way to make the reader feel finished."),
    ("Wave 2 — Reader depth (study & hands-free)",
     "#17 notes & highlights panel, #19 continue-across-devices, #20 auto-scroll, #18 real narration audio.",
     "Turn an excellent page into a study tool and a hands-free companion — the features that keep serious readers."),
    ("Wave 3 — Tablet as a first-class page",
     "#7 landscape two-column, #8 tablet default measure, #9 pinned split view, #10 stylus highlighting.",
     "The underserved middle. Note: #7/#12 touch the paged-mode position logic duplicated between Reader.svelte and the chapter +page.svelte — consolidate that first (its comments warn it has drifted before)."),
    ("Wave 4 — Laptop power + mobile polish",
     "#11 shortcut sheet, #12 column-aware click, #13 hover scripture, #14 extra-wide measure; then mobile polish #2 reveal-chrome, #3 breadcrumb, #4 thumb reach, #5 tap-to-page, #6 chapter-complete.",
     "Discoverable power for laptops, and the small phone refinements that add up to a reader that feels considered on every screen."),
]

THREE = ("If you could only do three next: <b>#19 continue-across-devices</b>, "
         "<b>#7 landscape two-column</b>, and <b>#20 auto-scroll</b> — resume everywhere, a real "
         "tablet page, and hands-free reading, now that the half-finished gaps are closed.")

# Idea numbers already built and shipped to production (marked ✓ on the cards).
# #1–6 the phone batch (plus a left/right single-page tap mode), #15–17 the
# cross-device study batch, and #8 / #14 with the type & layout controls
# (tablet default width, extra-wide measure).
SHIPPED = {1, 2, 3, 4, 5, 6, 8, 14, 15, 16, 17}

# Supplemental styles for the shipped treatment, appended after the borrowed
# <style> from ideas.html (which this doc reuses verbatim for its look).
SHIP_STYLE = (
    "<style>\n"
    ".idea.shipped{ border-color:#bfe3c8; background:#f3fbf5; }\n"
    ".idea.shipped .num{ color:#2e9e57; }\n"
    ".ship-badge{ display:inline-block; margin-left:8px; font-family:var(--sans); font-weight:700;\n"
    "  font-size:7pt; letter-spacing:.08em; text-transform:uppercase; color:#fff; background:#2e9e57;\n"
    "  padding:2px 7px 3px; border-radius:5px; vertical-align:middle; }\n"
    ".shipnote{ background:#eef8f1; border:1px solid #bfe3c8; border-left:4px solid #2e9e57;\n"
    "  border-radius:10px; padding:12px 16px; margin:14px 0 4px; }\n"
    ".shipnote .k{ font-family:var(--sans); font-weight:700; color:#1f7a41; text-transform:uppercase;\n"
    "  letter-spacing:.06em; font-size:8pt; display:block; margin-bottom:4px; }\n"
    ".shipnote{ color:#2a4a35; font-size:9.7pt; line-height:1.5; }\n"
    ".shipnote b{ color:#1f7a41; }\n"
    "</style>"
)

SHIP_NOTE = (
    '  <div class="shipnote">\n'
    '    <span class="k">Shipped since this brief</span>\n'
    '    The <b>phone batch</b> (#1 swipe-to-turn, #2 focus-mode peek, #3 phone breadcrumb, '
    '#4 larger touch targets, #5 tap-to-page-down, #6 chapter-complete) plus a left/right '
    '<b>single-page tap mode</b>; and the <b>cross-device batch</b> (#15 bookmark sync, '
    '#16 search stemming, #17 notes &amp; highlights panel); and, with the <b>type &amp; layout '
    'controls</b>, #8 tablet default width and #14 extra-wide measure. Each is verified live '
    'and marked <b>✓ Shipped</b> on its card below.\n'
    '  </div>\n'
)


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def render() -> str:
    head = head_from_ideas()
    parts = [head, SHIP_STYLE, "</head><body>\n"]

    # Cover
    parts.append(
        '\n<div class="cover">\n'
        '  <div class="mark">OCHORUS</div>\n'
        '  <div class="rule"></div>\n'
        '  <h1>Reader Experience Ideas</h1>\n'
        '  <div class="sub">20 ways to improve the Ochorus reader — phone, tablet &amp; laptop —<br>'
        'each with a ready-to-use prompt</div>\n'
        '  <div class="meta">\n'
        '    A review of the reader at <a>ochorus-web.onrender.com</a><br>\n'
        '    <span class="tag">Equipping people with classic Christian books · A ministry since 2021 · Kampala, Uganda</span>\n'
        '  </div>\n'
        '</div>\n'
    )

    # Intro
    parts.append(
        '\n<section class="intro">\n'
        '  <h2>How to read this</h2>\n'
        '  <p>Twenty reader-focused ideas, grouped by the screen they help most — <b>phone</b>, <b>tablet</b>, '
        '<b>laptop</b>, and the things that span all three. Each has <b>what</b> it is, <b>why</b> it helps, what to '
        '<b>watch</b> for, and a copy-paste <b>prompt</b> you can hand to an AI coding assistant to build it against the '
        'Ochorus codebase. A recommended order follows at the end.</p>\n'
        f'  <div class="callout">\n    <span class="k">{INTRO_CALLOUT_K}</span>\n    {INTRO_CALLOUT}\n  </div>\n'
        f'{SHIP_NOTE}'
        '</section>\n'
    )

    # Categories
    n = 0
    for badge, title, ideas in CATEGORIES:
        parts.append(
            '\n<section class="cat">\n'
            f'      <div class="cat-head"><span class="badge">{badge}</span><h2>{esc(title)}</h2></div>\n'
        )
        for (h3, what, why, watch, prompt) in ideas:
            n += 1
            shipped = n in SHIPPED
            idea_cls = 'idea shipped' if shipped else 'idea'
            badge = ' <span class="ship-badge">✓ Shipped</span>' if shipped else ''
            parts.append(
                f'      <div class="{idea_cls}">\n'
                f'      <div class="num">{n}</div>\n'
                '      <div class="idea-body">\n'
                f'        <h3>{esc(h3)}{badge}</h3>\n'
                f'        <p><span class="lbl">What</span>{esc(what)}</p>\n'
                f'        <p><span class="lbl">Why</span>{esc(why)}</p>\n'
                f'        <p><span class="lbl watch">Watch</span>{esc(watch)}</p>\n'
                f'        <div class="prompt"><span class="plabel">Prompt</span><code>{esc(prompt)}</code></div>\n'
                '      </div>\n    </div>\n'
            )
        parts.append('    </section>\n')

    # Recommended order
    parts.append(
        '\n\n<section class="order">\n'
        '  <h2>Recommended order</h2>\n'
        '  <p class="lede">Sequenced by impact &times; dependency, in four waves.</p>\n'
    )
    for (wt, items, why) in WAVES:
        parts.append(
            '  <div class="wave">\n'
            f'      <h3>{esc(wt)}</h3>\n'
            f'      <p class="wave-items">{esc(items)}</p>\n'
            f'      <p class="wave-why"><span class="lbl">Why</span>{esc(why)}</p>\n'
            '    </div>\n'
        )
    parts.append(
        f'\n  <p class="three">{THREE}</p>\n'
        '  <div class="foot">OCHORUS · READER EXPERIENCE IDEAS · PREPARED WITH CLAUDE</div>\n'
        '</section>\n\n</body></html>\n'
    )

    return "".join(parts)


def main() -> None:
    OUT.write_text(render(), encoding="utf-8")
    ideas = sum(len(c[2]) for c in CATEGORIES)
    print(f"Wrote {OUT}  ({ideas} ideas, {OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
