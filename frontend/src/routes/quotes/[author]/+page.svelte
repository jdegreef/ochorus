<script lang="ts">
	import type { QuotePage } from '$lib/library-public';
	import { groupQuotes, onPhrase, authorTopicHref, citeChapter, quoteCollectionLd } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { hueForBirthYear } from '$lib/eras';
	import { jsonLd, breadcrumbLd, hreflangFor, absUrl } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import QuoteCard from '$lib/components/QuoteCard.svelte';

	// English-only, and written in English literals for the same reason the
	// scripture pages are: these quotations are lifted from the English works and
	// every citation names an English chapter, so there is no translated version
	// to serve.
	let { data } = $props();
	const page = $derived<QuotePage>(data.page);

	// Grouped by work, which is what earns the colour: the house rule is that a
	// list's hue tracks whatever it is grouped by (STYLE_GUIDE §5), so the
	// ungrouped list this replaced had no claim to one. The API sends the
	// quotations in reading order, so grouping is a scan, not a sort.
	const eraHue = $derived(hueForBirthYear(page.author.birth_year));
	const groups = $derived(groupQuotes(page, eraHue));

	const path = $derived(`/quotes/${page.author.slug}/`);
	const canonical = $derived(`${SITE_URL}${path}`);
	const hreflang = $derived(hreflangFor(path, ['en']));

	const title = $derived(`${page.author.name} — quotes, with sources — Ochorus`);
	const description = $derived(
		`${page.quotes.length} quotations from ${page.author.name}, each one traced to the ` +
			'book, chapter and paragraph it comes from — and linked to the full text, free to read.'
	);

	// Home › Quotes › Author: the page is a child of the quotes index, not of the
	// author's bio. This also gives the index an inbound link from every author
	// page, which is what makes /quotes a hub rather than a dead end.
	const crumbs = $derived([
		{ name: 'Home', href: '/' },
		{ name: 'Quotes', href: '/quotes/' },
		{ name: page.author.name, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));

	// Share card: the author's own portrait when we have one, so a shared quote
	// page wears the face it is about; otherwise the branded /quotes section card
	// (the sixteen image-less pages the topic/plan detail pages already fall back
	// on). Both go through absUrl so the og:image is an absolute URL.
	const ogImage = $derived(
		page.author.photo_url ? absUrl(page.author.photo_url) : absUrl('/og/quotes.png')
	);

	// A CollectionPage → ItemList of Quotations, shared with the author-theme
	// page. The `creator` @id matches the /authors Person node, fusing the quotes
	// with the life into one entity (see quoteCollectionLd).
	const quotesLd = $derived(
		jsonLd(
			quoteCollectionLd({
				name: `Quotations from ${page.author.name}`,
				description,
				url: canonical,
				authorSlug: page.author.slug,
				authorName: page.author.name,
				quotes: page.quotes
			})
		)
	);
</script>

<Seo {title} {description} {canonical} {hreflang} {ogImage} structuredData={[crumbsLd, quotesLd]} />

<!-- max-w-2xl is 42rem — the measure STYLE_GUIDE §2 calls normal, and the
     reason is on this page: at 48rem a quotation ran about 95 characters to
     the line, well past the 45-75 an eye tracks comfortably. Narrowing it and
     setting the quotation a step larger (below) lands at roughly 67. -->
<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<header class="mb-6">
		<h1 class="text-h1">{page.author.name} — in their own words</h1>
		<p class="mt-2 max-w-2xl text-small text-muted">
			{page.quotes.length} quotations, each traced to the exact paragraph it comes from. Follow
			any of them into the full text — free, and without an account.
		</p>
	</header>

	<!-- By theme: the author's deepest subjects, each its own page ("… on
	     Prayer"). Only themes with enough of their quotations to stand on their
	     own appear, so a chip never leads to a thin page. -->
	{#if page.topics.length > 0}
		<nav class="chips" aria-label="Quotes by topic">
			{#each page.topics as t (t.slug)}
				<a href={authorTopicHref(page.author.slug, t.slug)}>
					on {onPhrase(t.title)}
					<span class="n">{t.count}</span>
				</a>
			{/each}
		</nav>
	{/if}

	<!-- Jump row: sixty cards is a long scroll, and the works are the one
	     structure a reader can predict. Same pattern as /scripture. -->
	{#if groups.length > 1}
		<nav class="jump" aria-label="Jump to a work">
			{#each groups as g (g.id)}
				<a href={`#${g.id}`} style={`--hue: ${g.hue}`}>{g.work}</a>
			{/each}
		</nav>
	{/if}

	{#each groups as g (g.id)}
		<section class="group" id={g.id} style={`--hue: ${g.hue}`}>
			<h2 class="work">
				{#if g.slug}
					<a href={`/books/${g.slug}/`}>{g.work}</a>
				{:else}
					{g.work}
				{/if}
				<span class="count text-small font-normal">{g.quotes.length}</span>
			</h2>

			<ol class="quotes">
				{#each g.quotes as q (q.slug)}
					<QuoteCard quote={q} authorName={page.author.name} cite={citeChapter(q)} />
				{/each}
			</ol>
		</section>
	{/each}
</div>

<style>
	/* Every use of --hue goes through color-mix(), never as body text, so
	   contrast holds in both themes (STYLE_GUIDE §5). */
	.jump {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		margin-bottom: 2rem;
	}
	.jump a {
		padding: 0.25rem 0.7rem;
		border-radius: 999px;
		border: 1px solid color-mix(in srgb, var(--hue) 30%, var(--color-border));
		background: color-mix(in srgb, var(--hue) 8%, var(--color-surface));
		font-size: var(--fs-small);
		color: var(--color-text);
		text-decoration: none;
	}
	.jump a:hover {
		background: color-mix(in srgb, var(--hue) 16%, var(--color-surface));
	}

	.group {
		margin-bottom: 2.5rem;
		scroll-margin-top: 5rem;
	}
	.work {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
		margin: 0 0 0.9rem;
		padding-inline-start: 0.7rem;
		border-inline-start: 3px solid color-mix(in srgb, var(--hue) 55%, var(--color-border));
		font-size: var(--fs-h3);
		font-weight: 600;
	}
	.work a {
		color: inherit;
		text-decoration: none;
	}
	.work a:hover {
		text-decoration: underline;
	}


	.quotes {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.75rem;
	}

	/* Theme chips: the author's deepest subjects, sitting under the intro. Quiet
	   pills in the accent, not the era hue — they are navigation, not a group. */
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		margin-bottom: 2rem;
	}
	.chips a {
		display: inline-flex;
		align-items: baseline;
		gap: 0.4rem;
		padding: 0.25rem 0.7rem;
		border-radius: 999px;
		border: 1px solid color-mix(in srgb, var(--color-accent) 25%, var(--color-border));
		background: color-mix(in srgb, var(--color-accent) 6%, var(--color-surface));
		font-size: var(--fs-small);
		color: var(--color-text);
		text-decoration: none;
	}
	.chips a:hover {
		background: color-mix(in srgb, var(--color-accent) 14%, var(--color-surface));
	}
	.chips .n {
		font-size: var(--fs-small);
		color: var(--color-muted);
	}
</style>
