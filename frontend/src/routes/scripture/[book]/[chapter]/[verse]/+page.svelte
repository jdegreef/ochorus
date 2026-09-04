<script lang="ts">
	import type { ScripturePage } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumb, hreflangFor } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import CitingPassages from '$lib/components/CitingPassages.svelte';

	// English-only, and written in English literals for the reason spelled out
	// on the chapter page beside this one.
	let { data } = $props();
	const page = $derived<ScripturePage>(data.page);

	const chapterPath = $derived(`/scripture/${page.book.slug}/${page.chapter}/`);
	const path = $derived(`${chapterPath}${page.verse}/`);
	const canonical = $derived(`${SITE_URL}${path}`);
	const hreflang = $derived(hreflangFor(path, ['en']));

	const title = $derived(`${page.reference} — what the classics say — Ochorus`);
	const description = $derived(
		`${page.citing_count} passage${page.citing_count === 1 ? '' : 's'} from the ` +
			`Christian classics on ${page.reference}, each quoted and linked to its source.`
	);

	const crumbs = $derived([
		{ name: 'Home', href: '/' },
		{ name: 'Scripture', href: '/scripture' },
		{ name: `${page.book.title} ${page.chapter}`, href: chapterPath },
		{ name: page.reference, href: path }
	]);
	const crumbsLd = $derived(
		jsonLd(breadcrumb(crumbs.map((c) => ({ name: c.name, url: c.href }))))
	);
	const quotesLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: `${page.reference} in the Christian classics`,
			description,
			url: canonical,
			hasPart: page.passages.slice(0, 40).map((p) => ({
				'@type': 'Quotation',
				spokenByCharacter: p.author_name,
				isPartOf: { '@type': 'Book', name: p.book_title },
				url: `${SITE_URL}/books/${p.book_slug}/${p.chapter_order}/`
			}))
		})
	);
</script>

<Seo
	{title}
	{description}
	{canonical}
	{hreflang}
	structuredData={[crumbsLd, quotesLd]}
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<header class="mb-8">
		<h1 class="text-h1">{page.reference}</h1>
		{#if page.text}
			<blockquote class="verse">
				{page.text}
				<footer class="attrib">{page.version}</footer>
			</blockquote>
		{/if}
		<p class="mt-3 text-small text-muted">
			Treated in {page.citing_count}
			{page.citing_count === 1 ? 'passage' : 'passages'} across the library.
		</p>
	</header>

	<section>
		<h2 class="section-label">Where it is preached</h2>
		<CitingPassages passages={page.passages} />
		{#if page.citing_count > page.passages_shown}
			<p class="mt-3 text-small text-muted">
				Showing {page.passages_shown} of {page.citing_count}; the rest are reachable through
				search.
			</p>
		{/if}
	</section>

	<p class="mt-8 text-small">
		<a class="text-accent hover:underline" href={chapterPath}
			>All of {page.book.title}
			{page.chapter} →</a
		>
	</p>
</div>

<style>
	/* Logical inline-start, not a physical side, so the rule stays on the reading
	   edge if this page is ever served under an RTL locale. (Spelling the
	   physical property here would trip rtl.test.ts, which scans style blocks
	   line by line and does not strip comments — see the same note on
	   topics/[slug].) */
	.verse {
		margin: 1rem 0 0;
		padding-inline-start: 1rem;
		border-inline-start: 3px solid var(--color-accent);
		font-family: var(--font-display, Georgia, serif);
		font-size: var(--fs-body);
		line-height: 1.6;
		color: var(--color-text);
	}
	.attrib {
		margin-top: 0.4rem;
		font-family: var(--font-sans, system-ui, sans-serif);
		font-size: var(--fs-small);
		font-style: normal;
		color: var(--color-muted);
	}
</style>
