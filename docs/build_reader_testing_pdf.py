#!/usr/bin/env python3
"""Build docs/reader_testing.html — a four-page guide to testing the Ochorus
reader across phones, tablets and laptops — in the house style of
docs/ideas.html (its exact <style>, embedded fonts and all), then render it to
docs/reader_testing.pdf with headless Chrome.

Run:  python3 docs/build_reader_testing_pdf.py
"""
from __future__ import annotations
import html
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "ideas.html"  # borrow its <style> + embedded fonts
OUT_HTML = HERE / "reader_testing.html"
OUT_PDF = HERE / "reader_testing.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def head_from_ideas() -> str:
    doc = SRC.read_text(encoding="utf-8")
    end = doc.index("</style>") + len("</style>")
    return doc[:end]


def esc(s: str) -> str:
    return html.escape(s, quote=False)


# Supplemental styles: a title block instead of a full cover page, tables,
# checklists, and hard page breaks so the document is exactly four pages.
EXTRA_STYLE = """<style>
.cover{ height:auto; padding:6mm 0 4mm; page-break-after:avoid; text-align:start; align-items:flex-start; }
.cover h1{ font-size:26pt; margin:6px 0 4px; }
.cover .sub{ font-size:10.5pt; }
.cover .rule{ margin:8px 0; }
.cover .meta{ margin-top:6px; }
.page{ page-break-before:always; }
.page h2, .intro h2{ font-family:var(--serif); font-size:16pt; margin:0 0 6px; }
.lede{ font-size:10.2pt; color:var(--muted); margin:0 0 10px; }
table{ width:100%; border-collapse:collapse; font-size:9.3pt; margin:6px 0 12px; page-break-inside:avoid; }
th,td{ text-align:left; vertical-align:top; padding:6px 8px; border-bottom:1px solid var(--border); }
th{ font-family:var(--sans); font-size:8pt; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); background:var(--surface); }
td.k{ font-family:var(--sans); font-weight:700; white-space:nowrap; }
.tier{ display:flex; gap:10px; margin-bottom:9px; page-break-inside:avoid; }
.tier .num{ flex:0 0 26px; height:26px; border-radius:999px; background:var(--accent); color:#fff; font-family:var(--sans); font-weight:700; font-size:10pt; display:flex; align-items:center; justify-content:center; }
.tier h3{ margin:2px 0 3px; font-size:11.5pt; }
.tier p{ margin:0 0 3px; font-size:9.8pt; }
.check{ list-style:none; padding:0; margin:0 0 8px; }
.check li{ position:relative; padding-left:20px; margin:0 0 4px; font-size:9.6pt; }
.check li:before{ content:""; position:absolute; left:0; top:3px; width:11px; height:11px; border:1.5px solid var(--accent); border-radius:3px; }
.two{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.prompt code{ font-size:8.6pt; }
.small{ font-size:9pt; color:var(--muted); }
.foot{ margin-top:4px; }
table.tight td, table.tight th{ padding:3px 8px; }
table.tight{ margin-bottom:4px; }
</style>"""

TIERS = [
    ("Browser emulation for layout and pointer logic",
     "Minutes per pass, and it catches most things. Chrome DevTools’ device toolbar at 375×812 (phone), "
     "768×1024 and 1024×768 (tablet, both ways) and 1440 (laptop). Emulation flips <code>pointer: coarse</code>, "
     "which is what gates the 44px scrubber, the swipe and tap page turns and the tablet-default width — so it "
     "exercises the real code paths, not a lookalike.",
     "Page-mode tap zones · the Aa panel and its live preview · margins and extra-wide · the progress hairline · "
     "the up-next card · the return pill and the cross-device offer · Undo toasts."),
    ("Real devices on the same Wi-Fi, against the dev server",
     "The only way to feel scroll physics, safe-area insets and Safari’s quirks. Run the frontend with "
     "<code>--host</code>, open <code>http://&lt;mac-ip&gt;:5180</code> on the phone. The API must list the phone’s "
     "origin in <code>CORS_ALLOWED_ORIGINS</code> and <code>PUBLIC_API_BASE_URL</code> must point at the Mac’s IP, "
     "not localhost. Test in Safari <i>and</i> in the installed PWA (home-screen icon).",
     "The service-worker cache is where “feature absent” false alarms live: unregister it and clear site data before "
     "trusting a negative."),
    ("Production spot-checks after every deploy",
     "Per the deploy playbook’s traps: book URLs with the trailing slash (the no-slash form is a 5.7 KB SPA shell that "
     "200s forever), and confirm the web build actually changed — compare the JS bundle hashes — before hunting for "
     "a feature. The API build lags frontend-only PRs; an endpoint exists when it answers 401, not 404.",
     "Two signed-in devices on production are the only honest test of anything that syncs."),
]

MATRIX = [
    ("iPhone · Safari + installed PWA", "Safe-area insets, 100vh, rubber-band scroll, the toast stack and the return "
     "pill sitting above the footer, text selection vs the tap-to-turn zones."),
    ("Android · Chrome (a mid-range phone)", "Coarse pointer, low-end performance of the idle prefetch and page-mode "
     "layout, the 44px scrubber, back-gesture vs swipe-to-turn."),
    ("iPad · portrait and landscape", "The 768–1023 tablet-default width, two-thumb tap zones, rotation re-layout, "
     "page mode with a hardware keyboard attached."),
    ("Laptop · 1280 and a scaled 4K display", "Extra-wide measure, keyboard navigation and focus rings, the Aa panel’s "
     "70vh cap, hover states on the pills."),
]

SETUP = [
    ("Frontend on the LAN",
     "cd frontend && npm run dev -- --host --port 5180 --strictPort\n"
     "# then on the phone: http://<mac-ip>:5180/books/<slug>/1/"),
    ("API reachable from the phone",
     "# backend/.env\nCORS_ALLOWED_ORIGINS=http://localhost:5180,http://<mac-ip>:5180\n"
     "# frontend/.env\nPUBLIC_API_BASE_URL=http://<mac-ip>:8000"),
    ("Clean slate before trusting a negative",
     "# DevTools → Application → Service Workers → Unregister; Storage → Clear site data\n"
     "# or in the console:\n"
     "navigator.serviceWorker.getRegistrations().then(rs => rs.forEach(r => r.unregister()));\n"
     "caches.keys().then(ks => ks.forEach(k => caches.delete(k)));"),
    ("Did the web build change?",
     "curl -s https://ochorus.com/books/<slug>/1/ | grep -oE '_app/immutable/[^\"\\x27]+\\.js' | sort | md5"),
]

WALK = [
    ("Open cold", ["Open a mid-book chapter from the home screen / a deep link: the position restores to the "
                   "paragraph, not the top; no progress hairline in page mode, hairline present in scroll mode.",
                   "Signed in, with the other device further along: the “further along on another device” pill "
                   "appears within a second; <b>Continue · ch. N</b> lands on the paragraph; no “back to where you "
                   "were” pill follows it; dismiss holds for the book."]),
    ("Turn pages", ["Tap right/left thirds and swipe both ways in page mode; RTL book flips both; rubber-band at "
                    "the chapter ends; a fast flick turns one page, not two.",
                    "Scroll mode: the footer scrubber has a ≥44px thumb target on touch; the last line of prose "
                    "clears the footer; “Page N / M” updates as you go."]),
    ("Type & layout", ["Open Aa: the preview line follows size, typeface, width and margins live; Generous margins "
                       "move the chrome bar with the text; extra-wide is offered on laptops; Margins are hidden in "
                       "page mode.",
                       "First run on an iPad in portrait defaults to the wide measure; a stored choice beats it."]),
    ("Marks & bookmarks", ["Highlight, recolour, then un-highlight: “Removed · Undo” appears; Undo restores colour "
                           "and note; wait 6 s and it goes away.",
                           "Remove a bookmark in the contents drawer: the Undo is <i>inside</i> the drawer "
                           "(reachable by Tab); close the drawer and it moves to the corner toast."]),
    ("Chapter end", ["The Next card shows the next chapter’s reading time and its opening line without the button "
                     "growing under your thumb; a Contents link sits below it mid-book.",
                     "Reading times everywhere say “· at your pace” in the footer after ~7 minutes of reading and "
                     "shrink or grow to match; listening and scrubbing do not change them."]),
    ("Modes & themes", ["Focus mode on a phone: the hairline stays, a screen reader hears “Page 4 / 9” as pages change; "
                        "Escape or the summon gesture brings the chrome back.",
                        "Dark theme and the sepia palette: pills, toasts and the drawer stay legible; the accent "
                        "passes contrast on both grounds."]),
]

TRAPS = [
    ("Emulation cannot tell you", "Whether iOS text selection fights the tap-to-turn zones, and whether the toast "
     "stack overlaps the audio player on a small phone. Both need real hardware."),
    ("Hidden preview panes have no viewport", "A hidden in-app browser pane reports <code>innerHeight: 0</code> and "
     "<code>visibilityState: hidden</code>: nothing scrolls, and visibility-gated features correctly do nothing. "
     "Emulate a device size before calling a feature broken."),
    ("Module instances after an edit", "Overriding a store from the console works only until the file is edited; "
     "after HMR the app holds a timestamped module URL and your import is an inert twin."),
    ("The localized-page trap", "A stored <code>en</code> preference de-localizes <code>/lg</code> URLs in a "
     "persistent session; wipe storage or use curl for ground truth."),
    ("Two-device sync", "Bookmark sync and the cross-device offer only prove themselves with two signed-in devices "
     "on the same account; one browser with two profiles is the cheapest stand-in."),
]

SIGNOFF = [
    ("Phone · Safari", "Open cold · Turn pages · Marks · Chapter end · Focus"),
    ("Phone · PWA", "Open cold · Offline reopen · Toasts vs player"),
    ("Android · Chrome", "Turn pages · Scrubber target · Back gesture"),
    ("iPad · both orientations", "Tablet default width · Two-thumb zones · Rotation"),
    ("Laptop", "Extra-wide · Keyboard · Aa panel"),
    ("Two devices, signed in", "Bookmark sync · Cross-device offer · Pace stays per device"),
]


def render() -> str:
    p = [head_from_ideas(), EXTRA_STYLE, "</head><body>\n"]

    # Page 1 — title block, why, three tiers
    p.append(
        '<div class="cover">\n  <div class="mark">OCHORUS</div>\n  <div class="rule"></div>\n'
        '  <h1>Testing the Reader on Real Devices</h1>\n'
        '  <div class="sub">How to check the reader improvements on phones, tablets and laptops — three tiers, '
        'a device matrix, a walkthrough and the traps</div>\n'
        '  <div class="meta"><span class="tag">Reader batches 1–2 · September 2026</span></div>\n</div>\n'
    )
    p.append(
        '<section class="intro">\n  <h2>Three tiers, cheapest first</h2>\n'
        '  <p>Most reader bugs are layout and pointer-logic bugs, and emulation finds those in minutes. A smaller '
        'set are physics and platform bugs — scroll feel, safe areas, Safari — and only a real device finds those. '
        'A last few only show on production, after a deploy. Spend time in that order.</p>\n'
    )
    for i, (h, body, watch) in enumerate(TIERS, 1):
        p.append(
            f'  <div class="tier"><div class="num">{i}</div><div>\n    <h3>{h}</h3>\n    <p>{body}</p>\n'
            f'    <p class="small"><span class="lbl watch">Check</span>{watch}</p>\n  </div></div>\n'
        )
    p.append(
        '  <div class="callout">\n    <span class="k">The rule</span>\n'
        '    Never call a feature absent until the service worker is unregistered, site data is cleared, and the '
        'bundle hashes prove the build you are looking at is the one you shipped.\n  </div>\n</section>\n'
    )

    # Page 2 — matrix + setup
    p.append('<section class="page">\n  <h2>A device matrix that covers the risk</h2>\n'
             '  <p class="lede">Four devices, each on the list for something the others cannot show.</p>\n'
             '  <table><tr><th>Device</th><th>What it alone reveals</th></tr>\n')
    for k, v in MATRIX:
        p.append(f'    <tr><td class="k">{esc(k)}</td><td>{v}</td></tr>\n')
    p.append('  </table>\n  <h2>Setup recipes</h2>\n'
             '  <p class="lede">Copy-paste; the two env files must agree on the Mac’s LAN address.</p>\n')
    for k, code in SETUP:
        p.append(f'  <div class="prompt"><span class="plabel">{esc(k)}</span><code>{esc(code)}</code></div>\n')
    p.append('</section>\n')

    # Page 3 — walkthrough
    p.append('<section class="page">\n  <h2>The walkthrough, on each device</h2>\n'
             '  <p class="lede">In this order, once signed out and once signed in — sync and the toast stack behave '
             'differently. Tick as you go.</p>\n  <div class="two">\n')
    for k, items in WALK:
        p.append(f'    <div><h3 style="margin:4px 0 5px;font-size:11.5pt">{esc(k)}</h3>\n      <ul class="check">\n')
        for it in items:
            p.append(f'        <li>{it}</li>\n')
        p.append('      </ul>\n    </div>\n')
    p.append('  </div>\n')
    # The signed-in, two-device pass
    p.append('  <h2 style="margin-top:12px">The two-device pass</h2>\n'
             '  <p class="lede">Same account on both. A and B can be two browser profiles on one Mac for a first '
             'pass; the real thing is a phone and a laptop.</p>\n  <ol style="font-size:9.6pt;margin:0;padding-left:18px">\n')
    for step in [
        "On <b>A</b>, open a book and read to chapter 7; scroll a few paragraphs in. Wait a second for the push.",
        "On <b>B</b>, having last read chapter 3 of the same book, open chapter 3 from the book page. Within a second the "
        "pill says <i>You’re further along on another device · Continue · ch. 7</i>. Take it: you land on A’s paragraph "
        "and no “back to where you were” pill follows.",
        "Turn a chapter on B: no second pill. Dismiss holds for the book until the page is reloaded.",
        "On <b>B</b>, reopen chapter 3 without scrolling, then check A: A’s position on the server is unchanged — a bare "
        "open no longer counts as reading. Scroll on B, and it does.",
        "Bookmark a paragraph on A; open the contents drawer on B: it is there. Remove it on B, Undo, check A still "
        "has it after a reload.",
        "Read for ten minutes on A: A’s footer says <i>· at your pace</i>; B’s does not — pace is per device.",
    ]:
        p.append(f'    <li style="margin:0 0 4px">{step}</li>\n')
    p.append('  </ol>\n</section>\n')

    # Page 4 — traps + sign-off
    p.append('<section class="page">\n  <h2>Traps</h2>\n'
             '  <p class="lede">Each of these has cost a session at least once.</p>\n')
    for k, v in TRAPS:
        p.append(f'  <p style="margin:0 0 8px;font-size:9.8pt"><span class="lbl">{esc(k)}</span>{v}</p>\n')
    p.append('  <h2 style="margin-top:14px">Sign-off</h2>\n'
             '  <p class="lede">A release is tested when every row has a date and initials.</p>\n'
             '  <table><tr><th>Device</th><th>Passes</th><th>Date</th><th>By</th></tr>\n')
    for k, v in SIGNOFF:
        p.append(f'    <tr><td class="k">{esc(k)}</td><td>{esc(v)}</td><td style="width:18mm"></td>'
                 f'<td style="width:14mm"></td></tr>\n')
    p.append('  </table>\n  <h2 style="margin-top:6px">Where the code lives</h2>\n'
             '  <p class="lede" style="margin-bottom:4px">For the bug report: name the file and the state you were in.</p>\n'
             '  <table class="tight"><tr><th>Behaviour</th><th>File</th></tr>\n')
    for k, v in [
        ("Page turns, tap zones, swipe", "frontend/src/lib/pageGestures.ts · routes/books/[slug]/[order]/+page.svelte"),
        ("Aa panel, preview, margins, width", "lib/readerPrefs.svelte.ts · lib/components/ReaderControls.svelte"),
        ("Hairline, up-next card, return pill, sync pill", "routes/books/[slug]/[order]/+page.svelte · lib/resumeSync.ts"),
        ("Undo for highlights / notes / bookmarks", "lib/undo.svelte.ts · lib/undoable.ts · lib/components/PwaToasts.svelte"),
        ("Reading pace and time estimates", "lib/pace.ts · lib/readingPace.svelte.ts · lib/reading.ts"),
        ("Position sync (API)", "backend/reading/views.py ProgressView · lib/readingSync.ts · lib/progress.ts"),
    ]:
        p.append(f'    <tr><td class="k">{esc(k)}</td><td style="font-family:var(--mono,monospace);font-size:8.6pt">{esc(v)}</td></tr>\n')
    p.append('  </table>\n'
             '  <div class="foot">OCHORUS · TESTING THE READER ON REAL DEVICES · PREPARED WITH CLAUDE</div>\n'
             '</section>\n</body></html>\n')
    return "".join(p)


def main() -> None:
    OUT_HTML.write_text(render(), encoding="utf-8")
    print("wrote", OUT_HTML, f"({OUT_HTML.stat().st_size // 1024} KB)")
    if not Path(CHROME).exists():
        sys.exit(f"Chrome not found at {CHROME}; open {OUT_HTML} and print to PDF")
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri()],
        check=True, capture_output=True,
    )
    print("wrote", OUT_PDF, f"({OUT_PDF.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
