"""Regenerate docs/ochorus-code-review-2026-08.{pdf,md}.

    pip install reportlab && python3 docs/build-code-review-pdf.py

The PDF is committed because it is the artefact people read; this script is
committed so the artefact stays editable — restyling it, or folding in a later
review pass, means editing the FINDINGS below rather than rebuilding a generator
from scratch.

Both outputs come from the same source of truth: the `add(...)` calls build the
finding list once, the PDF renders it, and the Markdown companion is written from
the same data so the two can never drift. Section sizes are asserted against the
finding count, so adding a finding without placing it in a section fails loudly.

Content note: the findings are a snapshot of the 2026-08 review. Many have since
been fixed (see the git history for waves 1-4); this file is the report as
written, not a live checklist.
"""

import html
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

OUT = str(Path(__file__).resolve().parent / "ochorus-code-review-2026-08.pdf")

# ---- palette -------------------------------------------------------------
INK      = colors.HexColor("#1f2933")
MUTED    = colors.HexColor("#52606d")
FAINT    = colors.HexColor("#7b8794")
PAPER    = colors.HexColor("#ffffff")
BRAND    = colors.HexColor("#3b5b73")   # deep slate blue
BRAND_DK = colors.HexColor("#263c4d")
RULE     = colors.HexColor("#d9e0e6")
BAND     = colors.HexColor("#f4f6f8")
CODEBG   = colors.HexColor("#f2f4f7")

SEV = {
    "CRITICAL": colors.HexColor("#9b1c1c"),
    "HIGH":     colors.HexColor("#c2410c"),
    "MEDIUM":   colors.HexColor("#a16207"),
    "LOW":      colors.HexColor("#3f6212"),
}
SEV_BG = {
    "CRITICAL": colors.HexColor("#fdecec"),
    "HIGH":     colors.HexColor("#fdeee2"),
    "MEDIUM":   colors.HexColor("#fbf3dc"),
    "LOW":      colors.HexColor("#eef6e2"),
}

# ---- styles --------------------------------------------------------------
ss = getSampleStyleSheet()

def mk(name, **kw):
    parent = kw.pop("parent", ss["Normal"])
    return ParagraphStyle(name, parent=parent, **kw)

st_body   = mk("body", fontName="Helvetica", fontSize=9.3, leading=13.4, textColor=INK, spaceAfter=4)
st_label  = mk("label", fontName="Helvetica-Bold", fontSize=7.4, leading=10, textColor=BRAND, spaceAfter=1)
st_what   = mk("what", parent=st_body, textColor=INK)
st_why    = mk("why", parent=st_body, textColor=MUTED)
st_fix    = mk("fix", fontName="Helvetica-Oblique", fontSize=8.8, leading=12.6, textColor=BRAND_DK)
st_file   = mk("file", fontName="Courier", fontSize=8, leading=11, textColor=MUTED)
st_ftitle = mk("ftitle", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=INK, spaceAfter=2)
st_sect   = mk("sect", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=BRAND_DK, spaceBefore=4, spaceAfter=2)
st_sectd  = mk("sectd", fontName="Helvetica", fontSize=9, leading=12.5, textColor=MUTED, spaceAfter=6)
st_h2     = mk("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=BRAND_DK, spaceBefore=10, spaceAfter=4)
st_intro  = mk("intro", fontName="Helvetica", fontSize=10, leading=15, textColor=INK, spaceAfter=7)
st_cap    = mk("cap", fontName="Helvetica", fontSize=8, leading=11, textColor=FAINT)

def hx(c):
    return "#" + c.hexval()[2:]

def esc(s):
    return html.escape(str(s), quote=False)

# ---- findings data -------------------------------------------------------
# each: (num, sev, title, files, what, why, fix)
F = []
def add(sev, title, files, what, why, fix):
    F.append({"sev": sev, "title": title, "files": files, "what": what,
              "why": why, "fix": fix})

# ===== A. Security & authentication =====
SEC_A = ("A", "Security &amp; authentication",
    "The trust boundary between the Supabase JWT layer, the email-allowlist admin gate, and the public API.")

add("CRITICAL",
    "Admin allowlist trusts the unverified email claim in the JWT",
    "backend/accounts/authentication.py:107; backend/accounts/permissions.py:44",
    "_get_or_create_user copies the token's email claim onto the Django user with no check of an email_verified claim, and is_admin_user grants admin purely on user.email in ADMIN_EMAILS. If the Supabase project has email confirmation disabled, anyone can register with the admin's email, receive a validly-signed token bearing it, and be treated as admin.",
    "Full takeover of every /api/admin/* endpoint (publish content, create authors/languages, trigger deploys, file GitHub jobs) by anyone who can obtain a signed token with the admin's address — no mailbox access required.",
    "In backend/accounts/authentication.py, after decoding the token reject or downgrade any JWT whose email_verified (or user_metadata.email_verified) claim is not truthy before trusting email for authorization. Ensure permissions.is_admin_user only considers a verified email, and add a test that an unverified-email token is never treated as admin even when the address is on ADMIN_EMAILS.")

add("MEDIUM",
    "JWT decode does not verify the issuer and takes the algorithm from the token header",
    "backend/accounts/authentication.py:68",
    "_decode reads alg from the unverified token header and passes algorithms=[alg] with no issuer check. exp and aud are enforced and the HS secret is correctly sourced separately, but issuer is never validated and the audience check silently disables if SUPABASE_JWT_AUDIENCE is set empty.",
    "Defense-in-depth gap: a signature that validates against the configured keys but was minted for a different issuer/audience context is not rejected on those grounds.",
    "In backend/accounts/authentication.py, pass an explicit issuer=f'{settings.SUPABASE_URL}/auth/v1' to jwt.decode and require it, constrain algorithms to the specific expected set per key type (e.g. ES256/RS256 for JWKS, HS256 for the secret path) rather than echoing the token's alg, and fail closed when the audience setting is empty. Add tests for wrong-issuer and unexpected-alg tokens.")

add("MEDIUM",
    "Open redirect via the login 'redirect' query parameter",
    "frontend/src/routes/login/+page.svelte:24",
    "redirectTarget is read straight from $page.url.searchParams.get('redirect') and passed to goto() after sign-in with no validation that it is a local same-origin path. A value like //evil.com or https://evil.com is honoured as a navigation target.",
    "A crafted …/login?redirect=//evil.com link sends a freshly-authenticated user to an attacker site, trading on the trust of the real login page (phishing / token relay).",
    "In frontend/src/routes/login/+page.svelte validate the redirect param before use: accept it only if it begins with a single '/' and not '//', otherwise fall back to localizeHref('/'). Add a unit test covering //evil.com, https://evil.com, and a valid /books/x path.")

add("LOW",
    "DRF Browsable API renderer is enabled in production",
    "backend/config/settings.py:140",
    "DEFAULT_RENDERER_CLASSES includes BrowsableAPIRenderer unconditionally, so every endpoint — including /api/admin/* — serves an interactive HTML explorer with forms and serializer metadata to any browser sending Accept: text/html, in production.",
    "Unnecessary attack surface and information disclosure: it advertises endpoint shapes and forms to probers and serves no purpose to a JSON-only SPA.",
    "In backend/config/settings.py set DEFAULT_RENDERER_CLASSES to JSONRenderer only, then append BrowsableAPIRenderer after the DEBUG flag is computed when DEBUG is true. Verify the admin dashboard and frontend still work against the JSON-only renderer.")

add("LOW",
    "Django admin mounted at the predictable /admin/ with no rate limiting",
    "backend/config/urls.py:35",
    "The full Django admin (admin.site.urls) is mounted at /admin/ with session auth separate from the Supabase JWT layer and no brute-force protection. The project otherwise has no is_staff concept, so this is a distinct, easily-found credential-login surface.",
    "A discoverable password-login endpoint invites credential-stuffing against any superuser account; a compromise there is unrestricted DB access.",
    "In backend/config/urls.py move the Django admin to an env-configurable non-obvious path and add login rate limiting (e.g. django-axes) or a network restriction. Confirm no automation depends on the /admin/ path before moving it.")

add("LOW",
    "Publish endpoint stores external URLs with only a scheme-prefix check",
    "backend/library/upload_import.py:218",
    "_http_url accepts any string starting with http:// or https:// and stores it as source_url/cover_url; these are later emitted to readers as <img src>. There is no host allowlist and non-TLS http:// is permitted. The values are not fetched server-side (so not SSRF), but they are unvalidated stored URLs on an admin write.",
    "A stored http:// cover causes mixed-content on the HTTPS reader, and an unconstrained external cover host can track readers via image requests.",
    "In backend/library/upload_import.py tighten _http_url to require https:// and optionally validate the host against an allowlist (or store covers locally). Ensure cover_url/source_url render safely on the frontend. Add tests for rejected schemes/hosts.")

add("LOW",
    "Popular Searches echoes raw reader query text publicly",
    "backend/library/views.py:512",
    "PopularSearchesView is AllowAny and returns the raw lowercased text of reader queries above frequency thresholds (MIN_COUNT>=5, MIN_DISTINCT>=4). The privacy protection is purely structural; the endpoint reflects reader-entered strings verbatim to anyone and, combined with the unthrottled logging below, is seedable.",
    "On low-traffic locales a handful of repeated queries can surface partial reader input publicly.",
    "Review PopularSearchesView in backend/library/views.py: consider an admin-only or curated-allowlist mode and ensure the frequency thresholds are high enough on production traffic that no low-volume reader text is echoed. Add a test asserting sub-threshold queries never appear.")

# ===== B. Backend correctness & robustness =====
SEC_B = ("B", "Backend correctness &amp; robustness",
    "The reading-sync merge path — the reconciliation that must never lose or corrupt a reader's offline work.")

add("HIGH",
    "Merge and PUT endpoints 500 with AttributeError on malformed JSON",
    "backend/reading/views.py:319",
    "_merge_progress, _merge_favorites, _merge_marks and _merge_sermon_marks iterate request.data.get(...) or [] and immediately call row.get(...) without checking the container is a list or the row is a dict — only _merge_plan_progress and _merge_activity have those guards. Verified: {'progress':'oops'}, {'favorites':[42]}, {'marks':[42]} and a bare JSON array body all raise AttributeError -> 500.",
    "The first-sign-in merge is the critical reconciliation path; one malformed field in a client bundle (a stale localStorage shape, a buggy PWA build) aborts the whole merge with a 500 instead of skipping the bad rows.",
    "In backend/reading/views.py harden every _merge_* helper: return early when incoming is not a list and continue on non-dict rows (mirroring the existing guards in _merge_plan_progress); in MarksView.put, ProgressView.put and SermonMarksView.put treat a non-dict request.data as {} like SearchClickView does. Add tests posting a string, an int-list and an array body to each endpoint asserting no 500.")

add("HIGH",
    "Unbounded merge fan-out — authenticated write-amplification with no throttle",
    "backend/reading/views.py:357",
    "MAX_ACTIVITY_MERGE caps only _merge_activity. Favorites, marks, progress, sermon-marks and plan-progress iterate the full incoming list with no cap, issuing 1-3 queries per row, and slugs are arbitrary strings so every row creates a new DB row. No /api/reading/ endpoint carries a throttle.",
    "Any signed-up user can send one POST with a million favorite rows and drive millions of sequential queries on a Render worker, or grow the tables without limit.",
    "In backend/reading/views.py cap every merge list to a per-type maximum (reuse the MAX_ACTIVITY_MERGE pattern), convert _merge_activity/_merge_favorites to bulk_create(ignore_conflicts=True), and add a per-user throttle scope for the reading endpoints in settings.REST_FRAMEWORK DEFAULT_THROTTLE_RATES applied to MergeView at minimum. Add a test asserting an oversized bundle is truncated, not fully written.")

add("MEDIUM",
    "MergeView is not atomic — a mid-merge failure leaves half-applied state",
    "backend/reading/views.py:319",
    "MergeView.post runs six sequential merge phases, each many writes, with no transaction.atomic. If any phase raises, earlier phases are already committed while later ones never ran, and the client receives a 500 instead of the merged state it was about to write back over localStorage.",
    "A partially-merged account is the worst outcome for the 'nothing a reader did offline is lost' contract: the client may treat the 500 as sync failure while the server already holds a different half of the truth.",
    "In backend/reading/views.py wrap the body of MergeView.post (all six _merge_* calls) in django.db.transaction.atomic() so reconciliation is all-or-nothing, and add a test that a payload failing in a later phase leaves no partial favorites written.")

add("MEDIUM",
    "Read-modify-write race in _upsert_plan_progress can drop completed plan days",
    "backend/reading/views.py:91",
    "_upsert_plan_progress reads the existing row with .first(), unions done in Python, then writes via update_or_create. Two devices PUTting concurrently — the exact scenario the docstring claims to handle — can both read the same old done and the second write clobbers the first's union, losing a completed day.",
    "The module's whole merge contract ('a completion earned on any device is never lost') is violated under concurrency.",
    "In backend/reading/views.py make _upsert_plan_progress atomic: wrap in transaction.atomic() and fetch the existing row with select_for_update() before unioning. Keep the union-of-done / earliest-start semantics and add a comment noting the locking backs the 'never lost' guarantee.")

add("MEDIUM",
    "Negative chapter_order clamps to 0 and is stored instead of rejected",
    "backend/reading/views.py:397",
    "_merge_marks uses order = _clamp_int(row.get('chapter_order'), default=-1, low=0) then skips rows with order < 0. But _clamp_int returns max(low, int(value)), so a parseable -5 becomes 0 — the sentinel only fires for unparseable values. Verified: a chapter_order=-5 payload stores a ChapterMarks row with chapter_order=0, but chapters are 1-based so chapter 0 is a junk row.",
    "The intended validation is dead code for negative numbers; corrupt client data lands as orphan rows that surface in _serialize_state and confuse the client's rehydration.",
    "In backend/reading/views.py _merge_marks replace the clamp with explicit parsing: try order = int(row.get('chapter_order')) and continue unless order >= 1. Add a test asserting a negative chapter_order row is skipped, not stored as order 0.")

add("MEDIUM",
    "Over-long slugs and huge chapter orders cause Postgres DataError 500s",
    "backend/reading/urls.py:19; backend/reading/views.py:255",
    "Favorite.slug and the two book_slug fields are SlugField(max_length=160), but Django's <slug:> converter accepts unbounded length and MergeView takes slugs straight from JSON with no length check; <int:order> accepts values above PositiveIntegerField's limit. On Postgres a 300-char slug PUT raises DataError -> 500 (SQLite dev masks this).",
    "Trivially crafted requests turn into 500s (Sentry noise) instead of clean 400s, and mid-merge they trigger the partial-write problem above.",
    "In backend/reading/views.py truncate or reject over-long identifiers before writing (slice slugs to 160 chars or return 400 when longer) across FavoriteView, ProgressView, MarksView, SermonMarksView and every MergeView _merge_* helper; bound order/chapter_order to a sane maximum. Add a test PUTting a 300-char slug asserting a non-500 response.")

add("MEDIUM",
    "Highlight note length and mark count per chapter are unbounded",
    "backend/reading/marks.py:35",
    "clean_mark_list validates each mark's shape but bounds neither the number of marks per chapter nor the length of note or id. One authenticated PUT can store a multi-megabyte JSON blob in a single ChapterMarks.marks field, and because book_slug is any string, unlimited junk rows can be minted. merge_mark_lists then unions these on every merge and _serialize_state returns them all on every sign-in.",
    "Storage abuse plus a self-inflicted payload bomb: StateView/MergeView responses balloon with the stored data, slowing every sync for that account.",
    "In backend/reading/marks.py clean_mark_list cap the accepted list (e.g. first 500 valid marks), truncate note to ~5000 chars and id to ~64 chars, and document the bounds; apply the same cap after merge_mark_lists in views.py. Add tests for an oversized mark list and an oversized note.")

# ===== C. Backend performance & API design =====
SEC_C = ("C", "Backend performance &amp; API design",
    "Query efficiency and payload consistency on the prerender-time hot paths (author, book, plan, search).")

add("MEDIUM",
    "word_count silently missing from book cards everywhere except the /books shelf",
    "backend/library/serializers.py:123",
    "BookListSerializer.word_count = IntegerField(source='total_words') depends on a total_words annotation. AuthorDetailSerializer._books annotates only num_chapters, so DRF drops the field via SkipField. Verified: author-detail book cards contain chapter_count but no word_count key, while other paths include it — the same serializer emits two different shapes.",
    "Reading-time estimates silently disappear on author pages, and the inconsistent payload is a trap for every future consumer.",
    "In backend/library/serializers.py add total_words=Sum('chapters__word_count') to the annotation in AuthorDetailSerializer._books, and audit every queryset serialized with BookListSerializer for both annotations. Add a test asserting author-detail book cards each contain a word_count key.")

add("MEDIUM",
    "Book topic chips are always empty outside BookListView",
    "backend/library/serializers.py:143",
    "BookListSerializer.get_topics returns self.context.get('book_topics', {}).get(obj.slug, []). That map is built only in BookListView.get_serializer_context, so when the same serializer renders books inside AuthorDetailSerializer, TopicDetailSerializer and BookDetailSerializer.get_related, topics is silently [] for every book.",
    "Author pages, topic pages and 'more like this' cards can never show topic chips — a quiet feature loss the API can't signal (empty list is indistinguishable from 'no topics').",
    "In backend/library/serializers.py make get_topics fall back to a real lookup when book_topics is absent (call the existing _topic_chips helper with the resolved language), or build and thread the book_topics map in AuthorDetailView and TopicDetailView contexts as BookListView does. Add a test that an author-detail response includes topic chips for a book in a published topic.")

add("MEDIUM",
    "AuthorDetailSerializer re-executes the same book/sermon queries up to five times",
    "backend/library/serializers.py:334",
    "_books(obj) returns a fresh queryset each call and is evaluated by get_books (full fetch), get_book_count (.count()) and get_topics (.values_list) — three round-trips over the same filter; _sermons(obj) is called by both get_sermon_count and get_sermons, and get_topics re-queries the author's sermons a third way.",
    "The author page — a prerender-time hot path across every locale — pays ~6 queries where 2 would do, multiplied by authors x languages on each build.",
    "In backend/library/serializers.py AuthorDetailSerializer memoize per instance: cache list(self._books(obj)) and self._sermons(obj), derive the counts via len(), and derive the slug sets in get_topics from the cached lists. Add an assertNumQueries test for the author-detail endpoint.")

add("MEDIUM",
    "BookDetailView loads every chapter's full body just to render a TOC",
    "backend/library/views.py:181",
    "BookDetailView.get_object does .prefetch_related('chapters', ...), loading complete Chapter rows — body_html, body_text and the search_vector tsvector — for every chapter, when the serializer needs only order/title/word_count for the TOC and the first five chapters' body_text for get_difficulty.",
    "For a long book (Confessions, Pilgrim's Progress) this drags megabytes from Postgres into memory per book-page request and per prerender, for data that is thrown away.",
    "In backend/library/views.py replace the bare chapters prefetch with Prefetch('chapters', queryset=Chapter.objects.defer('body_html','search_vector')), keeping body_text for get_difficulty (or defer it too and have get_difficulty run its own .only('body_text') query over the first five chapters). Verify the book-detail test still passes.")

add("MEDIUM",
    "SearchView performs an unthrottled anonymous DB write on every request",
    "backend/library/views.py:476",
    "Every unscoped search creates a SearchQueryLog row with no throttle on SearchView (only SearchClickView is throttled). It is one row per request, per keystroke, capped only by a 180-day trim, and every zero-result query additionally runs the full-vocabulary difflib suggest scan.",
    "Anyone can script millions of ?q= requests to grow the table and skew the popular-searches analytics that drive content decisions, at zero cost.",
    "In backend/library/views.py add a throttle to SearchView analogous to _SearchClickThrottle (a UserRateThrottle subclass with its own generous scope, e.g. 120/min for search-as-you-type, registered in settings), or at minimum bound the logging behind a per-IP token bucket. Preserve fail-open behaviour and add a test that the limit is enforced for anonymous callers.")

add("LOW",
    "Scripture-reference searches fetch every sermon's full body into Python",
    "backend/library/search.py:719",
    "_scripture_sermon_hits iterates full sermon instances (including body_html and body_text) for every published sermon in the language and calls reference_verse_ids per row, even though only the winners' body_text is used — while the neighbouring _scripture_chapter_hits explicitly avoids exactly this ('measured 40 MB').",
    "Every query that parses as a scripture reference ('John 3:16') loads the whole sermon corpus' bodies, per keystroke once digits appear.",
    "In backend/library/search.py _scripture_sermon_hits first iterate .values('slug','scripture_ref') to pick winning slugs by verse-id overlap, then fetch only the winners with .defer('body_html','search_vector'), mirroring _scripture_chapter_hits' two-phase pattern. Keep dedupe and the sermon cap identical.")

add("LOW",
    "No DRF pagination configured; all list endpoints return unbounded result sets",
    "backend/config/settings.py:133; backend/library/views.py:343",
    "REST_FRAMEWORK sets no DEFAULT_PAGINATION_CLASS, so author/book/sermon/plan list views return every row in one response. TopicListView even sets pagination_class = None explicitly, a no-op given the default is already None — evidence the codebase believes pagination exists somewhere.",
    "As the sermon/book count grows into the hundreds per language, shelf payloads and query time grow linearly with no pressure valve, and the meaningless pagination_class = None misleads future readers.",
    "In backend/config/settings.py either add a generous DEFAULT_PAGINATION_CLASS/PAGE_SIZE (LimitOffsetPagination with a high default limit so static-build consumers are unaffected) or, if unpaginated lists are a deliberate prerender contract, document that in a comment on REST_FRAMEWORK and delete the dead pagination_class = None from TopicListView.")

# ===== D. Content & translation pipeline =====
SEC_D = ("D", "Content &amp; translation pipeline",
    "The seed/upsert and AI-translation machinery, and the invariant that unreviewed text is never presented as approved.")

add("CRITICAL",
    "Translating new chapters into an approved book silently keeps it 'reviewed'",
    "backend/library/management/commands/translate_book.py:86",
    "The book row's source_type is only written inside if target is None or force. If a translation was approved (ai_reviewed) and the English source later gains chapters (or --chapters targets a missing order), the chapter loop inserts brand-new machine-translated chapters into the approved book without touching source_type. The same hole exists in contemporize_book.",
    "Unreviewed AI text is presented to readers without the 'awaiting native review' badge — a direct violation of the never-present-unreviewed-as-approved invariant.",
    "In translate_book.py and contemporize_book.py, after the chapter loop, if any chapter was created or updated and the target's source_type is AI_REVIEWED, flip it back to AI_UNREVIEWED and save (printing that re-review is required). Add a regression test: an approved target, one new chapter via a mocked client, assert the book is ai_unreviewed afterwards.")

add("HIGH",
    "seed_plans is not atomic and never repairs a plan created without its days",
    "backend/library/management/commands/seed_plans.py:277",
    "handle() has no transaction.atomic, and Plan.objects.create(...) is followed by a separate PlanDay.objects.bulk_create(...). A crash between the two leaves a day-less plan; on every later deploy _reconcile_existing returns True for any existing (slug, language) row without checking it has days, so creation is skipped forever.",
    "A single mid-seed failure produces a permanently empty reading plan visible to readers, and re-running the 'idempotent' command can never fix it.",
    "In backend/library/management/commands/seed_plans.py wrap each plan's create+bulk_create in one atomic block, and make _reconcile_existing treat a plan with zero PlanDays as 'not existing' (backfill or delete-and-recreate its days). Add a test that a Plan with no days is repaired by seed_plans.")

add("HIGH",
    "Re-importing a book re-asserts is_published / source_type, republishing pulled works",
    "backend/library/management/commands/import_ochorus.py:535",
    "upsert() puts is_published: bool(chapters) and source_type: PUBLIC_DOMAIN in the defaults of update_or_create, so any re-import overwrites them. EXCLUDED_SLUGS only guards catalogue-wide imports; an explicit import_ochorus <slug> (allowed per the docstring) recreates and republishes a book that the copyright audit had unpublished.",
    "One command invocation re-publishes non-public-domain content, and a later fixture serialization would ship is_published: true to every fresh install.",
    "In import_ochorus.py upsert() (and ingest.upsert_book) move is_published and source_type out of the update defaults into create_defaults so re-imports never republish or re-type an existing row; make import_ochorus refuse slugs in corrections.EXCLUDED_SLUGS unless an explicit --include-excluded flag is passed. Add a test that re-importing an unpublished book leaves is_published False.")

add("HIGH",
    "Translation approvals live only in the prod DB and are lost on a fresh-DB rebuild",
    "backend/library/management/commands/approve_translation.py:29",
    "approve_translation / approve_sermon_translation / the admin approve endpoint flip source_type on the live row only; the fixture still says ai_unreviewed (seed_books' own comment notes '37 fixture books still say ai_unreviewed'), and regen_fixture.py regenerates the fixture from the fixture, never from a DB, so the flip can never round-trip into the committed files.",
    "Any fresh install or disaster-recovery rebuild silently re-gates every approved translation back to 'awaiting native review', losing months of review decisions.",
    "Make approvals durable in the repo: have approve_translation (and the sermon/admin variants) also apply the source_type edit to the book's fixture file, or add a small committed approvals list that a release step re-applies after seed_if_empty. Add a test that a fresh loaddata + release preserves a recorded approval.")

add("HIGH",
    "fetch_chapter permanently negative-caches transient failures, dropping scripture",
    "backend/library/translation.py:107",
    "On any RequestException or non-OK response, _verse_cache[key] = None is stored and never retried for the life of the process. scripture_context fails open by skipping None passages, so after one network blip mid-translate_book every later chapter citing that passage is translated with no authoritative verse text — despite verify_bible_code passing at job start.",
    "The exact failure the module's docstring calls the worst case (model-invented scripture wording, at full cost, looking entirely normal) can happen from a single transient timeout in a long paid job.",
    "In backend/library/translation.py fetch_chapter distinguish a definitive miss (HTTP 404) from a transient failure: cache only 404s, and retry transient failures with small backoff, raising after repeated failure so the job stops rather than shipping scripture-less chapters. Add a test with a mocked requests.get that fails once then succeeds, asserting the retry.")

add("MEDIUM",
    "Integrity audit keys chapters by slug only, merging all language editions",
    "backend/library/admin_views/quality.py:177",
    "_scan_chapters builds titles and orders dicts keyed by book__slug, but a slug has one row per language. _order_gaps takes set(orders) across all editions, so a Spanish edition missing chapter 3 is invisible whenever the English edition has one; _duplicate_titles counts a title repeated across two language editions as a duplicate within one book.",
    "The audit can never detect a chapter gap in a partially-translated book (the most likely place for one) and reports false duplicate-title findings that erode trust in the report.",
    "In backend/library/admin_views/quality.py _scan_chapters key the accumulators by (slug, language) and carry language through the _duplicate_titles / _order_gaps output rows. Add tests: an es edition missing an order the en edition has is reported; en and es sharing a title string is not a duplicate.")

add("MEDIUM",
    "Admin publish accepts any language string and stamps non-English uploads public_domain",
    "backend/library/admin_import_views.py:107",
    "AdminImportPublishView takes language from the payload with no validation against languages.known_codes() (the jobs endpoint validates) and no normalization, and create_book/create_sermon hard-code source_type=PUBLIC_DOMAIN regardless of language.",
    "A typo ('Sw', 'es ') strands content in a language no reader can reach, and a human- or third-party-translated upload is labelled a public-domain original with no review pathway.",
    "In backend/library/admin_import_views.py AdminImportPublishView.post lowercase/strip language and reject codes not in library.languages.known_codes() with a 400; consider accepting an optional source_type restricted to Book.SourceType. Add tests for an unknown code and a mixed-case code.")

add("MEDIUM",
    "TopicTranslation has no review state despite the pipeline's review-flow promise",
    "backend/library/models.py:587",
    "seed_topics' comments say topic prose is 'AI-drafted, pending native review (the same review flow as book translations)', but TopicTranslation has no reviewed/source_type field, no badge, and no approve command; the seed's update_or_create re-asserts the code dict over any DB edit every deploy.",
    "AI-drafted shelf prose is presented indistinguishably from reviewed text — the one content type that escapes the ai_unreviewed -> approval invariant — and a native reviewer has no way to record or protect an approval.",
    "Add a reviewed BooleanField (default False) to TopicTranslation with a migration; make seed_topics skip overwriting rows with reviewed=True (mirroring seed_author_translations' ownership rule), add an approve path (extend the review queue and/or an approve_topic_translation command), and surface unreviewed topics in the queue. Pin with tests.")

add("MEDIUM",
    "apply_body_corrections runs before the content seeds, so new rows ship uncorrected",
    "backend/library/management/commands/release.py:32",
    "The release chain runs apply_body_corrections before seed_books/seed_sermons. A work first created by this deploy's seed (a new fixture whose text still carries a defect in BODY_CORRECTIONS) is created after the correction pass and ships uncorrected until the next deploy.",
    "Prod serves known-defective text — the exact strings the corrections table exists to fix — for one deploy window on every new-work release, with nothing reporting it.",
    "In backend/library/management/commands/release.py move apply_body_corrections to run after seed_books and seed_sermons (it is idempotent), or run it a second time after the seeds. Add a release-ordering test that seeds a new fixture book containing a correctable string and asserts the stored chapter is corrected within the same run.")

# ===== E. Frontend sync, offline & PWA =====
SEC_E = ("E", "Frontend sync, offline &amp; PWA",
    "The localStorage-first stores, the sign-in merge, the service worker, and the shared-device data boundary.")

add("HIGH",
    "Service worker can permanently cache authenticated /api/ responses (cross-user leak)",
    "frontend/src/service-worker.ts:100",
    "The fetch handler routes every same-origin GET that isn't a navigation, library API, or image to cacheFirst, which caches any ok response forever within a deploy and never revalidates. config.ts documents API_BASE_URL='' (same origin) as the production mode; under that config /api/auth/me/ is cached on first fetch, and the cache key ignores the Authorization header.",
    "Profile pulls go permanently stale within a deploy, and on a shared browser a second user is served the previous user's cached /api/auth/me/ response. It only doesn't bite today because render.yaml happens to set a cross-origin API URL, contradicting config.ts's own comment.",
    "In frontend/src/service-worker.ts add an early bail for any pathname starting with /api/ that isn't matched by isLibraryApi, so authenticated endpoints go straight to the network and are never cached. Reconcile the config.ts comment with render.yaml's cross-origin PUBLIC_API_BASE_URL.")

add("HIGH",
    "Session-expiry sign-out skips the shared-device data wipe",
    "frontend/src/lib/auth.svelte.ts:66",
    "clearOnSignOut() runs only inside the explicit signOut() method. When Supabase fires SIGNED_OUT through onAuthStateChange for any other reason (refresh token expired/revoked, signed out in another tab, password changed elsewhere), #applySession(null) clears the token and user but leaves all reading data in localStorage.",
    "This defeats the exact scenario the wipe exists for: on a shared device, user A's expired session leaves their highlights/notes/progress behind, and user B's next sign-in merge uploads A's private reading data into B's account permanently.",
    "In frontend/src/lib/auth.svelte.ts, in the onAuthStateChange callback detect the signed-in -> signed-out transition (wasSignedIn && !session) and call readingSync.clearOnSignOut() plus reset displayName/isAdmin, mirroring signOut(). Keep the removal idempotent so the explicit signOut() path doesn't double-wipe.")

add("HIGH",
    "Bookmarks are wiped on sign-out but never synced — guaranteed data loss",
    "frontend/src/lib/bookmarks.svelte.ts:4; frontend/src/lib/reading-schema.ts:39",
    "BOOKMARKS_KEY is in READING_DATA_KEYS, so clearDeviceData() deletes it on sign-out, but readingSync has no pushBookmarks, the merge payload omits bookmarks, and the server state never restores them. Marks/progress/favorites all round-trip through the account; bookmarks are the only store wiped without a server copy.",
    "A signed-in reader who signs out permanently loses every explicit bookmark with no warning; the settings copy ('the next sync restores from the account') is false for this data class.",
    "Either add bookmarks to the sync layer (a debounced pushBookmarks PUT, bookmarks in the merge payload and response, plus the matching Django endpoint/model), or as a stopgap remove BOOKMARKS_KEY from READING_DATA_KEYS so sign-out stops destroying the only copy, noting the shared-device tradeoff in the comment.")

add("MEDIUM",
    "Merge response clobbers local mutations made while the request is in flight",
    "frontend/src/lib/readingSync.ts:267",
    "mergeOnSignIn() snapshots localStorage, POSTs it, and on response #writeState unconditionally overwrites progress/marks/favorites/activity/plans with the server's answer. It runs on every full page load for a signed-in user, so a highlight, favorite, or chapter-open recorded between snapshot and response is erased locally when the response lands. There is also no guard against two concurrent merges interleaving.",
    "The reader sees their just-made highlight or 'continue reading' position visibly revert; the debounced push may still deliver it, leaving local and server silently divergent.",
    "In frontend/src/lib/readingSync.ts add an in-flight guard (a shared promise) and, instead of blind overwrite, re-merge the response with current localStorage (newest-at wins for progress; union marks/favorites/activity/plan days), or detect that localStorage changed since the snapshot and re-run the merge.")

add("MEDIUM",
    "Highlights are keyed without language, corrupting every translation of a work",
    "frontend/src/lib/reading-schema.ts:82",
    "workKey(kind, slug, order) omits language, so marks made in the English edition are loaded verbatim when the reader opens the Spanish or en-modern edition of the same chapter — but marks are character offsets into paragraph text that differ per translation. The merge payload rows also omit language even though pushMarks sends it.",
    "Readers of any translated or modernized edition see highlights attached to the wrong spans (or mid-word), and the server's language column is unreliable after a merge.",
    "In frontend/src/lib/reading-schema.ts extend workKey/parseWorkKey with a language component for non-'en' entries (keeping bare keys for existing 'en' data), thread language through marks.svelte.ts load/persist, and include language in the mergeOnSignIn marks rows to match pushMarks. Coordinate with the Django merge endpoint's identity columns.")

add("MEDIUM",
    "apiFetch has no timeout or retry; every sync push is fire-and-forget with silent drop",
    "frontend/src/lib/api.ts:28; frontend/src/lib/readingSync.ts:136",
    "apiFetch calls bare fetch with no AbortController/timeout, so a hung connection leaves promises pending indefinitely — including auth.init's awaited profile/merge chain. All readingSync push* calls end in .catch(() => {}): a failed push is dropped with no retry and no dirty flag.",
    "In a long-lived PWA session (the app's core offline audience), hours of highlights and progress can silently fail to mirror, and users on flaky networks get UI that waits forever.",
    "In frontend/src/lib/api.ts wrap apiFetch/apiFetchRaw with an AbortController timeout (~15s, overridable). In readingSync.ts, on push failure set a persisted dirty flag and re-run the push (or a full merge) when the 'online' event fires (pwa.svelte.ts already tracks connectivity) instead of swallowing the error.")

add("MEDIUM",
    "A book with failed chapter downloads is still recorded as fully available offline",
    "frontend/src/lib/offlineBooks.svelte.ts:82",
    "In download(), each chapter fetch failure is swallowed by the inner try/catch or the res.ok check, the progress counter still advances, and after the loop the book is unconditionally appended to the downloaded list with chapterCount: orders.length. Nothing tracks how many URLs actually made it into the cache.",
    "The UI tells the reader 'this book is available offline' when arbitrary chapters are missing; they discover it on a plane when a chapter 404s into the SPA error page.",
    "In frontend/src/lib/offlineBooks.svelte.ts download() count successful cache.put calls; if any chapter or the book detail failed, either return false without recording the book (and surface a retry) or record the real cached count and show a partial/retry state. At minimum, don't push the metadata entry when successCount < urls.length.")

add("MEDIUM",
    "Auto-applied PWA update reloads the page mid-input on most routes",
    "frontend/src/lib/pwa.svelte.ts:104",
    "#applyWhenSafe treats only /books/[slug]/[order] and /sermons/[slug] as unsafe; on every other route a waiting worker triggers SKIP_WAITING and an immediate location.reload(). That includes the settings page mid-display-name-edit, the search page with a typed query, an admin form, or the notebook.",
    "A deploy landing while a reader is typing silently reloads the tab and destroys their input; 'not mid-chapter' is far narrower than 'safe to reload'.",
    "In frontend/src/lib/pwa.svelte.ts broaden the safety check: skip the reload when any input/textarea/contenteditable is focused or dirty (document.activeElement), and add settings/admin/search to the unsafe set (or invert to an allowlist of passive routes). Migrate the page import from $app/stores to $app/state while there.")

# ===== F. Frontend UX, accessibility & SEO =====
SEC_F = ("F", "Frontend UX, accessibility &amp; SEO",
    "Error states, focus management, RTL correctness, and the per-locale SEO story on the public reading surfaces.")

add("HIGH",
    "Library search has no error state — API failure shows stale results plus an unhandled rejection",
    "frontend/src/routes/search/+page.svelte:569",
    "runSearch is try { ... } finally { loading = false } with no catch, invoked fire-and-forget from the debounce timer. When the API call rejects, the rejection is unhandled, loading flips off, and the page keeps rendering the previous query's hits and counts under the new query text with no message.",
    "A reader on a flaky connection types a query, the spinner disappears, and they see results for a different search presented as the answer — a silent lie — plus console noise.",
    "In frontend/src/routes/search/+page.svelte add a catch to runSearch that (when the token is current) clears hits/counts and sets a searchError state, and render an error panel with a retry button, following the loadError pattern BooksShelf.svelte already uses. Add the new message key to all catalogues and run npm run sync:catalogues.")

add("HIGH",
    "In-book search drawer is aria-modal but has no focus trap",
    "frontend/src/lib/components/SearchDrawer.svelte:132",
    "The panel is role='dialog' aria-modal='true' but nothing constrains Tab — unlike its sibling TocDrawer and CommandPalette, which use a focus trap. Focus moves into the input on open but Tab then walks out of the drawer into the page content hidden behind the scrim.",
    "Screen-reader and keyboard users are told the rest of the page is inert while it is actually reachable, breaking the modal contract and letting keyboard users escape into invisible content.",
    "In frontend/src/lib/components/SearchDrawer.svelte apply the existing focusTrap action to the .search-panel (as CommandPalette.svelte does), passing { onEscape: close }, and remove the now-redundant manual Escape handling. Verify Tab/Shift-Tab cycle within the panel and focus returns to the opener on close.")

add("MEDIUM",
    "Unknown topic and plan slugs render a generic error instead of the designed 404",
    "frontend/src/routes/topics/[slug]/+page.ts:22; frontend/src/routes/plans/[slug]/+page.ts:22",
    "Both loads call the API directly without the orNotFound helper that books, chapters, sermons and authors all use to translate an ApiError 404 into SvelteKit's error(404). A mistyped or unpublished slug surfaces as a generic 'something went wrong, try again' page instead of the not-found page with daily picks.",
    "Readers hitting a stale topic/plan link get a useless retry for a page that will never exist, and the 404-only picks section never renders; 404 semantics are inconsistent across otherwise-identical detail routes.",
    "In topics/[slug]/+page.ts and plans/[slug]/+page.ts wrap the fetch in the existing helper: import { orNotFound } from '$lib/loadHelpers' and return await orNotFound(() => getTopic(params.slug, getLang())) (same for getPlan), matching books/[slug]/+page.ts.")

add("MEDIUM",
    "feed.xml prerender crashes on any work with a missing created_at",
    "frontend/src/routes/feed.xml/+server.ts:38",
    "The sort explicitly anticipates undated rows ('API deploy race: keep them, sort undated last'), but entryXml then does new Date(it.date).toISOString(). For an undefined or '' date that is an Invalid Date and .toISOString() throws a RangeError, so the very rows the guard keeps crash the feed's prerender and fail the whole static build.",
    "One backend deploy that briefly serves works without created_at turns a cosmetic data gap into a hard web-build failure — the exact race the comment says the file is designed to survive.",
    "In frontend/src/routes/feed.xml/+server.ts make entryXml tolerate a bad date: const d = new Date(it.date); const updated = isNaN(d.getTime()) ? new Date(0).toISOString() : d.toISOString(); and apply the same guard to the feed-level updated. Align the comment with whichever behaviour you pick.")

add("MEDIUM",
    "Physical CSS in scoped styles breaks RTL (Arabic) reading surfaces",
    "frontend/src/routes/notebook/+page.svelte:310; sermons/[slug]/+page.svelte:503; authors/[slug]/+page.svelte:444",
    "rtl.test.ts only scans for physical Tailwind classes, so scoped <style> blocks slip through: notebook highlight cards mix logical border-s-2 with a physical border-left-color (the colour edge vanishes in RTL); .text-card, .author-quote and bio blockquotes draw their rule on the wrong side of Arabic prose; sermon outline items use text-align:left and the progress bar grows from the wrong end.",
    "Arabic is a routed, advertised RTL locale; these details make the reading surfaces look subtly broken there while staying invisible to every LTR locale and to the existing test.",
    "Across frontend/src convert physical properties in reader-facing scoped styles to logical ones (border-left -> border-inline-start, padding-left -> padding-inline-start, text-align:left -> start, transform-origin fixes for RTL), starting with notebook, sermons and authors pages, and extend rtl.test.ts to also grep <style> blocks for border-left|border-right|text-align:\\s*(left|right)|padding-(left|right).")

add("MEDIUM",
    "Hardcoded English meta-description fallbacks on localized book and sermon pages",
    "frontend/src/routes/books/[slug]/+page.svelte:57; sermons/[slug]/+page.svelte:136",
    "The book page falls back to `${title} by ${author} — free to read on Ochorus.` and the sermon page to a similar English literal. These pages prerender per locale (ar/es/sw/lg/pt/uk), so a Swahili work without a description ships an English meta and og:description at its /sw URL. The author page already solved this with a localized t('author.metaFallback').",
    "Search snippets and social cards for localized pages appear in the wrong language, which looks broken to readers and undercuts the carefully-built hreflang story.",
    "Add localized fallback messages (book_metaFallback, sermon_metaFallback) to all eight catalogues, run npm run sync:catalogues, and use them with %title%/%name% interpolation in books/[slug]/+page.svelte and sermons/[slug]/+page.svelte, following the author.metaFallback pattern.")

# ===== G. Engineering infrastructure & DX =====
SEC_G = ("G", "Engineering infrastructure &amp; developer experience",
    "The CI gate, build reproducibility, and test coverage that a fast-moving multi-session repo depends on.")

add("HIGH",
    "The auth boundary (SupabaseJWTAuthentication) has zero tests",
    "backend/accounts/authentication.py:27",
    "The 120-line SupabaseJWTAuthentication class — JWKS fetch, JWT decode, the documented 'bad token resolves to anonymous, never a 500' contract, and _get_or_create_user — has no test anywhere; accounts/tests.py covers only Me/OriginUrl/IsAdminUser.",
    "This is the security boundary for every authenticated and admin endpoint; a regression (an expired-token path that raises instead of resolving to anonymous, or a user-creation bug) ships silently since CI proves nothing about it.",
    "Add backend/accounts/tests_authentication.py covering SupabaseJWTAuthentication: a valid RS256 token (mock the JWKS client with a locally generated keypair) authenticates and creates/reuses the user; expired, malformed, wrong-audience and absent tokens resolve to anonymous without raising. Use unittest.mock.patch so no network is touched.")

add("HIGH",
    "No Python linter or formatter exists or runs in CI",
    "backend/pyproject.toml:27; .github/workflows/ci.yml",
    "The backend has no ruff/flake8/black/mypy configuration anywhere, and ci.yml runs only manage.py test and the migration check — no static-analysis gate at all on Python code.",
    "With many parallel AI sessions squash-merging to main fast, unused imports, dead code, shadowed names and style drift accumulate unchecked — exactly the failure mode a fast multi-agent repo needs a linter to catch cheaply.",
    "Add ruff to the backend: put ruff in the dev dependency group in pyproject.toml, add a [tool.ruff] section (target py312, select E,F,I,B,DJ), fix or ignore existing violations file-by-file, then add a 'Backend — lint (ruff)' step to ci.yml right after uv sync --frozen. Mirror with ESLint+Prettier on the frontend.")

add("MEDIUM",
    "No browser E2E or smoke test; SPA runtime paths are never executed in CI",
    "frontend/package.json:14",
    "There is no Playwright/Cypress anywhere; the only integration coverage is the CI prerender build fetching the seeded API, which exercises public GET endpoints at build time but nothing in a browser — hydration, the reader, client-side routing, auth, offline/PWA, or any authenticated endpoint contract (library-admin.ts is never checked against the real API).",
    "Frontend and backend can drift on any authenticated or mutating endpoint (rename a DRF field, change a payload shape) with all of CI green; the bug surfaces only when a user or the admin hits it in production.",
    "Add Playwright with a small smoke suite run in CI after the build: serve build/ honoring the 200.html fallback, then assert the home page hydrates, a book page renders chapter HTML, client navigation to a chapter works, and search returns results against the locally seeded API. Reuse the backend already running on port 8000.")

add("MEDIUM",
    "The API container runs as root and has no .dockerignore",
    "backend/Dockerfile:19",
    "The Dockerfile never switches to a non-root user, so gunicorn and the preDeploy manage.py release run as root. There is also no backend/.dockerignore, so COPY . . ingests __pycache__, any local .env, sqlite files and .venv when built locally.",
    "Root-in-container needlessly widens the blast radius of any Django/dependency RCE, and a locally built image can leak a developer's .env secrets into image layers.",
    "In backend/Dockerfile add a non-root user after the final uv sync (useradd app; chown -R app /app; USER app), verifying collectstatic output stays readable, and add backend/.dockerignore with .venv, __pycache__/, *.pyc, .env*, *.sqlite3. Confirm manage.py release still works as the non-root user on a Render preview.")

add("MEDIUM",
    "Same-commit deploy race lets the web build prerender stale API content",
    "render.yaml:79; frontend/svelte.config.js:52",
    "A push touching backend/library/fixtures/** auto-deploys the API and, via buildFilter, rebuilds the web service concurrently. The web build's prerender and fetch-live-locales.mjs hit the production API, which may still be serving the previous version while the API's Docker build runs — so the static site can bake old content (svelte.config.js already excuses routes that 'lag a simultaneous deploy').",
    "The rebuild that exists specifically to freshen prerendered content can silently ship the stale content it was meant to replace, with no signal; the next unrelated deploy quietly fixes it.",
    "Make the web build verify its content version: expose an API content fingerprint (e.g. /api/health/ returning the release git SHA) and add a prebuild check comparing it to the building commit, failing with 'API still serving previous release — retry the deploy' on mismatch. Alternatively replace the buildFilter trigger with an explicit web deploy-hook call at the end of manage.py release.")

add("MEDIUM",
    "The content fixture is ~75 MB and grows with whole-file rewrites per edit",
    "backend/library/fixtures/content/",
    "fixtures/content/ is ~75 MB across 234 JSON files (largest 7.2 MB, ten over 1 MB); the git pack is already ~46 MB. Every translation or english-qa fix rewrites an entire multi-MB JSON file, the roadmap (8 locales x 65+ books plus contemporized editions) multiplies this, and each fixture commit triggers a full frontend prerender rebuild.",
    "Clone/checkout/CI time and repo size grow superlinearly with content velocity (dozens of commits per month), and GitHub becomes slow and hostile to review well before hard limits hit.",
    "Produce a design note projecting fixture growth and CI-time, then evaluate (a) a one-file-per-chapter diff-friendly layout so edits touch kilobytes not megabytes, (b) Git LFS, or (c) object-store-backed content with only metadata in git. Constraints: manage.py release must still seed from files in the Docker build context, and content_fixtures.py + tests_fixture + regen_fixture.py define the current contract.")

# ---- build ---------------------------------------------------------------
SECTIONS = [SEC_A, SEC_B, SEC_C, SEC_D, SEC_E, SEC_F, SEC_G]
# map findings to sections by count
SECTION_COUNTS = [7, 7, 7, 9, 8, 6, 6]  # = 50
assert sum(SECTION_COUNTS) == len(F), (sum(SECTION_COUNTS), len(F))

# assign numbers
for i, f in enumerate(F, 1):
    f["num"] = i

def sev_chip(sev):
    return Table(
        [[Paragraph(f'<font color="{hx(SEV[sev])}"><b>{sev}</b></font>', st_cap)]],
        colWidths=[26*mm],
        style=TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), SEV_BG[sev]),
            ("BOX", (0,0), (-1,-1), 0.5, SEV[sev]),
            ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
            ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ]))

story = []

# ----- cover -----
story.append(Spacer(1, 46*mm))
story.append(Paragraph(f'<font color="{hx(BRAND)}"><b>Ochorus</b></font>',
                       mk("cover1", fontName="Helvetica-Bold", fontSize=34, leading=38, textColor=BRAND, alignment=TA_LEFT)))
story.append(Spacer(1, 4*mm))
story.append(Paragraph("Web App Code Review", mk("cover2", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=INK)))
story.append(Spacer(1, 3*mm))
story.append(Paragraph("50 issues, bugs, and improvements &mdash; with a fix prompt for each",
                       mk("cover3", fontName="Helvetica", fontSize=12, leading=16, textColor=MUTED)))
story.append(Spacer(1, 10*mm))
story.append(HRFlowable(width="38%", thickness=2, color=BRAND, spaceAfter=8, hAlign="LEFT"))
story.append(Paragraph("Django REST API &nbsp;&bull;&nbsp; SvelteKit static SPA &nbsp;&bull;&nbsp; multilingual reader",
                       mk("cover4", fontName="Helvetica", fontSize=9.5, leading=14, textColor=FAINT)))
story.append(Paragraph("Reviewed 7 August 2026", mk("cover5", fontName="Helvetica", fontSize=9.5, leading=14, textColor=FAINT)))
story.append(PageBreak())

# ----- how to read / summary -----
story.append(Paragraph("How this review was made", st_sect))
story.append(HRFlowable(width="100%", thickness=1, color=RULE, spaceAfter=8))
story.append(Paragraph(
    "Six independent review passes read the codebase in depth &mdash; the Django API, the content and translation "
    "pipeline, the frontend sync/offline libraries, the routes and components, a focused security audit across both "
    "stacks, and the CI/build/test infrastructure. Their ~98 raw findings were de-duplicated and curated down to the "
    "50 below. Several were reproduced against a live test database (noted in place). Each finding states <b>what</b> "
    "it is, <b>why</b> it should be fixed, and a self-contained <b>fix prompt</b> you can paste into Claude Code.",
    st_intro))
story.append(Spacer(1, 3*mm))

# severity tally
tally = {"CRITICAL":0,"HIGH":0,"MEDIUM":0,"LOW":0}
for f in F:
    tally[f["sev"]] += 1
trow = [[Paragraph(f'<b>{k}</b>', st_cap), Paragraph(str(v), mk("n",fontName="Helvetica-Bold",fontSize=13,textColor=SEV[k]))]
        for k,v in tally.items()]
tt = Table([[c for pair in trow for c in pair]], colWidths=[24*mm,10*mm]*4)
tt.setStyle(TableStyle([
    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
    ("LINEBELOW",(0,0),(-1,-1),0,PAPER),
]))
story.append(Paragraph("Severity mix", st_label))
story.append(tt)
story.append(Spacer(1, 4*mm))

# section index
story.append(Paragraph("Sections", st_label))
idx_rows = []
start = 1
for (code, name, _desc), cnt in zip(SECTIONS, SECTION_COUNTS, strict=True):
    rng = f"{start}–{start+cnt-1}"
    start += cnt
    idx_rows.append([Paragraph(f'<b>{code}</b>', st_body),
                     Paragraph(name, st_body),
                     Paragraph(f'<font color="{hx(FAINT)}">#{rng}</font>', st_body)])
it = Table(idx_rows, colWidths=[10*mm, 128*mm, 20*mm])
it.setStyle(TableStyle([
    ("VALIGN",(0,0),(-1,-1),"TOP"),
    ("LINEBELOW",(0,0),(-1,-2),0.4,RULE),
    ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
]))
story.append(it)
story.append(PageBreak())

# ----- findings -----
def finding_flow(f):
    parts = []
    # header row: number + title + sev chip
    hdr = Table(
        [[Paragraph(f'<font color="{hx(BRAND)}"><b>{f["num"]:02d}</b></font>', mk("num",fontName="Helvetica-Bold",fontSize=13,textColor=BRAND)),
          Paragraph(esc(f["title"]), st_ftitle),
          sev_chip(f["sev"])]],
        colWidths=[11*mm, 121*mm, 27*mm])
    hdr.setStyle(TableStyle([
        ("VALIGN",(0,0),(1,0),"TOP"),("VALIGN",(2,0),(2,0),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),1),
    ]))
    parts.append(hdr)
    parts.append(Paragraph(esc(f["files"]), st_file))
    parts.append(Spacer(1, 2))
    parts.append(Paragraph("WHAT", st_label))
    parts.append(Paragraph(esc(f["what"]), st_what))
    parts.append(Paragraph("WHY IT MATTERS", st_label))
    parts.append(Paragraph(esc(f["why"]), st_why))
    parts.append(Paragraph("FIX PROMPT", st_label))
    fixtbl = Table([[Paragraph(esc(f["fix"]), st_fix)]], colWidths=[159*mm])
    fixtbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),CODEBG),
        ("BOX",(0,0),(-1,-1),0.5,RULE),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LINEBEFORE",(0,0),(0,-1),2,BRAND),
    ]))
    parts.append(fixtbl)
    parts.append(Spacer(1, 5*mm))
    return KeepTogether(parts)

idx = 0
for (code, name, desc), cnt in zip(SECTIONS, SECTION_COUNTS, strict=True):
    # section header
    sh = [Paragraph(f'{code}. {name}', st_sect),
          Paragraph(desc, st_sectd),
          HRFlowable(width="100%", thickness=1.4, color=BRAND, spaceAfter=8)]
    story.append(KeepTogether(sh))
    for _ in range(cnt):
        story.append(finding_flow(F[idx]))
        idx += 1
    story.append(PageBreak())

# ----- prioritization -----
story.append(Paragraph("Recommended order of work", st_sect))
story.append(HRFlowable(width="100%", thickness=1, color=RULE, spaceAfter=8))
story.append(Paragraph(
    "Fifty items is a backlog, not a sprint. The order below is by <b>reader-facing risk per unit of effort</b>: "
    "correctness and data-safety bugs that silently harm real readers or violate the app's own promises come first; "
    "the deep-but-large refactors come last. Numbers in brackets reference the findings above.",
    st_intro))

def wave(title, subtitle, items):
    flow = [Paragraph(title, st_h2), Paragraph(subtitle, st_sectd)]
    li = []
    for head, body in items:
        li.append(ListItem(Paragraph(f'<b>{esc(head)}</b> &mdash; {esc(body)}', st_body), leftIndent=6))
    flow.append(ListFlowable(li, bulletType="bullet", start="square", leftIndent=12,
                             bulletColor=BRAND, bulletFontSize=6))
    flow.append(Spacer(1, 3*mm))
    return KeepTogether(flow)

story.append(wave(
    "Wave 1 &mdash; Stop the silent harm (this week)",
    "Small, high-certainty fixes that either leak data, mislead readers, or break an invariant the app advertises. "
    "Most are a few lines plus a test.",
    [
     ("Admin unverified-email takeover [01]", "the one true security hole; require an email_verified claim before any admin decision. Ship first."),
     ("Service worker caches authenticated /api/ [34] and session-expiry skips the wipe [35]", "together these leak one reader's private data to the next person on a shared device; fix both before anything else user-facing."),
     ("Bookmarks wiped but never synced [36]", "guaranteed silent data loss on every sign-out; the one-line stopgap (drop BOOKMARKS_KEY from the wipe list) buys time for the real sync."),
     ("New chapters keep an approved book 'reviewed' [24]", "unreviewed AI scripture shown as native-approved; flip source_type back on any chapter write."),
     ("Merge 500s on malformed JSON [08]", "one bad field aborts a reader's whole first-sign-in reconciliation; add the missing type guards."),
     ("Search shows stale results on API error [42]", "a silent wrong answer on the core feature; add the missing catch and error panel."),
    ]))

story.append(wave(
    "Wave 2 &mdash; Data integrity &amp; abuse resistance (next 2&ndash;3 weeks)",
    "Bugs that corrupt stored data under concurrency or let a single request amplify into unbounded work. Each needs a "
    "little more care and a concurrency/limit test.",
    [
     ("Throttle + cap the reading merge [09]", "no /api/reading/ endpoint is rate-limited and most merge lists are uncapped; add a per-user throttle and per-type caps."),
     ("Make merges atomic [10] and lock plan-progress [11]", "wrap MergeView in a transaction and use select_for_update so a completed day is never lost or half-applied."),
     ("fetch_chapter negative-cache [28]", "a single timeout can silently ship a whole book of scripture-less AI translation; cache only 404s and retry transient failures."),
     ("Re-import republishes pulled books [26] & approvals lost on rebuild [27]", "make is_published/source_type create-only, and persist approvals into the fixture so a rebuild can't un-approve."),
     ("Reject junk identifiers [12][13][14]", "negative chapter orders, 300-char slugs, and unbounded notes all become 500s or storage abuse; validate at the boundary."),
     ("seed_plans atomicity [25]", "a mid-seed crash leaves a permanently empty plan the idempotent command can never repair."),
    ]))

story.append(wave(
    "Wave 3 &mdash; Guardrails so regressions can't recur (parallel track)",
    "Infrastructure that would have caught several of the bugs above and will catch the next batch. Best done alongside "
    "the fixes, not after.",
    [
     ("Tests for the auth boundary [48]", "the security-critical class has zero coverage; add it before touching finding 01."),
     ("Ruff + ESLint/Prettier in CI [49]", "a fast-moving multi-session repo has no static-analysis gate at all; cheap and high-leverage."),
     ("A Playwright smoke suite [50]", "nothing exercises the SPA in a browser or checks the real API contract; a handful of tests closes the frontend/backend drift gap."),
     ("Non-root container + .dockerignore [45]", "stop leaking .env into image layers and shrink the RCE blast radius."),
     ("Fix the deploy-race stale prerender [46]", "add an API content fingerprint the web build verifies, so content deploys can't silently ship old text."),
    ]))

story.append(wave(
    "Wave 4 &mdash; Performance &amp; polish (as capacity allows)",
    "Efficiency and consistency wins on the prerender hot paths, plus the accessibility, RTL, SEO and pipeline items. "
    "None are emergencies; batch them by file to keep diffs small.",
    [
     ("Query hot paths [17][18][19][23]", "memoize the author serializer, defer chapter bodies for the TOC, throttle the search log; measurable build-time and latency wins."),
     ("Payload consistency [15][16]", "restore word_count and topic chips everywhere the shelf serializer is reused."),
     ("Accessibility & RTL [43][44][45][47]", "focus-trap the search drawer, 404 the unknown slugs, guard feed.xml, and convert physical CSS to logical for Arabic."),
     ("Per-locale SEO [42-adjacent, meta fallbacks] [46-F]", "localized meta descriptions so non-English pages stop shipping English snippets."),
     ("The big refactor: fixture growth [46-G]", "the ~75 MB whole-file-rewrite fixture is the one architectural item; scope it as a design note before the content roadmap makes it urgent."),
    ]))

story.append(Spacer(1, 4*mm))
story.append(HRFlowable(width="100%", thickness=0.6, color=RULE, spaceAfter=6))
story.append(Paragraph(
    "One closing note: this is an unusually well-tended codebase &mdash; complete i18n catalogues across eight locales, "
    "a thoughtful hreflang/canonical story, consistent JSON-LD escaping, correct object-scoping on every reading "
    "endpoint (no IDOR found), and production security headers already in place. The findings above are the sharp edges "
    "on a solid foundation, not signs of neglect.",
    st_why))

# ---- doc template with header/footer ----
def deco(canvas, doc):
    canvas.saveState()
    w, h = A4
    if doc.page > 1:
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(20*mm, h-14*mm, w-20*mm, h-14*mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(FAINT)
        canvas.drawString(20*mm, h-12.4*mm, "Ochorus Web App Code Review")
        canvas.drawRightString(w-20*mm, h-12.4*mm, "50 findings + prioritization")
        canvas.setStrokeColor(RULE)
        canvas.line(20*mm, 13*mm, w-20*mm, 13*mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(FAINT)
        canvas.drawCentredString(w/2, 9*mm, str(doc.page))
    canvas.restoreState()

doc = BaseDocTemplate(OUT, pagesize=A4,
                      leftMargin=20*mm, rightMargin=20*mm, topMargin=18*mm, bottomMargin=18*mm,
                      title="Ochorus Web App Code Review", author="Code review")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=deco)])
doc.build(story)
print("wrote", OUT, "pages via build")

# ---- markdown companion --------------------------------------------------
MD = str(Path(__file__).resolve().parent / "ochorus-code-review-2026-08.md")
lines = []
lines.append("# Ochorus Web App Code Review")
lines.append("")
lines.append("**50 issues, bugs, and improvements — with a fix prompt for each.** "
             "Reviewed 7 August 2026. Django REST API + SvelteKit static SPA, multilingual reader.")
lines.append("")
lines.append(f"Severity mix: **{tally['CRITICAL']} critical, {tally['HIGH']} high, "
             f"{tally['MEDIUM']} medium, {tally['LOW']} low.** "
             "A cleanly formatted PDF of this report is at `docs/ochorus-code-review-2026-08.pdf`.")
lines.append("")
lines.append("Six independent review passes (Django API, content/translation pipeline, frontend "
             "sync/offline libraries, routes & components, a security audit across both stacks, and "
             "CI/build/test infrastructure) produced ~98 raw findings, de-duplicated and curated to the 50 below. "
             "Several were reproduced against a live test database (noted in place).")
lines.append("")
_idx = 0
for (code, name, desc), cnt in zip(SECTIONS, SECTION_COUNTS, strict=True):
    plain = name.replace("&amp;", "&")
    lines.append(f"## {code}. {plain}")
    lines.append("")
    lines.append(f"_{desc.replace('&amp;','&')}_")
    lines.append("")
    for _ in range(cnt):
        f = F[_idx]
        _idx += 1
        lines.append(f"### {f['num']:02d}. {f['title']}  — `{f['sev']}`")
        lines.append("")
        lines.append(f"**Files:** `{f['files']}`")
        lines.append("")
        lines.append(f"**What:** {f['what']}")
        lines.append("")
        lines.append(f"**Why it matters:** {f['why']}")
        lines.append("")
        lines.append(f"**Fix prompt:** {f['fix']}")
        lines.append("")
Path(MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", MD)
