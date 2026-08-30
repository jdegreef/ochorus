<script lang="ts">
	import type { QuoteAuthorSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { hueForBirthYear } from '$lib/eras';
	import { jsonLd, breadcrumb, hreflangFor } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';

	// English literals, as on the author pages and /scripture: this index is not
	// localized because what it lists is not.
	let { data } = $props();
	const authors = $derived<QuoteAuthorSummary[]>(data.authors);

	const path = '/quotes/';
	const canonical = `${SITE_URL}${path}`;
	const hreflang = hreflangFor(path, ['en']);
	const total = $derived(authors.reduce((n, a) => n + a.count, 0));

	const title = 'Christian quotes, with their sources · Ochorus';
	const description =
		'Quotations from the classic Christian writers — Spurgeon, Andrew Murray, ' +
		'Thomas à Kempis — each one traced to the book, chapter and paragraph it comes ' +
		'from, and linked to the full text, free to read.';

	const crumbs = [
		{ name: 'Home', href: '/' },
		{ name: 'Quotes', href: path }
	];
	const crumbsLd = $derived(jsonLd(breadcrumb(crumbs.map((c) => ({ name: c.name, url: c.href })))));
	// A CollectionPage listing each author page, so the set is one entity to a
	// crawler rather than four unrelated URLs.
	const listLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: 'Christian quotes, with their sources',
			description,
			url: canonical,
			hasPart: authors.map((a) => ({
				'@type': 'CreativeWork',
				name: `Quotations from ${a.name}`,
				url: `${SITE_URL}/quotes/${a.slug}/`
			}))
		})
	);
</script>

<Seo {title} {description} {canonical} {hreflang} structuredData={[crumbsLd, listLd]} />

<div class="page-col px-5 py-6">
	<Breadcrumb items={crumbs} />

	<header class="mb-6">
		<h1 class="text-h1">Quotes, with their sources</h1>
		<p class="mt-2 max-w-2xl text-body text-muted">
			The lines these writers are remembered for — {total} of them so far — each traced to the exact
			book, chapter and paragraph it comes from, and linked to the full work. What the unsourced
			quote sites cannot give you is the citation; that is the whole of this.
		</p>
	</header>

	<!-- A card per author. The accent bar wears the author's era hue, the same
	     colour their row carries on the Biographies shelf and their quote page's
	     groups — one consistent visual key for "when". -->
	<ul class="grid gap-3 sm:grid-cols-2">
		{#each authors as a (a.slug)}
			<li>
				<a
					href={`/quotes/${a.slug}/`}
					class="flex items-center gap-4 rounded-card border border-border bg-surface p-4 hover:no-underline"
					style={`--hue: ${hueForBirthYear(a.birth_year)}`}
				>
					<span class="era-bar" aria-hidden="true"></span>
					<span class="flex-1">
						<span class="block text-h3 text-text">{a.name}</span>
						<span class="text-small text-muted"
							>{a.count} quotation{a.count === 1 ? '' : 's'}</span
						>
					</span>
					<span class="text-muted" aria-hidden="true">→</span>
				</a>
			</li>
		{/each}
	</ul>
</div>

<style>
	/* --hue is the era's hex (eras.ts); every use goes through color-mix, never
	   raw, the same rule the author quote page states. */
	.era-bar {
		width: 0.375rem;
		align-self: stretch;
		min-height: 2.5rem;
		border-radius: 999px;
		background: color-mix(in srgb, var(--hue) 60%, var(--color-surface));
	}
	a:hover {
		border-color: color-mix(in srgb, var(--hue) 45%, var(--color-border));
	}
</style>
