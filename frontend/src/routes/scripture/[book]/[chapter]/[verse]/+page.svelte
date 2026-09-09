<script lang="ts">
	import type { ScripturePage } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, hreflangFor } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import CitingPassages from '$lib/components/CitingPassages.svelte';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	// English-only passage DATA; the chrome around it goes through the catalogues
	// (F3), as on the chapter page beside this one.
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
		{ name: t('common.home'), href: '/' },
		{ name: t('reader.scripture'), href: '/scripture' },
		{ name: `${page.book.title} ${page.chapter}`, href: chapterPath },
		{ name: page.reference, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
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
			{t('scripture.treated').replace('%count%', String(page.citing_count))}
		</p>
	</header>

	<section>
		<h2 class="section-label">{t('scripture.preachedHeading')}</h2>
		<CitingPassages passages={page.passages} />
		{#if page.citing_count > page.passages_shown}
			<p class="mt-3 text-small text-muted">
				{t('scripture.showingRest')
					.replace('%shown%', String(page.passages_shown))
					.replace('%total%', String(page.citing_count))}
			</p>
		{/if}
	</section>

	<p class="mt-8 text-small">
		<a class="text-accent hover:underline" href={chapterPath}
			>{t('scripture.allOf').replace('%reference%', `${page.book.title} ${page.chapter}`)}</a
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
