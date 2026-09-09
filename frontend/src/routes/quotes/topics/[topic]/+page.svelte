<script lang="ts">
	import type { QuoteTopicPage } from '$lib/library-public';
	import { onPhrase, citeLine, authorTopicHref } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { hueForBirthYear } from '$lib/eras';
	import { jsonLd, breadcrumbLd, hreflangFor, absUrl } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import QuoteCard from '$lib/components/QuoteCard.svelte';
	import ScriptureEpigraph from '$lib/components/ScriptureEpigraph.svelte';
	import AccountCta from '$lib/components/AccountCta.svelte';

	// English-only, like the author quote pages: the quotations are lifted from
	// the English works and every citation names an English chapter.
	let { data } = $props();
	const page = $derived<QuoteTopicPage>(data.page);
	const topic = $derived(page.topic);
	const phrase = $derived(onPhrase(topic.title));
	const total = $derived(page.authors.reduce((n, g) => n + g.count, 0));

	const path = $derived(`/quotes/topics/${topic.slug}/`);
	const canonical = $derived(`${SITE_URL}${path}`);
	const hreflang = $derived(hreflangFor(path, ['en']));

	const title = $derived(`Quotes on ${phrase} — Ochorus`);
	const description = $derived(
		topic.blurb ||
			`${total} quotations on ${phrase} from the classic Christian writers, each traced to its source.`
	);

	const crumbs = $derived([
		{ name: 'Home', href: '/' },
		{ name: 'Quotes', href: '/quotes/' },
		{ name: 'By topic', href: '/quotes/topics/' },
		{ name: topic.title, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));

	// An ItemList of Quotations across every author, in the order the page shows
	// them. `about` names the theme; each quote keeps its own author as creator.
	const listLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: `Quotes on ${phrase}`,
			description,
			url: canonical,
			mainEntity: {
				'@type': 'ItemList',
				numberOfItems: total,
				itemListElement: page.authors
					.flatMap((g) =>
						g.quotes.map((q) => ({
							text: q.text,
							author: g.author.name,
							authorSlug: g.author.slug
						}))
					)
					.map((q, i) => ({
						'@type': 'ListItem',
						position: i + 1,
						item: {
							'@type': 'Quotation',
							text: q.text,
							creator: {
								'@type': 'Person',
								name: q.author,
								'@id': `${SITE_URL}/authors/${q.authorSlug}/`
							}
						}
					}))
			}
		})
	);
</script>

<Seo {title} {description} {canonical} {hreflang} ogImage={absUrl('/og/quotes.png')} structuredData={[crumbsLd, listLd]} />

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<header class="mb-6">
		<h1 class="text-h1">Quotes on {phrase}</h1>
		{#if topic.blurb}
			<p class="mt-2 max-w-2xl text-body text-muted">{topic.blurb}</p>
		{/if}
		<ScriptureEpigraph text={topic.scripture_text} reference={topic.scripture_ref} />
		<p class="mt-3 text-small text-muted">
			{total} quotation{total === 1 ? '' : 's'} from {page.authors.length}
			writer{page.authors.length === 1 ? '' : 's'}, each traced to the exact paragraph it comes from.
		</p>
	</header>

	<!-- Jump row when there are several writers — the one structure a reader can
	     predict, the same pattern as the author page. -->
	{#if page.authors.length > 1}
		<nav class="jump" aria-label="Jump to a writer">
			{#each page.authors as g (g.author.slug)}
				<a href={`#a-${g.author.slug}`} style={`--hue: ${hueForBirthYear(g.author.birth_year)}`}
					>{g.author.name}</a
				>
			{/each}
		</nav>
	{/if}

	{#each page.authors as g (g.author.slug)}
		<section class="group" id={`a-${g.author.slug}`} style={`--hue: ${hueForBirthYear(g.author.birth_year)}`}>
			<h2 class="who">
				<!-- Link to the author's own theme page only when it was built (see
				     has_page); otherwise the name is plain, and their quotes still
				     sit right here. -->
				{#if g.has_page}
					<a href={authorTopicHref(g.author.slug, topic.slug)}>{g.author.name}</a>
				{:else}
					{g.author.name}
				{/if}
				<span class="count text-small font-normal">{g.count}</span>
			</h2>
			<ol class="quotes">
				{#each g.quotes as q (q.slug)}
					<QuoteCard quote={q} authorName={g.author.name} cite={citeLine(q)} />
				{/each}
			</ol>
		</section>
	{/each}

	<AccountCta action={`follow the writers on ${phrase}`} />
</div>

<style>
	/* Every use of --hue goes through color-mix(), never as body text, so
	   contrast holds in both themes (STYLE_GUIDE §5). Mirrors the author page. */
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
	.who {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
		margin: 0 0 0.9rem;
		padding-inline-start: 0.7rem;
		border-inline-start: 3px solid color-mix(in srgb, var(--hue) 55%, var(--color-border));
		font-size: var(--fs-h3);
		font-weight: 600;
	}
	.who a {
		color: inherit;
		text-decoration: none;
	}
	.who a:hover {
		text-decoration: underline;
	}

	.quotes {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.75rem;
	}
</style>
