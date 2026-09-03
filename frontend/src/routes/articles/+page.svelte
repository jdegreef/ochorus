<script lang="ts">
	import type { ArticleSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumb, hreflangFor, absUrl } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';

	// English literals, as on /quotes and /scripture: this index is not localized
	// because what it lists is not (articles are English-only for now).
	let { data } = $props();
	const articles = $derived<ArticleSummary[]>(data.articles);

	const path = '/articles/';
	const canonical = `${SITE_URL}${path}`;
	const hreflang = hreflangFor(path, ['en']);

	const title = 'Articles on prayer, faith & the Christian life · Ochorus';
	const description =
		'Short, plain-spoken readings on prayer, faith, grace and the life with God — ' +
		'each one pointing you to a classic Christian book, sermon or life worth reading in full, ' +
		'free.';

	const crumbs = [
		{ name: 'Home', href: '/' },
		{ name: 'Articles', href: path }
	];
	const crumbsLd = $derived(jsonLd(breadcrumb(crumbs.map((c) => ({ name: c.name, url: c.href })))));
	// A CollectionPage listing each article, so the set reads as one entity to a
	// crawler rather than a handful of unrelated URLs.
	const listLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: 'Articles',
			description,
			url: canonical,
			hasPart: articles.map((a) => ({
				'@type': 'Article',
				headline: a.h1,
				url: `${SITE_URL}/articles/${a.slug}/`
			}))
		})
	);
</script>

<Seo {title} {description} {canonical} {hreflang} structuredData={[crumbsLd, listLd]} />

<div class="page-col px-5 py-6">
	<Breadcrumb items={crumbs} />

	<header class="mb-6">
		<h1 class="text-h1">Articles</h1>
		<p class="mt-2 max-w-2xl text-body text-muted">
			Short readings on prayer, faith and the life with God — each one written to send you on to a
			classic worth reading in full.
		</p>
	</header>

	{#if articles.length}
		<ul class="article-list">
			{#each articles as a (a.slug)}
				<li>
					<a class="article-card" href="/articles/{a.slug}/">
						<h2 class="text-h3">{a.h1}</h2>
						{#if a.description}
							<p class="mt-1 text-body text-muted">{a.description}</p>
						{/if}
						<span class="read-more">Read →</span>
					</a>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="text-body text-muted">No articles yet — check back soon.</p>
	{/if}
</div>

<style>
	.article-list {
		display: grid;
		gap: 0.75rem;
		max-width: 44rem;
	}
	.article-card {
		display: block;
		padding: 1.1rem 1.25rem;
		border: 1px solid var(--color-border);
		border-radius: 0.75rem;
		background: var(--color-surface);
		text-decoration: none;
		color: inherit;
		transition:
			border-color 0.15s ease,
			transform 0.15s ease;
	}
	.article-card:hover {
		border-color: var(--color-accent);
		transform: translateY(-1px);
	}
	.article-card h2 {
		color: var(--color-text);
	}
	.read-more {
		display: inline-block;
		margin-top: 0.6rem;
		font-family: var(--font-sans);
		font-weight: 600;
		color: var(--color-accent);
	}
</style>
