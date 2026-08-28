<script lang="ts">
	import type { QuotePage } from '$lib/library-public';
	import { quoteHref } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumb, hreflangFor } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';

	// English-only, and written in English literals for the same reason the
	// scripture pages are: these quotations are lifted from the English works and
	// every citation names an English chapter, so there is no translated version
	// to serve. Adding catalogue keys would either claim translations nobody has
	// reviewed or fail the advertised-locale completeness gate.
	let { data } = $props();
	const page = $derived<QuotePage>(data.page);

	const path = $derived(`/quotes/${page.author.slug}/`);
	const canonical = $derived(`${SITE_URL}${path}`);
	const hreflang = $derived(hreflangFor(path, ['en']));

	const title = $derived(`${page.author.name} — quotes, with sources · Ochorus`);
	const description = $derived(
		`${page.quotes.length} quotations from ${page.author.name}, each one traced to the ` +
			'book, chapter and paragraph it comes from — and linked to the full text, free to read.'
	);

	const crumbs = $derived([
		{ name: 'Home', href: '/' },
		{ name: page.author.name, href: `/authors/${page.author.slug}` },
		{ name: 'Quotes', href: path }
	]);
	const crumbsLd = $derived(
		jsonLd(breadcrumb(crumbs.map((c) => ({ name: c.name, url: c.href }))))
	);
	// Each card is a Quotation tied to its work — the markup equivalent of the
	// citation printed on it.
	const quotesLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: `Quotations from ${page.author.name}`,
			description,
			url: canonical,
			hasPart: page.quotes.map((q) => ({
				'@type': 'Quotation',
				text: q.text,
				spokenByCharacter: page.author.name,
				isPartOf: { '@type': 'Book', name: q.source.work },
				url: `${SITE_URL}${quoteHref(q)}`
			}))
		})
	);

	const cite = (q: QuotePage['quotes'][number]) =>
		q.source.order === null
			? q.source.work
			: `${q.source.work}, chapter ${q.source.order}`;
</script>

<Seo {title} {description} {canonical} {hreflang} structuredData={[crumbsLd, quotesLd]} />

<div class="mx-auto max-w-3xl px-5 py-6">
	<Breadcrumb items={crumbs} />

	<header class="mb-8">
		<h1 class="text-h1">{page.author.name} — in his own words</h1>
		<p class="mt-2 max-w-2xl text-small text-muted">
			{page.quotes.length} quotations, each traced to the exact paragraph it comes from. Follow
			any of them into the full text — free, and without an account.
		</p>
	</header>

	<ol class="quotes">
		{#each page.quotes as q (q.slug)}
			<li class="quote">
				<blockquote>{q.text}</blockquote>
				<!-- The citation IS the product: an unsourced card is what the
				     aggregators already publish. It links to the paragraph, not just
				     the chapter, using the reader's own `?p=` jump. -->
				<a class="cite" href={quoteHref(q)}>
					{cite(q)}<span class="para">¶{q.paragraph}</span>
				</a>
			</li>
		{/each}
	</ol>
</div>

<style>
	.quotes {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 1rem;
	}
	.quote {
		padding: 1.1rem 1.3rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
	}
	.quote blockquote {
		margin: 0;
		font-family: var(--font-display, Georgia, serif);
		font-size: var(--fs-body);
		line-height: 1.55;
		color: var(--color-text);
	}
	.cite {
		display: inline-block;
		margin-top: 0.6rem;
		font-size: var(--fs-small);
		color: var(--color-muted);
		text-decoration: none;
	}
	.cite:hover {
		color: var(--color-accent);
		text-decoration: underline;
	}
	.para {
		margin-inline-start: 0.4rem;
		font-variant-numeric: tabular-nums;
		opacity: 0.75;
	}
</style>
