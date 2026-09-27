<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
	import type { Article, ArticleRelated } from '$lib/library-public';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { localizeHref } from '$lib/href';
	import { portraitSrcset } from '$lib/portraits';
	import { absUrl, jsonLd, breadcrumbLd } from '$lib/seo';
	import { getLang, localeName } from '$lib/lang.svelte';
	import { editionSeo, languageFallback } from '$lib/languageFallback';
	import { shareCard, shareImage } from '$lib/coverArt';
	import { editionHref } from '$lib/editionHref';
	import { scrollSpy } from '$lib/scrollSpy.svelte';
	import { listen } from '$lib/listen.svelte';
	import LanguageFallbackNotice from '$lib/components/LanguageFallbackNotice.svelte';
	import { contentLang, readingTime } from '$lib/reading';
	import Reader from '$lib/components/Reader.svelte';
	import FloatingBookmark from '$lib/components/FloatingBookmark.svelte';
	import { readerBookmark } from '$lib/readerBookmark.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import ArticleCard from '$lib/components/ArticleCard.svelte';
	import AccountCta from '$lib/components/AccountCta.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	// The reader detail for one article. Its sibling on the same route is the
	// topic shelf (ArticleTopicShelf) — the [slug]/+page.svelte switch picks one.
	let { article }: { article: Article } = $props();

	/** Links into the ARTICLE's language, not the UI locale: an article falls
	 *  back to English, and the works it names have no English fallback. */
	const inArticleLang = (path: string) => editionHref(path, article.language);

	// The classic this article is written to send you to — the hero cover, the
	// "read it in full" card, and the link preview's image.
	const lead = $derived(article.lead_book);

	// --- Contents --------------------------------------------------------------
	// Resolved server-side (article.toc); the body already carries the matching
	// <h2 id> anchors from that same pass — so the page renders the jump list and
	// never parses or mutates the body. Shown only when there are enough sections
	// to be worth it: inline above the text on a narrow screen, and as a sticky
	// side column on a wide one, lighting the section you are reading.
	const showToc = $derived((article.toc?.length ?? 0) >= 3);
	const spy = scrollSpy(() => (showToc ? article.toc.map((h) => h.id) : []));

	// --- Body: the shared Reader ------------------------------------------------
	// The prose renders through the same <Reader> as the sermon and the
	// biography (kind "article"), so an article gets everything the reader has:
	// highlights and margin notes (synced, and in the Notebook),
	// Listen with follow-along, the verse popover, define, copy/share a quote,
	// and a resume point, and a bookmark (a floating one: this header scrolls
	// away, so a button up there could only ever mark the top). `frac` drives the progress hairline; the reader's own
	// reaching-the-end finishes the article onto the reading history. The
	// header offset stays the reader default: this route keeps the sticky app
	// nav, so a resumed or linked paragraph has to park below it, not under it.
	let reader = $state<Reader | undefined>();
	let body = $state<HTMLElement | undefined>();
	let frac = $state(0);
	const listening = $derived(listen.status !== 'idle');

	const bookmark = readerBookmark({
		kind: 'article',
		slug: () => article.slug,
		title: () => article.h1,
		reader: () => reader,
		body: () => body,
		frac: () => frac
	});

	// --- SEO -------------------------------------------------------------------
	// Self-referential canonical + hreflang — an English canonical on a future
	// translated article would deindex it. Articles are per-language rows with no
	// English fallback, so hreflang lists only the locales this article exists in.
	const path = $derived(`/articles/${article.slug}/`);
	// A missing edition renders the English one (see languageFallback).
	const fallback = $derived(languageFallback(getLang(), article.language));
	const seo = $derived(editionSeo(path, article.available_languages, fallback));
	const hreflang = $derived(seo.hreflang);
	const canonical = $derived(seo.canonical);
	// Attribution for a quote copied or shared from the selection bar: the
	// house byline, the article, and this edition's canonical page.
	const cite = $derived({ author: 'Ochorus', book: article.h1, chapter: '', url: canonical });

	/** The article's other editions, for "Also in …" — only when it has any. */
	const otherEditions = $derived(
		// On a fallback page the notice above already lists the editions.
		!fallback && (article.available_languages?.length ?? 0) > 1
			? hreflang.alternates.filter((a) => a.loc !== article.language)
			: []
	);

	// A real description from the standfirst, falling back to the opening prose.
	const metaDescription = $derived(
		article.description ||
			(article.body_html || '')
				.replace(/<[^>]+>/g, ' ')
				.replace(/\s+/g, ' ')
				.trim()
				.slice(0, 155)
	);
	const titleTag = $derived(`${article.meta_title || article.h1} — Ochorus`);

	// The link preview is the lead book's landscape card — the one its own book
	// page names, so the build has already composed it (an author page borrows
	// its first book's card the same way; see scripts/build-share-cards.mjs).
	// Structured data gets the cover itself, as Book pages do.
	const share = $derived(lead ? shareCard(lead) : null);
	const cover = $derived(lead ? shareImage(lead) : null);

	const updated = $derived.by(() => {
		// Only a real revision: `updated_at` is stamped on creation too, so an
		// article never touched since would otherwise claim an update.
		const d = article.updated_at ? new Date(article.updated_at) : null;
		const made = article.created_at ? new Date(article.created_at).getTime() : NaN;
		if (!d || Number.isNaN(d.getTime())) return '';
		if (!Number.isNaN(made) && d.getTime() - made < 24 * 60 * 60 * 1000) return '';
		return new Intl.DateTimeFormat(getLang(), { day: 'numeric', month: 'short', year: 'numeric' }).format(d);
	});

	const articleLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Article',
			headline: article.h1,
			description: article.description || undefined,
			inLanguage: article.language,
			url: canonical,
			mainEntityOfPage: canonical,
			image: cover ? absUrl(cover.url) : undefined,
			wordCount: article.word_count || undefined,
			articleSection: article.topics?.[0]?.title,
			about: article.topics?.length
				? article.topics.map((tc) => ({ '@type': 'Thing', name: tc.title }))
				: undefined,
			isAccessibleForFree: true,
			datePublished: article.created_at || undefined,
			dateModified: article.updated_at || undefined,
			// There is no per-article author FK (see the backend model); the house
			// name stands as the organizational author, mirroring the publisher.
			author: { '@type': 'Organization', name: 'Ochorus' },
			publisher: { '@type': 'Organization', name: 'Ochorus' }
		})
	);
	// One crumb trail feeds both the visible <Breadcrumb> and the JSON-LD, so the
	// on-page path and the structured BreadcrumbList can't drift apart (the
	// sibling detail routes keep this single source; see books/[slug]).
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.articles'), href: '/articles/' },
		{ name: article.h1, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));

	// The "Read next" label for each funnel target's kind (reuses the search
	// type labels; "Biography" is the singular of the nav word).
	const KIND_LABEL = $derived<Record<ArticleRelated['type'], string>>({
		book: t('search.typeBook'),
		sermon: t('search.typeSermon'),
		author: t('articles.kindBiography')
	});

	const more = $derived(article.more_articles ?? []);
</script>

<Seo
	title={titleTag}
	description={metaDescription}
	{canonical}
	{hreflang}
	ogType="article"
	ogTitle={article.h1}
	ogImage={share ? absUrl(share.url) : ''}
	ogImageWidth={share?.width}
	ogImageHeight={share?.height}
	ogImageAlt={lead ? `${t('a11y.coverOf')} ${lead.title}` : ''}
	structuredData={[articleLd, crumbsLd]}
/>

<!-- How far through the article you are: the shared scroll hairline the
     sermon page and the reader's focus mode use (app.css .read-progress). -->
<div class="read-progress" style="transform: scaleX({frac})" aria-hidden="true"></div>

{#snippet contents(sticky: boolean)}
	<nav class="toc" class:toc-side={sticky} aria-labelledby={sticky ? 'toc-side-heading' : 'toc-heading'}>
		<p id={sticky ? 'toc-side-heading' : 'toc-heading'} class="eyebrow text-muted">
			{t('articles.onThisPage')}
		</p>
		<ul>
			{#each article.toc as h (h.id)}
				<li>
					<a
						href={`#${h.id}`}
						class:is-active={sticky && spy.active === h.id}
						aria-current={sticky && spy.active === h.id ? 'true' : undefined}>{h.text}</a
					>
				</li>
			{/each}
		</ul>
	</nav>
{/snippet}

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />
	<LanguageFallbackNotice {fallback} alternates={hreflang.alternates} browsePath="/articles" />

	<!-- The prose column answers to the reader's text settings (the A a popover:
	     measure, size, face, leading), exactly as the sermon page and the author
	     biography do — not to a hand-set 40rem, which no control could move.
	     readerPrefs is hydrated once by the root layout. On a wide screen the
	     contents sit in a column beside it. -->
	<div class="article-layout" style={readerPrefs.style}>
		{#if showToc}
			<div class="toc-rail">{@render contents(true)}</div>
		{/if}

		<article class="article-col">
			<header class="mb-6 flex items-start gap-6">
				<div class="min-w-0 flex-1">
					<!-- Kind eyebrow (page-design A8): KIND · BYLINE · TIME · UPDATED.
					     Ochorus is the house byline for every article (there is no
					     per-article author — see the backend model), so it is a literal
					     like the kind word, not article data. -->
					<p class="eyebrow mb-1 text-muted">
						{t('search.typeArticle')} · Ochorus · {readingTime(article.word_count)}{#if updated}{' · '}{t(
								'articles.updated'
							).replace('%date%', updated)}{/if}
					</p>
					<h1 class="text-h1" lang={contentLang(article.language)}>{article.h1}</h1>
					{#if article.description}
						<p class="standfirst">{article.description}</p>
					{/if}

					<!-- The page's actions, under the title rather than beside it: four
					     controls in the H1's row crushed it to a column on a phone. -->
					<div class="mt-4 flex flex-wrap items-center gap-2">
						{#if listen.supported}
							<button
								class="btn btn-sm"
								class:btn-ghost={!listening}
								class:btn-primary={listening}
								onclick={() => (listening ? listen.stop() : reader?.startListening())}
								aria-pressed={listening}
							>
								<Icon name="headphones" size={16} />
								{t('reader.listen')}
							</button>
						{/if}
						<!-- Save this article to "My Library". -->
						<FavoriteButton kind="article" slug={article.slug} showLabel />
						<ShareButton url={canonical} title="{article.h1} — Ochorus" showLabel />
						<ReaderControls />
					</div>

					{#if otherEditions.length}
						<p class="mt-3 text-small text-muted">
							{t('articles.alsoIn')}
							<!-- A full load, as LanguageFallbackNotice does: the locale is
							     set per document, so a client-side hop would keep this one. -->
							{#each otherEditions as e, i (e.loc)}{#if i}{' · '}{/if}<a
									href={e.href}
									hreflang={e.loc}
									lang={e.loc}
									data-sveltekit-reload>{localeName(e.loc)}</a
								>{/each}
						</p>
					{/if}
				</div>

				{#if lead}
					<!-- The classic behind the article. The cover is the book's own
					     link; its title is in the "read it in full" card and Read next. -->
					<a
						href={inArticleLang(`/books/${lead.slug}`)}
						class="hero-cover hidden shrink-0 sm:block"
						aria-label="{t('a11y.coverOf')} {lead.title}"
					>
						<BookCover book={lead} />
					</a>
				{/if}
			</header>

			{#if showToc}
				<div class="toc-inline">{@render contents(false)}</div>
			{/if}

			<!-- Server-sanitized HTML (backend rich/bio profile — pull-quotes,
			     internal links, server-wrapped scripture refs, and the <h2 id>
			     anchors the TOC links to); never user input — rendered by the
			     shared Reader, which owns the scripture popover, selection bar,
			     marks, Listen and resume for it (frontend/CLAUDE.md). -->
			<Reader
				bind:this={reader}
				kind="article"
				slug={article.slug}
				language={article.language}
				html={article.body_html}
				{cite}
				listenTitle={article.h1}
				listenArtist="Ochorus"
				class="article-body no-initial"
				bind:body
				bind:frac
				finishOnEnd
			/>

			<!-- "Read it in full": the classic the article was written to send you
			     to, at the moment you have finished reading about it. (It sat
			     mid-article once; inside the Reader's prose any extra block would
			     shift the paragraph index every highlight and bookmark keys on.) -->
			{#if lead}
				<aside class="book-teaser" aria-label={t('articles.readInFull')}>
					<a href={inArticleLang(`/books/${lead.slug}`)} class="w-14 shrink-0" tabindex="-1" aria-hidden="true">
						<BookCover book={lead} />
					</a>
					<div class="min-w-0 flex-1">
						<p class="eyebrow text-accent">{t('articles.readInFull')}</p>
						<a href={inArticleLang(`/books/${lead.slug}`)} class="teaser-title">{lead.title}</a>
						<p class="text-small text-muted">{lead.author.name}</p>
					</div>
					<a href={inArticleLang(`/books/${lead.slug}/1`)} class="btn btn-primary btn-sm shrink-0">
						{t('book.beginReading')}
					</a>
				</aside>
			{/if}

			<!-- The passages the article cites — the same chip row, and the same
			     links, as the sermon page's scripture index: its /scripture page
			     where one exists (English-only pages, so not localized), else a
			     localized search. -->
			{#if (article.scripture_refs?.length ?? 0) >= 2}
				<section class="mt-8" aria-labelledby="scriptures-heading">
					<h2 id="scriptures-heading" class="section-label">{t('articles.scriptures')}</h2>
					<div class="flex flex-wrap gap-2">
						{#each article.scripture_refs ?? [] as ref (ref)}
							<a
								href={article.scripture_links?.[ref] ??
									localizeHref(`/search?q=${encodeURIComponent(ref)}`)}
								class="tag">{ref}</a
							>
						{/each}
					</div>
				</section>
			{/if}

			{#if article.related?.length}
				<aside class="read-next" aria-labelledby="read-next-heading">
					<h2 id="read-next-heading" class="section-label">{t('articles.readNext')}</h2>
					<ul>
						{#each article.related as r (r.type + r.slug)}
							<li>
								<a href={r.url} class="rel-link">
									{#if r.type === 'book' && r.cover_url}
										<img
											class="rel-cover"
											src={r.cover_url}
											use:hydrateSrc={{ src: r.cover_url }}
											alt=""
											loading="lazy"
											style:background={r.cover_color || undefined}
										/>
									{:else if r.type === 'author' && r.photo_url}
										{@const source = { src: r.photo_url, srcset: portraitSrcset(r.photo_url) }}
										<img
											class="rel-portrait"
											src={source.src}
											srcset={source.srcset}
											use:hydrateSrc={source}
											sizes="44px"
											alt=""
											loading="lazy"
										/>
									{/if}
									<span class="rel-text">
										<span class="kind">{KIND_LABEL[r.type]}</span>
										<span class="rel-title">{r.title}</span>
									</span>
								</a>
								{#if r.type === 'book'}
									<!-- Straight into chapter one: the book page is a click
									     the reader who has decided doesn't need. -->
									<a href={inArticleLang(`/books/${r.slug}/1`)} class="btn btn-ghost btn-sm shrink-0">
										{t('book.beginReading')}
									</a>
								{/if}
							</li>
						{/each}
					</ul>
				</aside>
			{/if}

			{#if more.length}
				<section class="mt-10" aria-labelledby="more-heading">
					<h2 id="more-heading" class="section-label">
						{t('articles.moreLikeThis')}
					</h2>
					<div class="flex flex-col gap-3">
						{#each more as a (a.slug)}
							<ArticleCard article={a} heading="h3" />
						{/each}
					</div>
				</section>
			{/if}

			{#if article.topics?.length}
				<nav class="mt-8 flex flex-wrap items-center gap-2" aria-label={t('nav.topics')}>
					<span class="text-small text-muted">{t('nav.topics')}:</span>
					<!-- Link each chip in the language the ARTICLE resolved to
					     (`article.language`), not the page's UI locale. Articles fall
					     back to English, so /sw/articles/<slug> can be the English
					     original; its chips are the backend's list for that language
					     (each one translated into it), but a topic has no English
					     fallback — localizing them to /sw/ points at topic pages that
					     don't exist there and 404s the prerender crawl. -->
					{#each article.topics as topic (topic.slug)}
						<a href={inArticleLang(`/topics/${topic.slug}`)} class="tag">
							{topic.title}
						</a>
					{/each}
				</nav>
			{/if}

			<AccountCta />
		</article>
	</div>
</div>

<!-- Bookmark the spot: floats, because this page's header scrolls away. -->
<FloatingBookmark {bookmark} {frac} />

<style>
	/* The prose column at the reader's measure; on a wide screen, a contents
	   column beside it (the column the grid centres the prose between). */
	.article-col {
		margin-inline: auto;
		max-width: var(--reading-measure);
	}
	.toc-rail {
		display: none;
	}
	@media (min-width: 1200px) {
		.article-layout {
			display: grid;
			grid-template-columns: minmax(0, 1fr) minmax(0, var(--reading-measure)) minmax(0, 1fr);
			column-gap: 3rem;
		}
		.article-col {
			grid-column: 2;
			margin-inline: 0;
			max-width: none;
		}
		.toc-rail {
			display: block;
			grid-column: 1;
			grid-row: 1;
			justify-self: end;
			width: 100%;
			max-width: 15rem;
		}
		.toc-inline {
			display: none;
		}
	}

	.standfirst {
		margin-top: 0.75rem;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		line-height: 1.5;
		color: var(--color-muted);
	}
	.hero-cover {
		width: 7.5rem;
	}
	.hero-cover:hover {
		text-decoration: none;
	}

	/* Prose. The body renders as the Reader's `.reading.article-body`, so size,
	   leading, typeface, measure and colour come from the reader's variables and
	   the text-settings control moves them — like the sermon and the biography
	   (this closes page-design A10 for articles). Only what an article carries
	   that a chapter doesn't is set here, on the global class (the element
	   belongs to <Reader>, which this component's scoped styles can't reach). */
	:global(.article-body h2) {
		/* Keep a contents jump from tucking the heading under the sticky nav. */
		scroll-margin-top: 5rem;
	}
	:global(.article-body ul),
	:global(.article-body ol) {
		margin: 0 0 1.15em;
		padding-inline-start: 1.4rem;
	}
	:global(.article-body ul) {
		list-style: disc;
	}
	:global(.article-body ol) {
		list-style: decimal;
	}
	:global(.article-body li) {
		margin: 0 0 0.4em;
	}
	:global(.article-body a:not(.scripture-ref)) {
		color: var(--color-accent);
		text-underline-offset: 2px;
	}
	/* The pull-quote: the voice of the classic the article leans on, set as a
	   display quote on the gold rule the style guide gives quotations (K1) —
	   in `em`, so it scales with the reader's text size. */
	:global(.article-body blockquote) {
		margin: 1.6em 0;
		padding-inline-start: 1.1em;
		border-inline-start: 3px solid var(--color-gold);
		font-size: 1.12em;
		line-height: 1.5;
		color: var(--color-text);
	}
	:global(.article-body blockquote cite) {
		display: block;
		margin-top: 0.5rem;
		font-family: var(--font-sans);
		font-style: normal;
		font-size: var(--fs-small);
		color: var(--color-muted);
	}

	/* "Read it in full": the lead book, after the article. */
	.book-teaser {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin: 1.75rem 0 2rem;
		padding: 1rem 1.1rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
		font-family: var(--font-sans);
	}
	.book-teaser .teaser-title {
		display: block;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		color: var(--color-text);
	}

	.read-next {
		margin-top: 2.5rem;
		padding: 1.25rem 1.4rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
	}
	.read-next ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.5rem;
	}
	.read-next li {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.read-next .rel-link {
		display: flex;
		flex: 1;
		min-width: 0;
		align-items: center;
		gap: 0.8rem;
		padding: 0.55rem 0.7rem;
		border-radius: var(--radius-sm);
		text-decoration: none;
		color: inherit;
	}
	.read-next .rel-link:hover {
		background: var(--color-accent-soft);
	}
	/* A small book cover (2:3) or a round portrait, so the funnel shows the
	   shelf, not a text list. Fixed box so ragged art doesn't misalign rows. */
	.read-next .rel-cover {
		flex: 0 0 auto;
		width: 2.75rem;
		height: 4.125rem;
		object-fit: cover;
		border-radius: 0.25rem;
		box-shadow: 0 1px 3px rgb(0 0 0 / 0.18);
	}
	.read-next .rel-portrait {
		flex: 0 0 auto;
		width: 2.75rem;
		height: 2.75rem;
		object-fit: cover;
		border-radius: 999px;
	}
	.read-next .rel-text {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
		min-width: 0;
	}
	.read-next .kind {
		font-family: var(--font-sans);
		font-size: var(--fs-eyebrow);
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--color-accent);
	}
	.read-next .rel-title {
		font-family: var(--font-display);
		color: var(--color-text);
	}

	/* On this page — a compact jump list, styled as a quiet bordered aside so it
	   reads as navigation, not part of the prose. The side-column variant is
	   sticky and marks the section in view. */
	.toc {
		margin: 0 0 2rem;
		padding: 0.9rem 1.1rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
	}
	.toc ul {
		list-style: none;
		margin: 0.5rem 0 0;
		padding: 0;
		display: grid;
		gap: 0.35rem;
	}
	.toc a {
		color: var(--color-text);
		text-decoration: none;
		text-underline-offset: 2px;
	}
	.toc a:hover {
		color: var(--color-accent);
		text-decoration: underline;
	}
	.toc-side {
		position: sticky;
		top: calc(var(--appnav-h, 0px) + 1.5rem);
		margin: 0;
		padding: 0;
		border: 0;
		background: none;
		font-size: var(--fs-small);
	}
	.toc-side ul {
		gap: 0;
		border-inline-start: 2px solid var(--color-border);
	}
	.toc-side a {
		display: block;
		margin-inline-start: -2px;
		padding-block: 0.35rem;
		padding-inline: 0.9rem 0;
		border-inline-start: 2px solid transparent;
		color: var(--color-muted);
	}
	.toc-side a.is-active {
		border-inline-start-color: var(--color-accent);
		color: var(--color-accent);
		font-weight: 600;
	}
</style>
