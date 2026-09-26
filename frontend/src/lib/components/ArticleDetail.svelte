<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
	import type { Article, ArticleRelated } from '$lib/library-public';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { localizeHref } from '$lib/href';
	import { locales } from '$lib/paraglide/runtime';
	import { portraitSrcset } from '$lib/portraits';
	import { jsonLd, breadcrumbLd } from '$lib/seo';
	import { getLang } from '$lib/lang.svelte';
	import { editionSeo, languageFallback } from '$lib/languageFallback';
	import LanguageFallbackNotice from '$lib/components/LanguageFallbackNotice.svelte';
	import { scripture } from '$lib/scripture.svelte';
	import { readingTime } from '$lib/reading';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import ScripturePopover from '$lib/components/ScripturePopover.svelte';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import AccountCta from '$lib/components/AccountCta.svelte';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	// The reader detail for one article. Its sibling on the same route is the
	// topic shelf (ArticleTopicShelf) — the [slug]/+page.svelte switch picks one.
	let { article }: { article: Article } = $props();

	// The table of contents is resolved server-side (article.toc), and the body
	// already carries the matching <h2 id> anchors from that same pass — so the
	// page just renders the jump list, never parsing or mutating the body. Shown
	// only when there are enough sections to be worth it.
	const showToc = $derived((article.toc?.length ?? 0) >= 3);

	// Tap a server-wrapped Bible reference in the body → open the scripture
	// popover, the same treatment the chapter/sermon readers give. The body's
	// refs are wrapped as <a class="scripture-ref" data-ref="…"> by the API
	// (see get_body_html); this is the lightweight equivalent of the reader's
	// onScriptureClick, since an article page is a plain document, not the Reader.
	function onBodyClick(e: MouseEvent) {
		const a = (e.target as HTMLElement).closest?.('a.scripture-ref') as HTMLElement | null;
		if (!a?.dataset.ref) return;
		e.preventDefault();
		const r = a.getBoundingClientRect();
		scripture.show(a.dataset.ref, r.bottom + window.scrollY, r.left + window.scrollX + r.width / 2);
	}

	// Self-referential canonical + hreflang — an English canonical on a future
	// translated article would deindex it. Articles are per-language rows with no
	// English fallback, so hreflang lists only the locales this article exists in.
	const path = $derived(`/articles/${article.slug}/`);
	// A missing edition renders the English one (see languageFallback).
	const fallback = $derived(languageFallback(getLang(), article.language));
	const seo = $derived(editionSeo(path, article.available_languages, fallback));
	const hreflang = $derived(seo.hreflang);
	const canonical = $derived(seo.canonical);

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

	const articleLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Article',
			headline: article.h1,
			description: article.description || undefined,
			inLanguage: article.language,
			url: canonical,
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
</script>

<Seo
	title={titleTag}
	description={metaDescription}
	{canonical}
	{hreflang}
	ogType="article"
	ogTitle={article.h1}
	structuredData={[articleLd, crumbsLd]}
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />
	<LanguageFallbackNotice {fallback} alternates={hreflang.alternates} browsePath="/articles" />

	<!-- The prose column answers to the reader's text settings (the A a popover:
	     measure, size, face, leading), exactly as the sermon page and the author
	     biography do — not to a hand-set 40rem, which no control could move.
	     readerPrefs is hydrated once by the root layout. -->
	<article class="mx-auto" style="{readerPrefs.style}; max-width: var(--reading-measure)">
		<header class="mb-5">
			<!-- Kind eyebrow (page-design A8): KIND · BYLINE · TIME. Ochorus is the
			     house byline for every article (there is no per-article author — see
			     the backend model), so it is an English literal like the kind word,
			     not article data. The reading time is localized via readingTime(). -->
			<p class="eyebrow mb-1 text-muted">{t('search.typeArticle')} · Ochorus · {readingTime(article.word_count)}</p>
			<div class="flex items-start justify-between gap-4">
				<h1 class="text-h1">{article.h1}</h1>
				<div class="flex shrink-0 items-center gap-2">
					<!-- Save this article to "My Library". -->
					<FavoriteButton kind="article" slug={article.slug} />
					<ShareButton url={canonical} title="{article.h1} — Ochorus" />
					<ReaderControls />
				</div>
			</div>
			{#if article.description}
				<p class="standfirst">{article.description}</p>
			{/if}
		</header>

		{#if showToc}
			<nav class="toc" aria-labelledby="toc-heading">
				<p id="toc-heading" class="eyebrow text-muted">{t('articles.onThisPage')}</p>
				<ul>
					{#each article.toc as h (h.id)}
						<li><a href={`#${h.id}`}>{h.text}</a></li>
					{/each}
				</ul>
			</nav>
		{/if}

		<!-- Server-sanitized HTML (backend rich/bio profile — pull-quotes, internal
		     links, server-wrapped scripture refs, and the <h2 id> anchors the TOC
		     links to); never user input. The click delegate opens the scripture
		     popover on a tapped reference (same as the reader; see onBodyClick).
		     frontend/CLAUDE.md. -->
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
		<!-- eslint-disable-next-line svelte/no-at-html-tags -->
		<div class="article-body" lang={article.language} onclick={onBodyClick}>{@html article.body_html}</div>

		{#if article.related?.length}
			<aside class="read-next" aria-labelledby="read-next-heading">
				<h2 id="read-next-heading" class="section-heading">{t('articles.readNext')}</h2>
				<ul>
					{#each article.related as r (r.type + r.slug)}
						<li>
							<a href={r.url}>
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
						</li>
					{/each}
				</ul>
			</aside>
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
					<a
						href={localizeHref(`/topics/${topic.slug}`, {
							locale: article.language as (typeof locales)[number]
						})}
						class="tag"
					>
						{topic.title}
					</a>
				{/each}
			</nav>
		{/if}

		<AccountCta />
	</article>
</div>

<!-- The tapped-reference verse popover (self-contained; reads the scripture store). -->
<ScripturePopover />

<style>
	.standfirst {
		margin-top: 0.75rem;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		line-height: 1.5;
		color: var(--color-muted);
	}
	/* Prose. The body is authored HTML (p / h2 / blockquote / cite / a). It
	   consumes the reader's custom properties (set by readerPrefs.style on the
	   <article>) but keeps its own recipe rather than wearing `.reading`: that
	   class sizes from 1.18rem and adds a drop cap, both wrong for an SEO
	   article. Folding this into one shared prose class is page-design A10. */
	.article-body {
		font-family: var(--reading-font, var(--font-display));
		font-size: calc(var(--fs-body) * var(--reading-scale, 1));
		line-height: var(--reading-leading, 1.7);
		text-align: var(--reading-align, start);
		hyphens: var(--reading-hyphens, manual);
		color: var(--color-text);
	}
	.article-body :global(p) {
		margin: 0 0 1.05rem;
	}
	.article-body :global(h2) {
		font-family: var(--font-display);
		font-weight: 600;
		font-size: var(--fs-h2);
		line-height: 1.25;
		margin: 2rem 0 0.75rem;
		color: var(--color-text);
		/* Keep a TOC jump from tucking the heading under the sticky top nav. */
		scroll-margin-top: 5rem;
	}
	.article-body :global(h3) {
		font-weight: 600;
		font-size: var(--fs-h3);
		margin: 1.5rem 0 0.6rem;
	}
	.article-body :global(ul),
	.article-body :global(ol) {
		margin: 0 0 1.05rem;
		padding-inline-start: 1.4rem;
	}
	.article-body :global(li) {
		margin: 0 0 0.4rem;
	}
	.article-body :global(a) {
		color: var(--color-accent);
		text-underline-offset: 2px;
	}
	/* Server-wrapped Bible references: a tappable dotted underline in the text
	   colour, not a loud accent link — matches the reader's .scripture-ref. */
	.article-body :global(a.scripture-ref) {
		color: inherit;
		text-decoration: underline dotted var(--color-accent);
		text-underline-offset: 0.18em;
		cursor: pointer;
	}
	.article-body :global(a.scripture-ref:hover) {
		color: var(--color-accent);
		text-decoration-style: solid;
	}
	.article-body :global(blockquote) {
		margin: 1.4rem 0;
		padding-inline-start: 1.1rem;
		border-inline-start: 3px solid var(--color-accent);
		font-style: italic;
		color: var(--color-text);
	}
	.article-body :global(blockquote cite) {
		display: block;
		margin-top: 0.4rem;
		font-family: var(--font-sans);
		font-style: normal;
		font-size: var(--fs-small);
		color: var(--color-muted);
	}
	.read-next {
		margin-top: 2.5rem;
		padding: 1.25rem 1.4rem;
		border: 1px solid var(--color-border);
		border-radius: 0.75rem;
		background: var(--color-surface);
	}
	.read-next ul {
		list-style: none;
		margin: 0.75rem 0 0;
		padding: 0;
		display: grid;
		gap: 0.5rem;
	}
	.read-next a {
		display: flex;
		align-items: center;
		gap: 0.8rem;
		padding: 0.55rem 0.7rem;
		border-radius: 0.5rem;
		text-decoration: none;
		color: inherit;
	}
	.read-next a:hover {
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
	   reads as navigation, not part of the prose. */
	.toc {
		margin: 0 0 2rem;
		padding: 0.9rem 1.1rem;
		border: 1px solid var(--color-border);
		border-radius: 0.75rem;
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
</style>
