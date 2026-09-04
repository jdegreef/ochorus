<script lang="ts">
	import type { Article, ArticleRelated } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { localizeHref } from '$lib/href';
	import { jsonLd, breadcrumbLd, hreflangFor } from '$lib/seo';
	import { scripture } from '$lib/scripture.svelte';
	import { readingTime } from '$lib/reading';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import ScripturePopover from '$lib/components/ScripturePopover.svelte';

	let { data } = $props();
	const article = $derived(data.article as Article);

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
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const hreflang = $derived(hreflangFor(path, article.available_languages));

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
			// No author — an article carries no byline (see the backend model).
			publisher: { '@type': 'Organization', name: 'Ochorus' }
		})
	);
	// One crumb trail feeds both the visible <Breadcrumb> and the JSON-LD, so the
	// on-page path and the structured BreadcrumbList can't drift apart (the
	// sibling detail routes keep this single source; see books/[slug]).
	const crumbs = $derived([
		{ name: 'Home', href: '/' },
		{ name: 'Articles', href: '/articles/' },
		{ name: article.h1, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));

	// The "Read next" label for each funnel target's kind.
	const KIND_LABEL: Record<ArticleRelated['type'], string> = {
		book: 'Book',
		sermon: 'Sermon',
		author: 'Biography'
	};
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

	<article class="article">
		<header class="mb-5">
			<!-- Kind eyebrow (page-design A8): KIND · TIME. The reading time is
			     localized via readingTime(); the kind word is an English literal,
			     as are this page's other chrome strings (see F3). -->
			<p class="eyebrow mb-1 text-muted">Article · {readingTime(article.word_count)}</p>
			<h1 class="text-h1">{article.h1}</h1>
			{#if article.description}
				<p class="standfirst">{article.description}</p>
			{/if}
		</header>

		{#if showToc}
			<nav class="toc" aria-labelledby="toc-heading">
				<p id="toc-heading" class="eyebrow text-muted">On this page</p>
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
				<h2 id="read-next-heading" class="text-h3">Read next</h2>
				<ul>
					{#each article.related as r (r.type + r.slug)}
						<li>
							<a href={r.url}>
								{#if r.type === 'book' && r.cover_url}
									<img
										class="rel-cover"
										src={r.cover_url}
										alt=""
										loading="lazy"
										style:background={r.cover_color || undefined}
									/>
								{:else if r.type === 'author' && r.photo_url}
									<img class="rel-portrait" src={r.photo_url} alt="" loading="lazy" />
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
			<nav class="mt-8 flex flex-wrap items-center gap-2" aria-label="Topics">
				<span class="text-small text-muted">Topics:</span>
				{#each article.topics as topic (topic.slug)}
					<a
						href={localizeHref(`/topics/${topic.slug}`)}
						class="rounded-full border border-border px-3 py-1 text-small text-muted hover:border-accent hover:text-accent hover:no-underline"
					>
						{topic.title}
					</a>
				{/each}
			</nav>
		{/if}
	</article>
</div>

<!-- The tapped-reference verse popover (self-contained; reads the scripture store). -->
<ScripturePopover />

<style>
	.article {
		max-width: 40rem;
	}
	.standfirst {
		margin-top: 0.75rem;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		line-height: 1.5;
		color: var(--color-muted);
	}
	/* Prose. The body is authored HTML (p / h2 / blockquote / cite / a), so the
	   article styles it here rather than borrowing the reader's chrome. */
	.article-body {
		font-family: var(--font-display);
		font-size: var(--fs-body);
		line-height: 1.7;
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
