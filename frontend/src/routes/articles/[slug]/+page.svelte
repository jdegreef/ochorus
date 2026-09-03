<script lang="ts">
	import type { Article, ArticleRelated } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { localizeHref } from '$lib/href';
	import { jsonLd, breadcrumb, hreflangFor } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';

	let { data } = $props();
	const article = $derived(data.article as Article);

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
	const titleTag = $derived(`${article.meta_title || article.h1} · Ochorus`);

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
	const crumbsLd = $derived(
		jsonLd(breadcrumb(crumbs.map((c) => ({ name: c.name, url: c.href }))))
	);

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

<div class="page-col px-5 py-6">
	<Breadcrumb items={crumbs} />

	<article class="article">
		<header class="mb-5">
			<h1 class="text-h1">{article.h1}</h1>
			{#if article.description}
				<p class="standfirst">{article.description}</p>
			{/if}
		</header>

		<!-- Server-sanitized HTML (backend bio/rich profile — carries pull-quotes
		     and internal links); never user input. See frontend/CLAUDE.md. -->
		<!-- eslint-disable-next-line svelte/no-at-html-tags -->
		<div class="article-body" lang={article.language}>{@html article.body_html}</div>

		{#if article.related.length}
			<aside class="read-next" aria-labelledby="read-next-heading">
				<h2 id="read-next-heading" class="text-h3">Read next</h2>
				<ul>
					{#each article.related as r (r.type + r.slug)}
						<li>
							<a href={r.url}>
								<span class="kind">{KIND_LABEL[r.type]}</span>
								<span class="rel-title">{r.title}</span>
							</a>
						</li>
					{/each}
				</ul>
			</aside>
		{/if}
	</article>
</div>

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
		align-items: baseline;
		gap: 0.7rem;
		padding: 0.55rem 0.7rem;
		border-radius: 0.5rem;
		text-decoration: none;
		color: inherit;
	}
	.read-next a:hover {
		background: var(--color-accent-soft);
	}
	.read-next .kind {
		flex: 0 0 auto;
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
</style>
