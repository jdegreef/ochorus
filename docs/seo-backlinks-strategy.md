# Ochorus — Backlinks & Site-Rank Growth Strategy

_Drafted 2026-09-18. A plan for earning authority and climbing the rankings, tailored to
what Ochorus already is and already has built. Companion to `content-growth-plan.md`
(which covers the on-site content lever) and `perquote-seo.html`._

---

## 1. The strategic thesis (read this first)

Ochorus is not a normal startup with a thin site trying to fake authority. It is a
**large, multilingual, evergreen library of public-domain Christian classics** with a
**mature on-site SEO layer already shipped**. That changes the whole plan.

Two facts drive everything below:

1. **On-site SEO is largely done.** We already have: a sitemap _index_ with per-type
   children, full hreflang + image sitemaps; comprehensive prerendering with a 6-hourly CI
   audit against production; wide JSON-LD (Book, Article, Person, FAQPage, BreadcrumbList,
   CollectionPage/ItemList, Quotation, WebSite+SearchAction, Organization); a single shared
   head/OG/Twitter component; 5 live languages with false-alternate protection; **90 of 92
   authors with bios and FAQ**; and a whole content-generation skill suite
   (`write-article`, `write-biography`, `quote-extraction`, `sermon-questions`, `og-cards`,
   `topic-emblems`, `level-up-cover`) purpose-built as the SEO growth lever. **We do not
   need to rebuild technical SEO.** We need to (a) flip a few switches that aren't on yet,
   and (b) go earn off-site authority — which is genuinely greenfield.

2. **Our content IS the linkable asset.** The hardest thing in link building — having
   something people _want_ to cite — we already have at scale: the actual full texts of
   classics, free, multilingual, well-formatted, with schema. Most sites manufacture
   "linkable assets" (studies, tools, calculators). We host the primary sources scholars,
   pastors, bloggers, students and Wikipedia editors are _already looking for_. The job is
   to be _found_ and _cited_, not to invent link bait.

So the strategy is: **finish the on-site foundation (a handful of switches), then run a
sustained earned-links + digital-PR + niche-partnership program that leverages the library
as the citable asset.** Backlinks are still a top-3 Google ranking factor and are expected
to stay one — but in 2026 they must be _earned, not bought_. (See Sources.)

---

## 2. Where we stand — the foundation (from the code audit)

**Already solid — build ON this, don't redo it:**

- Sitemap index + per-type children (`frontend/src/lib/sitemap.ts`), full hreflang,
  image sitemap, graceful degradation, `prerenderCoverage.test.ts` gate.
- Hand-tuned `robots.txt` (blocks admin/thin pages + the old WordPress corpse paths).
- Static-adapter prerendering with `entries()` per locale + `prerender-audit.yml` CI every 6h.
- Rich JSON-LD across every content type; one shared `Seo.svelte` head component.
- 5 live/advertised locales (`en, es, sw, lg, pt`); more gated until an admin "goes live"
  (deliberate thin-content guard).
- Content footprint: ~125 books, ~160 sermons, ~82 articles, 92 authors (90 with bios+FAQ),
  33 topics, ~9 plans, quotes + scripture graph — multiplied across live locales.
- Strong internal linking already: "Read next" funnels, breadcrumb graph, topic/quote cross-links.

**Gaps / switches to flip (these become items #1–#5 below):**

- **Analytics is OFF** unless `PUBLIC_PLAUSIBLE_DOMAIN` is set. We're flying blind on
  real impression data — and `content-growth-plan.md` explicitly says to re-rank targets by
  real impressions once Plausible lands.
- **No in-repo Google Search Console verification** — confirm the property is verified and
  make it durable.
- **~1,890 chapter pages prerender but are deliberately un-advertised** in the sitemap
  (crawl-budget choice). An authority push may justify re-advertising some.
- **Content depth is English-heavy** — non-English locales have partial coverage.
- **No off-site / outreach program exists yet** — the whole of §4–§6 is new work.

---

## 3. The Top 20 Ways (the menu)

Grouped by tier, but numbered 1–20 so we can track them. Effort/impact and owner noted.
"Flip" = config/switch we control; "Earn" = outreach/relationship; "Make" = content we produce.

### Tier 1 — On-site switches to flip first (weeks 1–2, high ROI, low effort)

**1. Turn on analytics + fully verify Search Console.** Set `PUBLIC_PLAUSIBLE_DOMAIN`
(cookieless Plausible, already wired in `analytics.ts`; add host to CSP in `render.yaml`).
Confirm GSC + Bing Webmaster Tools verification; submit the sitemap index; add IndexNow for
Bing/Yandex. _Without impression data every other decision is a guess._ (Flip.)

**2. Mine Search Console for "striking-distance" keywords.** Once data flows, pull queries
ranking positions 5–20 and improve those exact pages (title, headings, internal links, a
Q&A block). This is the fastest rank lift available and needs no backlinks. (Flip → Make.)

**3. Selectively re-advertise high-value chapter/scripture pages.** The chapter machinery
is intact and reversible in one `.filter`. As authority grows, promote the best-performing
books' chapters (and scripture chapter pages) back into the sitemap to expand the indexed
footprint deliberately, watching GSC "Discovered – not indexed". (Flip, staged.)

**4. Deepen internal linking into topical clusters.** We already have topics, "Read next",
and breadcrumbs. Formalize **pillar → cluster** structure: each topic page = a pillar; books,
sermons, articles, quotes on that theme = the cluster, all cross-linked. Google rewards a
dense internal link graph on a subject far more than one long page. (Make; leverages existing
topic/quote machinery.)

**5. Close the multilingual depth gap on our strongest works.** hreflang correctly hides
gaps, but each new translation of an already-ranking book/sermon/article is a new indexable,
rankable page in a less-competitive language market. Prioritize by GSC impressions per
locale, then use `translation-worker`. (Make; existing pipeline.)

### Tier 2 — Ochorus-specific backlink goldmines (the unfair advantages)

**6. Wikipedia & Wikisource citations.** This is our single highest-authority, most
on-topic backlink source and it maps 1:1 to our catalog. Wikipedia articles about these
authors and their books can cite Ochorus as a free full-text source; Wikisource is the
Wikimedia library of exactly these public-domain texts and links out to hosts. Process:
for each author/book we host, find the corresponding Wikipedia article and, _where it
genuinely improves the article_, add Ochorus as an "External links"/further-reading source.
**Do this as a real contributing editor, respecting notability and citation norms — never
spam.** Even nofollow, these seed discovery and carry topical trust. (Earn; high effort,
very high value.)

**7. Church / seminary / ministry `.edu` and `.org` links.** Churches, Bible colleges,
seminaries and ministries routinely link to free Christian resource lists. These are
high-trust, on-topic domains. Build a target list; offer a genuinely useful "free classics
library" resource; ask to be added to their reading lists / resource pages. (Earn.)

**8. Resource-page link building.** Search for existing pages like "best free Christian
ebooks", "classic Christian books online", "free Puritan/Reformed texts", "[author] books
free" — many are outdated or incomplete. Reach out offering Ochorus as an addition. Our
multilingual + clean-reader angle is a real differentiator vs. Project Gutenberg/CCEL. (Earn.)

**9. Broken-link reclamation on our exact niche.** Christian classic texts have a long tail
of dead links (defunct sites, moved CCEL pages, broken archive.org links). Find pages
linking to now-dead copies of texts we host, and offer our live, well-formatted page as the
replacement. Highest-conversion outreach tactic there is, because we're doing the linker a
favor. (Earn.)

**10. Directory + aggregator listings.** Get listed in curated, real directories: free-ebook
aggregators, Christian resource directories, library link lists, "alternatives to X" pages,
open-education resource (OER) lists, and app/tool directories if we ship the mobile app.
Skip spammy link farms — quality over quantity. (Earn.)

### Tier 3 — Digital PR & earned editorial links (the compounding engine)

**11. Journalist-request platforms (the HARO successor stack).** Work a small stack:
**Source of Sources** (free, Peter Shankman's HARO successor), **Qwoted** and **Featured**
(higher-authority), plus the `#journorequest` feeds on X/Bluesky. Respond within the hour
with a ready-to-publish quote. The founder / a named contributor can comment on stories
about faith, reading habits, public-domain/open access, digital ministry, AI + religion,
etc. Digital PR is the single most powerful link-earning strategy in 2026. (Earn.)

**12. Original data / research as link bait.** We are sitting on unique data most outlets
would love: which classics are most-read, by language/region; reading-completion patterns;
the multilingual demand map; "the most-read Christian book in [country]". Publish an annual
"State of Reading the Classics" report or interactive map. Original data is the most
citation-attracting content type there is. (Make → Earn.)

**13. Founder thought-leadership / guest contributions.** Genuine, non-spammy guest essays
and podcast appearances in the Christian-media and open-knowledge worlds (why the classics
still matter, building a free multilingual library, public-domain preservation, faith +
tech). Editorial links + brand. Quality outlets only. (Earn.)

**14. Unlinked-mention reclamation.** Set up alerts (Google Alerts / a mention tool) for
"Ochorus". When someone mentions us without linking, ask them to link — the warmest, easiest
"link" there is. Grows automatically as awareness grows. (Earn.)

### Tier 4 — Content as a linkable, cite-able asset (leaning on our skills)

**15. Scale the Articles layer as topical-authority hubs.** `write-article` already
produces 1500–2000-word SEO articles that funnel into the library. Point them at real
search demand (from GSC + keyword research), organize into the topic clusters (#4), and make
each one genuinely the best free answer to its question. This is our content flywheel. (Make.)

**16. Grow author bios + Q&A for E-E-A-T.** 90/92 authors already have bios + FAQ — finish
the last 2, then _deepen_ the strongest, adding `same_as` links, real quotes, and answered
Q&A (FAQPage schema already emitted). Author authority pages are exactly what Google's
E-E-A-T + Helpful Content systems reward, and they're natural link targets for anyone
writing about that author. (Make; `write-biography`, `sermon-questions`.)

**17. Quote pages as micro-linkable assets.** `perquote-seo.html` already lays this out:
individual, shareable, schema'd quotations are highly linkable and shareable ("[Author]
quote on prayer"). Grow toward the ~50-quotes-per-author goal (`quote-extraction`) and make
each quote page share-ready with an OG card. (Make.)

**18. Answer Engine / Generative Engine Optimization (AEO/GEO).** AI assistants
(ChatGPT Search, Perplexity, Google AI answers) now send meaningful traffic and _cite_
sources. Our clean server-rendered HTML + rich schema already make us citable; press the
advantage with clear, question-shaped headings, concise summaries, and FAQ blocks so we get
named as the source. Confirm we don't block reputable AI crawlers we _want_ citing us. (Make/Flip.)

### Tier 5 — Distribution, community & social signals (discovery + seeding)

**19. Community seeding on high-crawl domains.** Genuine, non-spammy participation where our
audience already is: relevant subreddits (r/Christianity, r/Reformed, r/TrueChristian,
book/reading subs), Christian forums, and communities like Goodreads. Links from
constantly-crawled domains (Reddit, etc.) seed fast discovery of new pages even when
nofollow. Contribute value first; link only when genuinely relevant. (Earn.)

**20. Owned distribution + share loops.** Build the channels that compound: an email
newsletter (new translations, "classic of the week", reading plans), a light social
presence sharing quote cards (#17) and articles, and share buttons wired to our existing OG
cards. Owned audiences drive repeat visits and organic shares → natural links, and give us a
place to _announce_ the linkable assets from #12. (Make.)

---

## 4. What NOT to do (avoid the ways this backfires)

- **No buying links, PBNs, link farms, or bulk directory blasts.** One contextual link from
  a high-authority, relevant site beats dozens of low-quality ones — and manipulative links
  risk a penalty. Every link above is earned or editorial.
- **No Wikipedia/Wikisource/Reddit spam.** These only work if we're a genuine contributor.
  Spammy self-linking gets reverted and can get the domain blacklisted. Add value; link where
  it truly belongs.
- **No thin auto-translated pages just to inflate page count.** That's exactly why we gate
  locales until "go live". Machine-translation-only pages read poorly to natives and hurt.
  Depth over count.
- **No keyword-stuffing or AI-generated filler.** Google's Helpful Content system targets
  exactly this. Everything ships review-gated and genuinely useful, as we already do.

---

## 5. The 90-day plan (sequenced)

**Weeks 1–2 — Instrument & flip (items 1, 2).**
- Set `PUBLIC_PLAUSIBLE_DOMAIN`; update CSP in `render.yaml`; confirm analytics live.
- Verify GSC + Bing; submit sitemap index; wire IndexNow.
- Baseline: current impressions, indexed-vs-submitted per type, referring domains, top queries.
- _Deliverable: a real dashboard. Nothing else is prioritized well until this exists._

**Weeks 3–6 — On-site lift + goldmine outreach starts (items 4, 6, 8, 9, 15).**
- Pull striking-distance queries (#2); improve those pages.
- Formalize one or two topic clusters end-to-end as the template (#4).
- Begin Wikipedia/Wikisource contributions for our top 20 authors/books (#6) — steady,
  legitimate, a few per week.
- Start resource-page + broken-link outreach (#8, #9): build the target list, send first batch.
- Ship the next wave of cluster articles via `write-article` (#15).

**Weeks 7–10 — Digital PR engine on (items 11, 13, 14, 19).**
- Join Source of Sources / Qwoted / Featured; answer daily (#11).
- Set up "Ochorus" mention alerts; start reclamation (#14).
- First guest contribution / podcast outreach (#13).
- Begin genuine community participation (#19).

**Weeks 11–13 — Linkable assets + measure (items 12, 17, 20, then revisit 3, 5, 16, 18).**
- Publish the first original-data piece (e.g. "most-read classics by language") (#12) and
  pitch it (#11/#13).
- Grow quote pages + share loop (#17, #20).
- Review GSC: re-advertise chapters where it's earned (#3); prioritize translations by
  impression (#5); deepen the highest-traffic author pages (#16); tune AEO/GEO (#18).
- _Deliverable: a report of referring-domain growth, impression growth, and top movers,
  and a prioritized list for the next quarter._

**Ongoing (every quarter):** re-rank all targets by real impressions; keep the article /
translation / quote flywheel turning; keep working the PR stack and outreach; publish one
new linkable-asset per quarter.

---

## 6. How we'll measure it

Track monthly (mostly free tools — GSC, Bing, Plausible, plus a backlink checker):

- **Referring domains** (the real backlink KPI — domains, not raw link count) and their quality/relevance.
- **Organic impressions & clicks** (GSC), overall and per content type and per locale.
- **Indexed vs. submitted** per sitemap section (already split for exactly this).
- **Keyword positions** for target queries; count of queries in positions 1–3 / 4–10.
- **Assisted/AI-referral traffic** (citations from AI answer engines, referral logs).
- **Outreach funnel**: prospects → contacted → links won, per tactic (know which tactics pay).

Set a simple quarterly target once we have a baseline (e.g. "+X referring domains, +Y%
impressions"). Don't set numeric targets before week-2 data exists.

---

## 7. First five concrete moves (if you want to start today)

1. Set `PUBLIC_PLAUSIBLE_DOMAIN` and confirm GSC verification — get data flowing (#1).
2. Build the Wikipedia/Wikisource target list for our top 20 authors and start contributing (#6).
3. Build the resource-page + broken-link prospect list for "free Christian classics" (#8, #9).
4. Sign up for Source of Sources (free) and start answering relevant requests (#11).
5. Pick one topic and build it into a complete pillar→cluster as the repeatable template (#4).

---

## 8. Sources (research behind this plan, 2026)

Link building / backlinks (still a top-3 ranking factor; earned not bought; digital PR,
resource pages, broken links, unlinked mentions, original data):
- Semrush — How to Get Backlinks in 2026: https://www.semrush.com/blog/how-to-get-backlinks/
- Link-Assistant — 9 Powerful Link Building Strategies for 2026: https://www.link-assistant.com/news/link-building-strategies.html
- ALM Corp — Definitive Guide to Link Building 2026: https://almcorp.com/blog/definitive-guide-link-building-2026/

Topical authority / E-E-A-T / content clusters (pillar+cluster beats one long page; internal
link graph; Helpful Content):
- Knapsack — What Is Topical Authority in SEO (2026): https://knapsackcreative.com/blog/seo/topical-authority-in-seo
- Digital Applied — SEO Content Clusters 2026: https://www.digitalapplied.com/blog/seo-content-clusters-2026-topic-authority-guide
- Keywords Everywhere — Google E-E-A-T Guidelines (2026 Playbook): https://keywordseverywhere.com/blog/google-e-e-a-t-guidelines-an-overview/

Digital PR / HARO successors (Source of Sources, Qwoted, Featured; respond fast, real
expertise):
- Barchart — HARO Alternatives 2026: https://www.barchart.com/story/news/196157/haro-alternatives-2026-complete-guide-to-pr-and-link-building-platforms
- BuzzStream — 10 Best HARO Alternatives: https://www.buzzstream.com/blog/haro-alternatives/

Multilingual / international SEO (hreflang correctness; subdirectories consolidate authority;
translation quality; AEO/GEO in native languages):
- Digital Applied — International SEO 2026 (Hreflang): https://www.digitalapplied.com/blog/international-seo-2026-hreflang-multilingual-guide
- ai-glot — 10 Multilingual SEO Best Practices (2026): https://ai-glot.com/blog/multilingual-seo-best-practices

Indexing / domain authority / AI crawlers need server-rendered HTML; GSC is the direct
indexing lever; nofollow still seeds discovery:
- DEV — How to Get a New Site Indexed by Google in 2026: https://dev.to/mrtd/how-to-get-a-new-site-indexed-by-google-in-2026-what-works-whats-a-waste-8do
- Index Machine — Why Google Stopped Indexing New Sites 2025–2026: https://indexmachine.co/blog/google-stopped-indexing-new-sites-2025-2026-what-changed

Wikipedia / Wikisource (Wikisource = the Wikimedia library of public-domain texts; Wikipedia
cites full texts as sources/further reading):
- Wikisource — What is Wikisource?: https://en.wikisource.org/wiki/Wikisource:What_is_Wikisource
- Wikipedia — Wikipedia:Wikisource: https://en.wikipedia.org/wiki/Wikipedia:Wikisource
