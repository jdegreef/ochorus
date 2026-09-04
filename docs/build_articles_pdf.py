#!/usr/bin/env python3
"""Build docs/articles.html — a six-page brief on the Ochorus Articles section:
the data model, the two-layer topic answer, the SEO page anatomy, the first ten
articles, and a rollout plan — in the house style of docs/ideas.html (its exact
<style> and embedded fonts), then render it to docs/articles.pdf with headless
Chrome.

Run:  python3 docs/build_articles_pdf.py
"""
from __future__ import annotations
import html
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "ideas.html"  # borrow its <style> + embedded fonts
OUT_HTML = HERE / "articles.html"
OUT_PDF = HERE / "articles.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def head_from_ideas() -> str:
    doc = SRC.read_text(encoding="utf-8")
    end = doc.index("</style>") + len("</style>")
    return doc[:end]


def esc(s: str) -> str:
    return html.escape(s, quote=False)


# Supplemental styles: a compact title block, tables, a schema diagram, cluster
# chips, and hard page breaks so the document is exactly six pages.
EXTRA_STYLE = """<style>
.cover{ height:auto; padding:8mm 0 4mm; page-break-after:avoid; text-align:start; align-items:flex-start; }
.cover h1{ font-size:30pt; margin:8px 0 6px; }
.cover .sub{ text-align:start; margin:0; max-width:150mm; }
.cover .rule{ margin:10px 0; }
.cover .meta{ margin-top:10px; }
.page{ page-break-before:always; }
.page h2, .intro h2{ font-family:var(--serif); font-size:16.5pt; margin:0 0 6px; }
.page h3.sub-h{ font-family:var(--sans); font-weight:700; font-size:11pt; margin:12px 0 5px; color:var(--accent);
  text-transform:uppercase; letter-spacing:.05em; }
.lede{ font-size:10pt; color:var(--muted); margin:0 0 11px; max-width:170mm; }
p.body{ margin:0 0 8px; color:#3a332a; font-size:9.9pt; }
table{ width:100%; border-collapse:collapse; font-size:9.3pt; margin:6px 0 12px; page-break-inside:avoid; }
th,td{ text-align:left; vertical-align:top; padding:6px 9px; border-bottom:1px solid var(--border); }
th{ font-family:var(--sans); font-size:7.6pt; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); background:var(--surface); }
td.k{ font-family:var(--sans); font-weight:700; white-space:nowrap; }
td.h1{ font-family:var(--serif); font-weight:600; color:var(--accent); font-size:9.6pt; }
.card{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:12px 15px; margin-bottom:9px; page-break-inside:avoid; }
.card h3{ font-family:var(--sans); font-weight:700; font-size:11pt; margin:0 0 5px; }
.card p{ margin:0 0 4px; font-size:9.6pt; color:#3a332a; }
.two{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.small{ font-size:8.8pt; color:var(--muted); }
.foot{ text-align:center; color:var(--muted); font-size:8pt; letter-spacing:.05em; margin-top:20px; padding-top:10px; border-top:1px solid var(--border); }
.diagram{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:14px 16px; margin:8px 0 12px; page-break-inside:avoid; }
.row{ display:flex; align-items:stretch; gap:10px; margin:0 0 8px; }
.box{ flex:1; border:1.5px solid var(--soft-b); background:var(--soft); border-radius:8px; padding:9px 11px; }
.box h4{ margin:0 0 3px; font-family:var(--sans); font-weight:700; font-size:9.4pt; color:var(--accent); }
.box p{ margin:0; font-size:8.8pt; color:#3a332a; line-height:1.4; }
.box.alt{ border-color:var(--border); background:var(--surface-2); }
.box.alt h4{ color:var(--gold); }
.arrow{ align-self:center; font-family:var(--serif); font-size:15pt; color:var(--muted); }
.chips{ margin:4px 0 10px; }
.chip{ display:inline-block; font-family:var(--sans); font-size:8pt; font-weight:700; letter-spacing:.04em;
  color:var(--accent); background:var(--soft); border:1px solid var(--soft-b); border-radius:999px;
  padding:3px 9px; margin:0 5px 5px 0; }
ol.steps{ margin:0; padding-left:18px; font-size:9.7pt; }
ol.steps li{ margin:0 0 5px; }
ul.tick{ list-style:none; padding:0; margin:0 0 8px; }
ul.tick li{ position:relative; padding-left:18px; margin:0 0 4px; font-size:9.5pt; }
ul.tick li:before{ content:""; position:absolute; left:0; top:4px; width:9px; height:9px; border:1.5px solid var(--accent); border-radius:2px; }
.mono{ font-family:var(--mono); font-size:8.4pt; color:#322d5a; }
</style>"""


def render() -> str:
    p = [head_from_ideas(), EXTRA_STYLE, "</head><body>\n"]

    # ---------------------------------------------------------------- Page 1
    p.append(
        '<div class="cover">\n'
        '  <div class="mark">OCHORUS</div>\n  <div class="rule"></div>\n'
        '  <h1>An Articles Section</h1>\n'
        '  <div class="sub">A footer-linked library of devotional &amp; theological articles that turns '
        'topic searches into readers of the classics — the model, the topics answer, the SEO anatomy, '
        'the first ten articles, and how to roll it out.</div>\n'
        '  <div class="meta"><span class="tag">Content &amp; SEO brief · English first · September 2026</span></div>\n'
        '</div>\n'
    )
    p.append(
        '<section class="intro">\n'
        '  <h2>What this is, in one paragraph</h2>\n'
        '  <p class="body">Nobody searches for a public-domain book by name. They search for '
        '<i>problems and questions</i> — &ldquo;how to trust God,&rdquo; &ldquo;what does it mean to abide in '
        'Christ.&rdquo; Articles are the bridge: 1,500&ndash;2,000-word evergreen pages that answer those queries and, '
        'at the end, hand the reader the exact book, sermon, or biography that goes deeper. They rank on their own '
        'and they pass authority down to the library pages, which have thin search demand today. English first; the '
        'per-language model makes translation free later.</p>\n'
        '  <div class="callout">\n    <span class="k">The two decisions this brief settles</span>\n'
        '    Articles carry <strong>no author or byline</strong> — they are simply great pages on the site, not works '
        'attributed to anyone. And topics are handled in <strong>two layers</strong>: articles <strong>reuse the '
        'shared Topic taxonomy</strong> for cross-linking with books and sermons, <em>and</em> get their own '
        '<strong>Series/cluster model</strong> for SEO structure. Both, not either.\n  </div>\n'
        '</section>\n'
    )

    # ---------------------------------------------------------------- Page 2
    p.append('<section class="page">\n  <h2>The data model</h2>\n'
             '  <p class="lede">Mirror the shapes the codebase already uses. Nothing here is novel — an Article is a '
             'Book-shaped row without an author.</p>\n')
    p.append(
        '  <table>\n'
        '    <tr><th style="width:34mm">Field</th><th>What it holds &amp; why</th></tr>\n'
        '    <tr><td class="k">slug + language</td><td><code>unique(slug, language)</code>, exactly like Books and '
        'Sermons. One English row today; a translation is later just a new row on the same slug. There is <b>no '
        'author FK</b>.</td></tr>\n'
        '    <tr><td class="k">title, h1</td><td>The SEO <code>&lt;title&gt;</code> and the on-page <code>&lt;h1&gt;</code> '
        'kept as separate fields — the title tag leads with the keyword, the H1 can be warmer.</td></tr>\n'
        '    <tr><td class="k">dek / meta_description</td><td>The 150-char answer-first summary, used as the meta '
        'description and the lede.</td></tr>\n'
        '    <tr><td class="k">body</td><td>The article HTML/markdown: intro + H2 sections + inline pull-quotes drawn '
        'from the classic authors (reuse the quote infrastructure).</td></tr>\n'
        '    <tr><td class="k">topics (M2M)</td><td>Links to the <b>existing</b> <code>Topic</code> rows — the shared '
        'cross-content graph. (Next page.)</td></tr>\n'
        '    <tr><td class="k">series + order</td><td>FK to a new <code>ArticleSeries</code> for the SEO cluster, plus '
        'a position within it. (Next page.)</td></tr>\n'
        '    <tr><td class="k">related (natural keys)</td><td>The funnel: a list of book / sermon / author slugs the '
        '&ldquo;Read next&rdquo; block renders. This is the whole point of the section.</td></tr>\n'
        '    <tr><td class="k">status, published_at</td><td>draft / published, so a half-written article never ships. '
        'og_image optional (reuse a cover, or a generated card).</td></tr>\n'
        '  </table>\n'
    )
    p.append(
        '  <h3 class="sub-h">Three things to get right</h3>\n'
        '  <ul class="tick">\n'
        '    <li><b>Prerender, do not SPA.</b> Articles must live in the prerendered SEO tier, not the client app — '
        'real <code>&lt;title&gt;</code>, meta, canonical, Open Graph and <code>Article</code> JSON-LD in the source. '
        'This is the entire reason the section exists; an SPA article is invisible to crawlers.</li>\n'
        '    <li><b>Footer, not header.</b> A single &ldquo;Articles&rdquo; link in the footer to <code>/articles</code>; '
        'individual pages at <code>/articles/&lt;slug&gt;</code>. Add every article to the sitemap.</li>\n'
        '    <li><b>Seed as create-only where a workflow owns a field.</b> Same rule as the rest of the library: if an '
        'editor hand-edits <code>status</code> or <code>body</code> after creation, the seed must not revert it on the '
        'next deploy.</li>\n'
        '  </ul>\n'
        '  <div class="callout"><span class="k">One honest note</span>Because articles have no author and are new '
        'writing (not public-domain text), never let one <strong>quote a classic at length</strong> in a way that reads '
        'as the author&rsquo;s own page — keep pull-quotes short and attributed, and let the &ldquo;Read next&rdquo; '
        'link carry the reader to the real work.</div>\n'
        '</section>\n'
    )

    # ---------------------------------------------------------------- Page 3
    p.append('<section class="page">\n  <h2>Topics: two layers, two jobs</h2>\n'
             '  <p class="lede">The question was &ldquo;their own model <i>and</i> reuse the Topics taxonomy — does that '
             'work?&rdquo; Yes, and it is the right call, because these are two different problems.</p>\n')
    p.append(
        '  <div class="diagram">\n'
        '    <div class="row">\n'
        '      <div class="box"><h4>Layer 1 · Reuse Topic (shared)</h4>'
        '<p>Tag each article with existing <code>Topic</code> rows — Prayer, Faith, Grace. Many-to-many. This is the '
        '<b>cross-content graph</b>: the article appears on the shared topic page next to books and sermons, and a book '
        'page can surface &ldquo;Articles about Prayer.&rdquo; The funnel becomes bidirectional.</p></div>\n'
        '      <div class="arrow">+</div>\n'
        '      <div class="box alt"><h4>Layer 2 · ArticleSeries (article-only)</h4>'
        '<p>A new model for the <b>SEO cluster</b>: a pillar article plus its supporting pieces, ordered, with its own '
        'landing page at <code>/articles/&lt;series&gt;</code>. This is publishing structure — it must not leak into the '
        'shared taxonomy that books and sermons also use.</p></div>\n'
        '    </div>\n'
        '    <p class="small" style="margin:2px 0 0">Rule of thumb: <b>Topic</b> answers &ldquo;what is this about?&rdquo; '
        '(shared vocabulary). <b>Series</b> answers &ldquo;which SEO cluster does this belong to, and in what order?&rdquo; '
        '(articles only).</p>\n'
        '  </div>\n'
    )
    p.append(
        '  <h3 class="sub-h">Why not force one to do both</h3>\n'
        '  <p class="body">If you only reused <code>Topic</code>, you&rsquo;d have no clean way to say &ldquo;this is the '
        'pillar, these three support it, render them in this order&rdquo; without overloading a taxonomy that Books and '
        'Sermons also depend on. If you only had a <code>Series</code>, articles would be islands — invisible on the topic '
        'pages that already gather the whole library. Each layer does the job the other cannot.</p>\n'
        '  <h3 class="sub-h">Worked example — the Prayer cluster</h3>\n'
        '  <div class="chips">\n'
        '    <span class="chip">Series: Learning to Pray (pillar + 4)</span>\n'
        '    <span class="chip">Topic: Prayer</span>\n'
        '    <span class="chip">Topic: Faith</span>\n'
        '  </div>\n'
        '  <p class="body">The pillar &ldquo;Spiritual Disciplines Every Christian Should Know&rdquo; sits in the '
        '<b>Learning to Pray</b> series and links down to its four supporting articles (M&uuml;ller, Bounds, Brother '
        'Lawrence, unanswered prayer). Every one of those five is <b>also</b> tagged <b>Topic: Prayer</b>, so they surface '
        'on the site-wide Prayer topic page beside <i>Life of Trust</i>, <i>Power Through Prayer</i>, and the prayer '
        'sermons — and each book page can now show &ldquo;Articles about Prayer&rdquo; in return.</p>\n'
        '  <div class="callout"><span class="k">Net effect</span>Series builds the tight internal-link cluster Google '
        'rewards; Topic wires that cluster into the library you already have. The reader lands from search, reads the '
        'article, and is one click from the actual classic.</div>\n'
        '</section>\n'
    )

    # ---------------------------------------------------------------- Page 4
    p.append('<section class="page">\n  <h2>The anatomy of one article</h2>\n'
             '  <p class="lede">Same skeleton every time — it helps readers, featured snippets, and the writer.</p>\n')
    p.append(
        '  <table>\n'
        '    <tr><th style="width:38mm">Part</th><th>What it does</th></tr>\n'
        '    <tr><td class="k">H1 (warm)</td><td>One per page, keyword-bearing but human. Distinct from the '
        '<code>&lt;title&gt;</code> tag, which leads with the keyword + &ldquo;Ochorus.&rdquo;</td></tr>\n'
        '    <tr><td class="k">Answer-first intro</td><td>2&ndash;3 sentences that answer the query immediately — this is '
        'what wins the featured snippet.</td></tr>\n'
        '    <tr><td class="k">4&ndash;6 H2 sections</td><td>One idea each, ~250&ndash;350 words, with a short attributed '
        'pull-quote from the classic author woven in.</td></tr>\n'
        '    <tr><td class="k">&ldquo;Read next&rdquo; block</td><td>The funnel. Links to the anchor book + bio + sermon '
        'from <code>related</code>. Converts the reader and passes authority to library pages.</td></tr>\n'
        '    <tr><td class="k">Head tags</td><td>meta description, canonical, OG/Twitter, and <code>Article</code> '
        'JSON-LD — all in the <b>prerendered</b> source.</td></tr>\n'
        '  </table>\n'
    )
    p.append(
        '  <h3 class="sub-h">Length &amp; cadence</h3>\n'
        '  <p class="body">1,500&ndash;2,000 words is right — long enough to rank and to genuinely help, short enough to '
        'finish. Publish in <b>clusters, not singletons</b>: a pillar plus its supporting pieces shipped together links '
        'internally from day one, which is what search rewards. Aim for one cluster of 4&ndash;6 every couple of weeks '
        'rather than scattered one-offs.</p>\n'
        '  <h3 class="sub-h">Measuring whether it works</h3>\n'
        '  <ul class="tick">\n'
        '    <li>Impressions &amp; average position per article in Search Console (are the H1/title keywords ranking?).</li>\n'
        '    <li>Click-through from the &ldquo;Read next&rdquo; block into books/sermons/bios — the true conversion.</li>\n'
        '    <li>Which library pages gain traffic <i>because</i> an article links to them (the authority pass-down).</li>\n'
        '  </ul>\n'
        '  <div class="callout"><span class="k">Anchor to content you already have</span>Start every article on an author '
        'whose work is already in the library, so the &ldquo;Read next&rdquo; link is genuinely the best next step. Write '
        'toward the library, not away from it.</div>\n'
        '</section>\n'
    )

    # ---------------------------------------------------------------- Page 5
    articles = [
        ("Answered prayer · George Müller", "How to Pray So That God Answers: Lessons from George Müller",
         "Life of Trust · Müller bio", "Learning to Pray"),
        ("Abiding in Christ · Andrew Murray", "What It Means to Abide in Christ (And How to Actually Do It)",
         "Abide in Christ · Murray bio", "Union with Christ"),
        ("The happy Christian life · Hannah Whitall Smith", "The Secret to a Happy Christian Life",
         "The Christian's Secret… · Smith bio", "The Deeper Life"),
        ("Presence of God · Brother Lawrence", "How to Practice the Presence of God in Ordinary Days",
         "Practice of the Presence · bio", "Learning to Pray"),
        ("Defining faith", "What Is Faith? A Plain, Biblical Answer",
         "Life of Trust · Christian's Secret", "The Deeper Life"),
        ("Trusting God in hardship", "How to Trust God When Your Life Is Falling Apart",
         "Christian's Secret · Life of Trust", "The Deeper Life"),
        ("Humility · Andrew Murray & Bernard", "Why Humility Is the Root of Every Other Virtue",
         "Humility · On Loving God", "Christlike Character"),
        ("Grace · Charles Spurgeon", "What Is Grace? The Gift You Can't Earn and Can't Lose",
         "All of Grace · Spurgeon bio", "Grace & Salvation"),
        ("Unanswered prayer · waiting", "When God Seems Silent: How to Wait on Unanswered Prayer",
         "Power Through Prayer · Life of Trust", "Learning to Pray"),
        ("Devotional Bible reading", "How to Read the Bible Devotionally — Not Just Study It",
         "Imitation of Christ · Abide in Christ", "Christlike Character"),
    ]
    p.append('<section class="page">\n  <h2>The first ten articles</h2>\n'
             '  <p class="lede">Highest search volume &times; strongest existing anchor, front-loading prayer, faith and '
             'trust. Each H1 is the on-page headline; the SEO title tag leads with the keyword and appends &ldquo;— '
             'Ochorus.&rdquo;</p>\n')
    p.append('  <table>\n    <tr><th style="width:8mm">#</th><th style="width:52mm">H1</th>'
             '<th>Subject</th><th style="width:36mm">Read next → &amp; series</th></tr>\n')
    for i, (subj, h1, funnel, series) in enumerate(articles, 1):
        p.append(
            f'    <tr><td class="k">{i}</td><td class="h1">{esc(h1)}</td>'
            f'<td>{esc(subj)}</td>'
            f'<td class="small">{esc(funnel)}<br><span style="color:var(--accent);font-weight:700">{esc(series)}</span></td></tr>\n'
        )
    p.append('  </table>\n')
    p.append(
        '  <p class="small">Series in play: <b>Learning to Pray</b> (1, 4, 9 + a pillar), <b>The Deeper Life</b> '
        '(3, 5, 6), <b>Union with Christ</b> (2), <b>Christlike Character</b> (7, 10), <b>Grace &amp; Salvation</b> (8). '
        'Ship the three Learning-to-Pray pieces plus a &ldquo;Spiritual Disciplines&rdquo; pillar as the first complete '
        'cluster.</p>\n'
        '</section>\n'
    )

    # ---------------------------------------------------------------- Page 6
    p.append('<section class="page">\n  <h2>Rollout</h2>\n'
             '  <p class="lede">One PR per slice, off origin/main, in a worktree — the standing workflow.</p>\n'
             '  <ol class="steps">\n')
    for step in [
        "<b>Model + admin.</b> <code>Article</code> (slug+language, title, h1, dek, body, related, status), "
        "<code>ArticleSeries</code>, and the M2M to the existing <code>Topic</code>. Fixture is one file per article, "
        "natural keys, create-only where a workflow owns the field.",
        "<b>Prerendered routes.</b> <code>/articles</code> index, <code>/articles/&lt;slug&gt;</code>, and "
        "<code>/articles/&lt;series&gt;</code> landing pages — generate <code>entries()</code> from the API, like the "
        "book/author prerender. Add meta, OG, canonical and <code>Article</code> JSON-LD to the head; add all three to "
        "the sitemap.",
        "<b>Footer link + funnel block.</b> One &ldquo;Articles&rdquo; link in the footer (not the header). Build the "
        "reusable &ldquo;Read next&rdquo; component from <code>related</code>, and add &ldquo;Articles about X&rdquo; to "
        "the topic and book pages so the graph is bidirectional.",
        "<b>First cluster.</b> Write the Learning-to-Pray cluster (Müller, Brother Lawrence, unanswered prayer) plus its "
        "pillar, all anchored to books already in the library. Ship together so they link internally on day one.",
        "<b>Measure, then scale.</b> Wire Search Console, watch impressions and the click-through into the library, and "
        "let the winners tell you which of the twenty clusters to write next. Translate only after the English cluster "
        "proves itself.",
    ]:
        p.append(f'    <li>{step}</li>\n')
    p.append('  </ol>\n')
    p.append(
        '  <h3 class="sub-h">The twenty ideas this builds toward</h3>\n'
        '  <p class="body">Beyond the first ten: contemplative prayer (Guyon), the Imitation of Christ (à Kempis), '
        'sanctification, hearing God&rsquo;s voice, prayerlessness &amp; power (Bounds), overcoming anxiety, '
        'Pilgrim&rsquo;s Progress (Bunyan), On Loving God (Bernard), and an African-voices piece on Samuel Crowther that '
        'seeds that cluster early. Each maps to a work already in — or already on the roadmap for — the library.</p>\n'
        '  <div class="callout"><span class="k">The one measure of success</span>An article earns its place when a reader '
        'arrives from a Google search they typed as a <em>question</em>, and leaves having opened the classic that answers '
        'it. Everything above serves that single motion.</div>\n'
        '  <div class="foot">OCHORUS · AN ARTICLES SECTION · CONTENT &amp; SEO BRIEF · PREPARED WITH CLAUDE</div>\n'
        '</section>\n</body></html>\n'
    )
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
