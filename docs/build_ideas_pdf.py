#!/usr/bin/env python3
"""Build an on-brand (Ochorus paper theme) HTML doc of the 40 improvement ideas —
each with a ready-to-use prompt — with Fraunces + Hanken Grotesk embedded as
base64 woff2. Render to PDF separately with headless Chrome."""
import base64
import html
from pathlib import Path

FONTS = Path.home() / "dev/ochorus/frontend/node_modules/@fontsource-variable"
OUT = Path(__file__).parent / "ideas.html"


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


fraunces = b64(FONTS / "fraunces/files/fraunces-latin-wght-normal.woff2")
hanken = b64(FONTS / "hanken-grotesk/files/hanken-grotesk-latin-wght-normal.woff2")

# --- content -----------------------------------------------------------------
# Each idea: (n, title, what, why, watch, prompt)
CATS = [
    ("A", "Discoverability & SEO", [
        (1, "Prerender / SSR the public pages",
         "Render real HTML for home, /books, each book and author (SvelteKit prerender at build, or adapter-node SSR).",
         "The #1 growth lever — right now none of your content is indexable or shareable.",
         "Build needs the API up; keep the in-app SPA feel for the reader.",
         "In the Ochorus SvelteKit app, make the public pages crawlable: prerender the home, /books, /books/[slug] and new /authors/[slug] routes to real HTML at build time — generate the entries() list from the Django API (all book and author slugs), like Take Root does for topic pages — while keeping the reader an SPA. Confirm the built HTML for a book page contains its real title and description."),
        (2, "Per-page meta + Open Graph / Twitter cards",
         "Unique title, description and og:image per book and author (use the covers).",
         "Accurate search snippets and rich link previews when shared.",
         "Depends on #1 to be crawlable.",
         "Add per-page metadata via <svelte:head> to Ochorus: a unique title, meta description, canonical URL, and Open Graph + Twitter Card tags (og:title/description/image/type) for the home, book and author pages — using each book's cover as og:image. Make sure it ends up in the prerendered HTML."),
        (3, "Structured data (JSON-LD Book / Person / Breadcrumb)",
         "Schema.org markup on books and authors.",
         "Eligibility for Google rich results.",
         "Needs rendered HTML.",
         "Add JSON-LD structured data to Ochorus: schema.org/Book (name, author, description, image, inLanguage) on book pages, schema.org/Person on author pages, and BreadcrumbList on both. Inject it through <svelte:head> so it's present in the prerendered HTML; validate with Google's Rich Results test."),
        (4, "robots.txt + a complete sitemap",
         "Add robots.txt (currently 404) referencing a sitemap that lists every book, author and chapter.",
         "Gives crawlers a clear map of the library.",
         "URLs must match the prerendered routes.",
         "Add a robots.txt to the Ochorus frontend (allow all, reference the sitemap) and generate a sitemap.xml at build time listing the home, /books, every /books/<slug>, every /authors/<slug> and the static pages — pulling the slugs from the Django API."),
        (5, "First-class author pages + canonicals",
         "Real /authors/<slug> routes (biographies are #anchors today) with canonical tags.",
         "Indexable, shareable author hubs and long-tail SEO.",
         "Redirect the old anchors.",
         "Create first-class /authors/[slug] routes in the Ochorus SvelteKit app from the /api/library/authors data — each showing the author's bio, dates and their books — prerendered with a canonical tag. Redirect the old /biographies#<slug> anchors to the new pages."),
    ]),
    ("B", "Reading experience", [
        (6, "Server-side sync of progress, highlights & notes",
         "Persist these to the account — they're localStorage-only now.",
         "The core promise of signing in: read across phone and laptop.",
         "Models + API + a localStorage→server migration; conflict handling.",
         "Add server-side sync to Ochorus for reading progress, highlights and notes: create Django models keyed to the Supabase user (via the existing UserProfile), DRF endpoints to read/write them, and update the frontend stores (progress.ts, marks.svelte.ts) to sync to the API when signed in while keeping localStorage as the offline cache. Merge existing local data on first sign-in."),
        (7, "Offline reading (service worker / PWA)",
         "Cache opened books; make the app installable.",
         "The manifest exists but there's no offline — huge for low-connectivity regions.",
         "Cache-size limits and an update flow.",
         "Make Ochorus a full offline-capable PWA: add a service worker that precaches the app shell and caches book chapters as they're opened (stale-while-revalidate), an 'available offline' indicator, and an update prompt when a new version ships. The web manifest already exists — make the app installable and usable without a network."),
        (8, "Real full-text search",
         "Search across the library and within a book, with jump-to-hit.",
         "/search exists but is likely shallow; readers hunt for passages.",
         "Needs an index — Postgres full-text is free and enough early.",
         "Build real search for Ochorus: a Django/DRF endpoint using Postgres full-text search over Book titles, author names and Chapter text, with ranking and highlighted snippets, and wire the existing /search route to it with result highlighting and deep links straight to the matching chapter."),
        (9, "Listen mode (text-to-speech / audio)",
         "A 'listen' mode via browser TTS or generated narration.",
         "Accessibility plus hands-free devotional listening; broad appeal.",
         "Browser TTS is free but robotic; generated audio is storage/cost, per language.",
         "Add a 'Listen' mode to the Ochorus reader using the browser SpeechSynthesis API: play/pause, highlight-the-paragraph-as-read, speed control and voice selection, with a graceful fallback when TTS is unsupported. Keep it in the reader toolbar alongside the existing controls."),
        (10, "Reading plans & a 'reading of the day'",
         "Curated multi-day plans and a daily excerpt.",
         "Habit-forming retention, perfect for the devotional genre.",
         "Curation plus a small scheduling model.",
         "Add reading plans to Ochorus: a model for an ordered plan of chapters with a daily cadence, a browsable plans page, a 'Day N of M' reader view with progress, and a 'reading of the day' block on the homepage. Seed one or two plans from existing books."),
        (11, "A 'Continue reading' rail",
         "Resume in-progress books on the home page and account.",
         "Re-engagement — brings readers back to where they left off.",
         "Needs progress data (#6).",
         "Add a 'Continue reading' section to the Ochorus homepage and account area listing in-progress books (from synced or local progress), each with a progress bar and a resume link to the exact chapter and scroll position."),
    ]),
    ("C", "Content & library", [
        (12, "AI translation pipeline (multilingual content)",
         "Translate the library into many languages with human/theological review, clearly labeled.",
         "THE differentiator — your hero already says 'in your language soon.'",
         "Review quality, cost, and AI-vs-reviewed labeling.",
         "Build an AI book-translation pipeline for Ochorus: a Django management command `translate_book <slug> <lang>` that translates each chapter with Claude using a theology-aware prompt (preserve meaning, keep Scripture quotations faithful), writes a new per-language Book (source_type=ai_unreviewed), plus a reviewer workflow to promote to ai_reviewed. Label unreviewed translations in the UI. Prove it on one short book into 2–3 languages first."),
        (13, "Grow the catalog",
         "Add Bunyan, à Kempis, Edwards, Ryle, E. M. Bounds, more Spurgeon/Torrey via the book-import skill.",
         "Depth attracts readers and builds long-tail search.",
         "Sourcing quality — the skill makes it fast.",
         "Using the Ochorus book-import skill, add these public-domain titles and generate covers for each: Pilgrim's Progress (Bunyan), The Imitation of Christ (à Kempis), Power Through Prayer (E. M. Bounds), Holiness (J. C. Ryle). Verify chapter structure and titles with the skill's QA scan; re-seed the launch fixture."),
        (14, "Collections / topical shelves",
         "Curated groupings: 'On Prayer', 'Holiness', 'For New Believers'.",
         "Discovery beyond author, and an editorial voice.",
         "A tagging model plus manual curation.",
         "Add curated collections to Ochorus: a Collection model (name, slug, description, ordered books) with admin, a /collections index and detail page, and homepage rails. Seed collections such as 'On Prayer', 'Holiness' and 'For New Believers'."),
        (15, "Finish the content-quality pass",
         "Fix remaining generic chapter titles and the Ochorus Originals collections' repeated sub-titles.",
         "Polish equals trust.",
         "Per-book corrections vs importer fixes — the skill covers both.",
         "Run the Ochorus book-import skill's QA scan, then fix the flagged books: the remaining generic 'Chapter N' titles and the 'Ochorus Originals' biography collections' repeated sub-section titles. Prefer importer improvements for recurring patterns and per-book entries in corrections.py for one-offs; re-seed the fixture."),
        (16, "Author portraits & richer bios",
         "Public-domain portraits, dates, era and external links on author pages.",
         "Richness and SEO.",
         "Image sourcing and licensing.",
         "Enrich Ochorus author pages: add a photo_url to the Author model, source public-domain portraits, and show the portrait, birth/death years, era and a longer bio with external links on the /authors/[slug] page."),
    ]),
    ("D", "Design & UX", [
        (17, "Real cover art for the SVG-covered books",
         "Designed covers (or a richer SVG generator) for All of Grace, Cheque Book, etc.",
         "The photographic ochorus.com covers outshine the flat SVGs side-by-side.",
         "Design effort; keep the SVG fallback.",
         "Improve Ochorus's generated book covers: upgrade the generate_covers command to produce richer SVGs — a subtle paper/linen texture, a small ornament or author monogram, and stronger type hierarchy — so the CCEL/Gutenberg titles look as premium as the photographic ochorus.com covers. Keep the current flat SVG as a fallback."),
        (18, "A homepage editorial layer",
         "Book-of-the-week, rotating quotes, 'recently added', a mission band.",
         "Warmth and repeat visits.",
         "Content upkeep.",
         "Add an editorial layer to the Ochorus homepage: a 'Book of the week' feature, a rotating public-domain quote band, a 'Recently added' rail and a short mission section — all data-driven from the API so they stay fresh."),
        (19, "Skeleton loaders & graceful empty/error states",
         "Shelf and reader placeholders instead of blank; a friendly API-down state.",
         "Perceived speed, especially on cold starts and slow networks.",
         "SSR (#1) reduces the need.",
         "Add skeleton loaders and graceful states to Ochorus: shimmer placeholders for the shelf and reader while data loads, a friendly 'the library is waking up' state for API cold starts, and clear empty/error states for search and the book list."),
        (20, "Progress indicators on covers",
         "A progress ring or '12% · 3 min left' on in-progress books.",
         "Motivation to keep going.",
         "Needs progress (#6).",
         "Show reading progress on Ochorus book cards: a small progress ring or a '12% · 3 min left' badge on in-progress books across the shelf and homepage, driven by synced or local progress."),
        (21, "Accessibility (WCAG) pass",
         "Contrast, focus states, ARIA, keyboard nav, alt text, reduced-motion.",
         "The right thing, plus legal and reach; your readers skew older.",
         "An audit plus ongoing discipline.",
         "Do a WCAG 2.1 AA accessibility pass on Ochorus: check colour contrast in both themes, add visible focus states, ARIA labels, full keyboard navigation for the reader and menus, alt text on covers, and prefers-reduced-motion support. Produce a report and fix the issues."),
        (22, "Reader typography refinement",
         "Drop caps, scripture/blockquote styling, footnotes, hyphenation, optimal measure.",
         "It's a reading app — type is the product.",
         "Per-language font coverage.",
         "Refine the Ochorus reader typography: proper drop caps, distinct scripture/blockquote styling, small-caps for reference lines, footnote handling, hyphenation and an optimal measure — all configurable per language and reading font."),
    ]),
    ("E", "Architecture, performance & reliability", [
        (23, "Cover image optimization + self-hosting / CDN",
         "Resize/compress to WebP with srcset; host your own copies instead of hotlinking ochorus.com.",
         "Page weight, speed in low-bandwidth regions, and one fewer external dependency.",
         "An image-derivative pipeline.",
         "Add cover-image optimization to Ochorus: a pipeline that downloads each ochorus.com cover, generates resized WebP derivatives, stores them (served from the frontend/CDN), and updates the shelf to use responsive srcset — removing the runtime hotlink to ochorus.com."),
        (24, "API pagination + slimmer payloads",
         "Paginate /books and trim list fields.",
         "The 26 KB full list is fine at 36 books, not at 500.",
         "Frontend shelf changes.",
         "Add pagination to the Ochorus /api/library/books endpoint (page/limit + total count) and slim the list serializer, then update the SvelteKit shelf to page or lazy-load while keeping the grouped-by-author UX."),
        (25, "Error monitoring (Sentry) + uptime alerts",
         "Wire Sentry front and back; add an uptime monitor.",
         "You can't fix what you can't see.",
         "Free tiers exist; reuse the Take Root Sentry pattern.",
         "Wire Sentry into Ochorus front and back (SvelteKit + Django), gated on env vars, with source-map upload on the frontend build, and add an uptime monitor that pings /api/health/. Follow the Take Root Sentry setup pattern."),
        (26, "Automated tests + CI (GitHub Actions)",
         "Backend tests (importers/API), a few Playwright e2e, run on every PR.",
         "Confidence — you've already had parallel-work merge churn.",
         "Upfront effort, worth it now.",
         "Set up GitHub Actions CI for Ochorus: run the Django tests and `manage.py check`, frontend `svelte-check` and build, and a couple of Playwright e2e (home loads books, a chapter opens) on every PR. Add starter tests for the importers and the library API."),
        (27, "Backups & a restore runbook",
         "Verify Supabase backups; content is reproducible from the fixture, accounts and highlights aren't.",
         "Don't lose reader data.",
         "Free-tier backup limits.",
         "Document and verify backups for Ochorus: confirm Supabase automated backups cover the user data (accounts, highlights, notes, progress), write a restore runbook, and note that library content is reproducible from the launch fixture but user data is not."),
        (28, "Security hardening (CSP, rate limiting, headers)",
         "Add a Content-Security-Policy, throttle the API, lock down admin.",
         "A public site with auth is a real surface.",
         "CSP can break inline scripts — test.",
         "Harden Ochorus: add a Content-Security-Policy and standard security headers to the frontend, enable DRF throttling on the API, lock down the Django admin (allowed hosts, strong credentials), and pin the Supabase JWT algorithm. Verify the CSP doesn't break the app."),
        (29, "Privacy-respecting analytics",
         "Plausible or Umami (cookieless) to see traffic, popular books and drop-off.",
         "Data-driven decisions for a growing mission.",
         "Pick cookieless to avoid consent friction.",
         "Add privacy-respecting, cookieless analytics (Plausible or Umami) to Ochorus to track page views, most-read books and reader drop-off without a consent banner. Wire the tracking snippet and confirm it doesn't set cookies."),
        (30, "Cost / hosting right-sizing",
         "Revisit the always-on Starter API vs free tier; plan CDN/caching as traffic grows.",
         "It's a free ministry — control the burn.",
         "Free tier means cold starts.",
         "Review Ochorus hosting for cost vs performance: compare the always-on Render Starter API against the free tier (cold starts), add cache/CDN headers for the public read API, and document the tradeoffs and a scaling plan for when traffic grows."),
    ]),
    ("F", "Accounts, community & engagement", [
        (31, "Complete auth flows + a welcome email",
         "Email verification, reset, magic link, maybe Google sign-in.",
         "Accounts unlock sync and retention.",
         "Supabase email templates plus SMTP deliverability.",
         "Complete the Ochorus auth flows on Supabase: email verification, password reset, magic-link sign-in, optional Google OAuth, a branded welcome email, and polished sign-up/in UI in the AccountMenu. Ensure the redirect URLs are configured for the production domain."),
        (32, "A 'My Library' page",
         "Highlights, notes, bookmarks and finished books — viewable and exportable.",
         "The payoff of an account, and a study aid.",
         "Depends on server sync (#6).",
         "Add a 'My Library' page to Ochorus for signed-in users: finished and in-progress books, all highlights and notes grouped by book, bookmarks, and an export to Markdown/PDF. Build on the server-side sync of marks and progress."),
        (33, "Shareable quote cards",
         "Turn a highlighted passage into a branded image or share link.",
         "Organic, word-of-mouth growth.",
         "Image generation plus OG (#2).",
         "Add shareable quote cards to Ochorus: from a highlighted passage, generate a branded image (paper theme, Fraunces, book + author attribution) and a share link with an OG preview, surfaced from the existing selection bar."),
        (34, "Newsletter / new-book digest",
         "Capture the emails your footer already invites; announce new titles.",
         "Retention and the ministry's audience.",
         "An email service, consent and a cadence.",
         "Add newsletter capture to Ochorus: wire the footer email prompt to an email provider (e.g. Buttondown or Mailchimp) with double opt-in, store consent, and set up a simple 'new books this month' send."),
        (35, "Lightweight personal stats",
         "Books read, streaks, minutes — no heavy social.",
         "Gentle motivation.",
         "Keep it devotional, not vanity metrics.",
         "Add lightweight personal reading stats to Ochorus, computed from synced progress and shown on the account page: books finished, current streak and total minutes read — kept gentle and devotional, not vanity metrics."),
    ]),
    ("G", "Mission, growth & governance", [
        (36, "Native mobile apps (Capacitor)",
         "Wrap the SPA for iOS/Android with offline and push.",
         "The vision is web and mobile; app-store reach.",
         "Store review and maintenance — reuse the PUBLIC_TARGET pattern.",
         "Wrap Ochorus as native iOS and Android apps with Capacitor, reusing the SvelteKit build and the PUBLIC_TARGET pattern: offline reading, push notifications for reading plans, and store-ready configuration. Document the build and release steps."),
        (37, "'Support this ministry' (donations)",
         "An optional Stripe/PayPal giving link.",
         "Sustainability for hosting and translation costs.",
         "Keep it gentle — it's a ministry, not a store.",
         "Add a gentle 'Support this ministry' page to Ochorus with a Stripe/PayPal giving option (one-time and monthly), reachable from the footer and About page, framed as sustaining free books and translations — non-intrusive. (I'll set up the payment account manually.)"),
        (38, "Full UI localization + RTL",
         "Complete UI translations for target languages; add right-to-left (Arabic/Urdu).",
         "Pairs with #12 for true multilingual reach.",
         "dir='auto' is already in the reader; RTL needs CSS work.",
         "Complete Ochorus UI localization: fill in the i18n translations for the target languages, add a new locale, and add full right-to-left (RTL) support — layout, icons and reader — for Arabic and Urdu. The reader already uses dir='auto' as a starting point."),
        (39, "Offline / print bundles & partnerships",
         "Downloadable book packs, a print-friendly mode, church/mission partnerships.",
         "Reach people the open web doesn't — squarely your mission.",
         "Logistics; your content, so licensing is easy.",
         "Add offline/print distribution to Ochorus: per-book downloadable bundles (EPUB and PDF), a print-friendly reader stylesheet, and a low-bandwidth mode — aimed at church and mission partners and readers with poor connectivity."),
        (40, "Legal + in-app feedback",
         "Privacy Policy, Terms, cookie/consent, plus a 'report a typo / suggest a book' link.",
         "Trust and compliance (you now collect emails + accounts) and crowdsourced quality.",
         "Keep policies honest and specific.",
         "Add legal and feedback to Ochorus: a real Privacy Policy, Terms of Service and a cookie/consent notice (you now collect emails and accounts), plus an in-app 'report a typo / suggest a book' widget that files to email or an issue tracker."),
    ]),
]

WAVES = [
    ("Wave 1 — Be findable & safe",
     "#1 SSR/prerender, then what it unlocks: #2 OG/meta, #3 structured data, #4 robots/sitemap, #5 author pages. Bundle the cheap safety wins: #25 Sentry+uptime, #29 analytics, #40 privacy/terms.",
     "SEO is your growth engine and it's currently near-zero; #1 is a prerequisite for #2/#3/#33; monitoring and legal are quick and protect you as traffic arrives."),
    ("Wave 2 — Make accounts worth it",
     "#6 server-side sync → #32 My Library → #31 auth polish → #11 continue-reading → #20 progress on covers.",
     "Login exists but syncs almost nothing today; this turns it into real value and retention. #6 gates the rest."),
    ("Wave 3 — The differentiator + reach",
     "#12 translation pipeline (start small: 2–3 languages on short books), in parallel with #13 more books and #15 quality pass; then #7 offline/PWA and #23 image optimization; #38 localization/RTL.",
     "This is what makes Ochorus special and extends reach to your actual mission field."),
    ("Wave 4 — Grow the audience",
     "#36 mobile apps, #33 quote sharing, #34 newsletter, #18 homepage editorial, #10 reading plans, #37 donations.",
     "Once it's findable, valuable and multilingual, invest in acquisition, virality and sustainability."),
    ("Wave 5 — Depth & polish (ongoing)",
     "#8 search, #9 listen mode, #14 collections, #16 author portraits, #17 covers, #21 accessibility, #22 typography, #24 pagination, #26 CI/tests, #27 backups, #28 security, #19 loading states, #30 hosting, #35 stats, #39 bundles.",
     "High-value refinements best done continuously rather than blocking launch-critical work."),
]


def esc(s):
    return html.escape(s)


def idea_html(n, title, what, why, watch, prompt):
    return f"""<div class="idea">
      <div class="num">{n}</div>
      <div class="idea-body">
        <h3>{esc(title)}</h3>
        <p><span class="lbl">What</span>{esc(what)}</p>
        <p><span class="lbl">Why</span>{esc(why)}</p>
        <p><span class="lbl watch">Watch</span>{esc(watch)}</p>
        <div class="prompt"><span class="plabel">Prompt</span><code>{esc(prompt)}</code></div>
      </div>
    </div>"""


sections = ""
for letter, name, ideas in CATS:
    items = "\n".join(idea_html(*i) for i in ideas)
    sections += f"""<section class="cat">
      <div class="cat-head"><span class="badge">{letter}</span><h2>{esc(name)}</h2></div>
      {items}
    </section>\n"""

waves = ""
for title, items, why in WAVES:
    waves += f"""<div class="wave">
      <h3>{esc(title)}</h3>
      <p class="wave-items">{esc(items)}</p>
      <p class="wave-why"><span class="lbl">Why</span>{esc(why)}</p>
    </div>\n"""

DOC = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<style>
@font-face {{ font-family:'Fraunces'; src:url(data:font/woff2;base64,{fraunces}) format('woff2'); font-weight:100 900; font-display:block; }}
@font-face {{ font-family:'Hanken'; src:url(data:font/woff2;base64,{hanken}) format('woff2'); font-weight:100 900; font-display:block; }}
:root{{
  --bg:#faf6ef; --surface:#ffffff; --surface-2:#f4eee3; --text:#221c15; --muted:#6e6358;
  --accent:#3f3d9a; --gold:#b07d22; --border:#e8dfcf; --soft:#ecebf7; --soft-b:#d9d7f0;
  --serif:'Fraunces',Georgia,serif; --sans:'Hanken','Helvetica Neue',Arial,sans-serif;
  --mono:'SF Mono','SFMono-Regular','Menlo','Consolas',monospace;
}}
@page {{ size: A4; margin: 17mm 15mm; }}
*{{ box-sizing:border-box; }}
html,body{{ margin:0; padding:0; }}
body{{ font-family:var(--sans); color:var(--text); background:var(--bg); font-size:10.5pt; line-height:1.5; }}

/* Cover */
.cover{{ height:263mm; display:flex; flex-direction:column; justify-content:center; text-align:center; page-break-after:always; }}
.cover .mark{{ font-family:var(--serif); font-weight:600; letter-spacing:.42em; color:var(--gold); font-size:13pt; text-indent:.42em; }}
.cover .rule{{ width:54px; height:2px; background:var(--accent); margin:20px auto 26px; }}
.cover h1{{ font-family:var(--serif); font-weight:600; font-size:40pt; line-height:1.05; letter-spacing:-.01em; color:var(--text); margin:0 0 14px; }}
.cover .sub{{ font-family:var(--serif); font-size:15.5pt; color:var(--muted); font-style:italic; margin:0 auto; max-width:130mm; line-height:1.35; }}
.cover .meta{{ margin-top:38px; color:var(--muted); font-size:9.5pt; }}
.cover .meta a{{ color:var(--accent); text-decoration:none; }}
.cover .tag{{ margin-top:6px; font-size:8.5pt; letter-spacing:.04em; }}

/* Intro */
.intro h2{{ font-family:var(--serif); font-weight:600; font-size:19pt; margin:0 0 8px; }}
.intro p{{ max-width:165mm; color:#3a332a; }}
.callout{{ background:var(--surface); border:1px solid var(--border); border-left:4px solid var(--accent);
  border-radius:10px; padding:14px 18px; margin:16px 0 8px; }}
.callout .k{{ font-family:var(--sans); font-weight:700; color:var(--accent); text-transform:uppercase; letter-spacing:.06em;
  font-size:8pt; display:block; margin-bottom:4px; }}
.callout strong{{ color:var(--text); }}

/* Category */
.cat{{ margin-top:20px; }}
.cat-head{{ display:flex; align-items:center; gap:10px; border-bottom:1px solid var(--border); padding-bottom:7px; margin-bottom:11px; }}
.cat-head .badge{{ font-family:var(--serif); font-weight:600; color:#fff; background:var(--accent);
  width:26px; height:26px; border-radius:7px; display:flex; align-items:center; justify-content:center; font-size:12pt; }}
.cat-head h2{{ font-family:var(--serif); font-weight:600; font-size:16.5pt; margin:0; color:var(--text); }}

/* Idea card */
.idea{{ display:flex; gap:12px; background:var(--surface); border:1px solid var(--border); border-radius:10px;
  padding:12px 15px; margin-bottom:9px; page-break-inside:avoid; }}
.idea .num{{ font-family:var(--serif); font-weight:600; font-size:15pt; color:var(--accent);
  min-width:24px; text-align:right; line-height:1.15; }}
.idea-body{{ flex:1; }}
.idea-body h3{{ font-family:var(--sans); font-weight:700; font-size:11.5pt; margin:0 0 5px; color:var(--text); letter-spacing:-.005em; }}
.idea-body>p{{ margin:0 0 3px; color:#3a332a; font-size:9.7pt; line-height:1.45; }}
.lbl{{ font-family:var(--sans); font-weight:700; font-size:7.4pt; text-transform:uppercase; letter-spacing:.07em;
  color:var(--accent); display:inline-block; min-width:38px; margin-right:2px; }}
.lbl.watch{{ color:var(--gold); }}
.prompt{{ margin-top:8px; background:var(--soft); border:1px solid var(--soft-b); border-radius:7px; padding:8px 11px; }}
.prompt .plabel{{ font-family:var(--sans); font-weight:700; font-size:7pt; letter-spacing:.1em; text-transform:uppercase;
  color:var(--accent); display:block; margin-bottom:4px; }}
.prompt code{{ font-family:var(--mono); font-size:8.3pt; line-height:1.5; color:#322d5a; white-space:pre-wrap; word-break:break-word; }}

/* Waves */
.order{{ page-break-before:always; }}
.order h2{{ font-family:var(--serif); font-weight:600; font-size:19pt; margin:0 0 4px; }}
.order .lede{{ color:var(--muted); margin:0 0 14px; }}
.wave{{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:13px 16px; margin-bottom:10px; page-break-inside:avoid; }}
.wave h3{{ font-family:var(--serif); font-weight:600; font-size:13pt; color:var(--accent); margin:0 0 5px; }}
.wave-items{{ margin:0 0 5px; font-size:9.7pt; }}
.wave-why{{ margin:0; color:var(--muted); font-size:9.4pt; }}
.wave-why .lbl{{ color:var(--gold); }}
.three{{ margin-top:14px; font-family:var(--serif); font-size:11.5pt; color:var(--text); font-style:italic; }}
.three b{{ color:var(--accent); font-style:normal; }}
.foot{{ text-align:center; color:var(--muted); font-size:8pt; letter-spacing:.05em; margin-top:26px; padding-top:10px; border-top:1px solid var(--border); }}
</style></head><body>

<div class="cover">
  <div class="mark">OCHORUS</div>
  <div class="rule"></div>
  <h1>Improvement Ideas</h1>
  <div class="sub">40 ideas for the site, architecture &amp; design —<br>each with a ready-to-use prompt</div>
  <div class="meta">
    A review of <a>ochorus-web.onrender.com</a><br>
    <span class="tag">Equipping people with classic Christian books · A ministry since 2021 · Kampala, Uganda</span>
  </div>
</div>

<section class="intro">
  <h2>How to read this</h2>
  <p>Forty varied ideas across discoverability, reading experience, content, design, architecture,
  community and mission — each with <b>what</b> it is, <b>why</b> it helps, what to <b>watch</b> for, and a
  copy-paste <b>prompt</b> you can hand to an AI coding assistant to build it against the Ochorus codebase.
  A recommended order follows at the end.</p>
  <div class="callout">
    <span class="k">The one finding that shapes the list</span>
    Ochorus is currently a <strong>pure client-side app with no per-page rendering</strong>: the homepage ships an
    almost-empty HTML shell, and a book page's title is just &ldquo;Ochorus&rdquo; with the book&rsquo;s text nowhere in the
    source. So search engines and social crawlers see <strong>empty pages</strong> — a free library whose whole mission is
    reach is, today, nearly invisible to search. Fixing that (Wave&nbsp;1) is the highest-leverage change.
  </div>
</section>

{sections}

<section class="order">
  <h2>Recommended order</h2>
  <p class="lede">Sequenced by impact &times; dependency, in five waves.</p>
  {waves}
  <p class="three">If you could only do three next: <b>#1 SSR/SEO</b>, <b>#6 sync</b>, and start <b>#12 translation</b> — findable, sticky, and unique.</p>
  <div class="foot">OCHORUS · IMPROVEMENT IDEAS · PREPARED WITH CLAUDE</div>
</section>

</body></html>"""

OUT.write_text(DOC, encoding="utf-8")
print("wrote", OUT, f"({len(DOC)//1024} KB, fonts embedded)")
