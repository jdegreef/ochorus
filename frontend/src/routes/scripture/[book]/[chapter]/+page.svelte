<script lang="ts">
	import type { ScripturePage } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, hreflangFor } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import CitingPassages from '$lib/components/CitingPassages.svelte';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	// The passage DATA is English-only (citations are extracted against
	// pythonbible's English book names, so a scripture page can only exist in
	// English). The CHROME around it — crumbs, counters, section labels — now
	// goes through the message catalogues (F3), filled for every advertised
	// locale so the completeness gate stays green. Reference labels
	// (`page.reference`, book titles) stay as the data provides them.
	let { data } = $props();
	const page = $derived<ScripturePage>(data.page);
	// Adjacent qualifying chapter pages, in canonical Bible order (computed in
	// +page.ts) — walk the reverse index without returning to the hub.
	const prev = $derived(data.prev);
	const next = $derived(data.next);

	const path = $derived(`/scripture/${page.book.slug}/${page.chapter}/`);
	const canonical = $derived(`${SITE_URL}${path}`);
	// Only `en` is offered as an alternate — advertising the other locales would
	// point search engines at pages that do not exist.
	const hreflang = $derived(hreflangFor(path, ['en']));

	const title = $derived(`${page.reference} — what the classics say — Ochorus`);
	const description = $derived(
		`${page.citing_count} passage${page.citing_count === 1 ? '' : 's'} from the ` +
			`Christian classics that treat ${page.reference}, each quoted and linked to its source.`
	);

	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('reader.scripture'), href: '/scripture' },
		{ name: page.reference, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
	// Each excerpt is a Quotation tied to the work it came from — the markup
	// that says these are sourced passages rather than a page of loose text.
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
		<p class="mt-2 text-small text-muted">
			{t('scripture.treated').replace('%count%', String(page.citing_count))}
		</p>
	</header>

	{#if page.verses?.length}
		<section class="mb-10">
			<h2 class="section-label">{t('scripture.versesHeading')}</h2>
			<ul class="verses">
				{#each page.verses as v (v.number)}
					<li class="verse">
						<!-- Linked only when the verse cleared the verse floor and has a
						     page. Linking every cited verse killed the build on
						     /scripture/genesis/1/27/ — cited, but under the floor, so the
						     page was deliberately never built. -->
						{#if v.has_page}
							<a href={`/scripture/${page.book.slug}/${page.chapter}/${v.number}/`}>
								<span class="num">{page.chapter}:{v.number}</span>
								<span class="vtext">{v.text}</span>
							</a>
						{:else}
							<span class="unlinked">
								<span class="num">{page.chapter}:{v.number}</span>
								<span class="vtext">{v.text}</span>
							</span>
						{/if}
						<span class="count text-small">{v.citing_count}</span>
					</li>
				{/each}
			</ul>
			<p class="mt-2 text-small text-muted">{page.version}</p>
		</section>
	{/if}

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

	<!-- Walk the reverse index in canonical order (adjacent qualifying pages). -->
	{#if prev || next}
		<nav class="mt-12 flex items-stretch justify-between gap-3 border-t border-border pt-6">
			{#if prev}
				<a href={prev.href} class="btn btn-ghost flex-1 flex-col items-start gap-0.5 text-start">
					<span class="eyebrow text-muted">{t('reader.previous')}</span>
					<span class="text-small">{prev.label}</span>
				</a>
			{:else}
				<span class="flex-1"></span>
			{/if}
			{#if next}
				<a href={next.href} class="btn btn-ghost flex-1 flex-col items-end gap-0.5 text-end">
					<span class="eyebrow text-muted">{t('reader.next')}</span>
					<span class="text-small">{next.label}</span>
				</a>
			{:else}
				<span class="flex-1"></span>
			{/if}
		</nav>
	{/if}
</div>

<style>
	.verses {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.4rem;
	}
	.verse {
		display: flex;
		align-items: baseline;
		gap: 0.75rem;
		padding: 0.55rem 0.8rem;
		border-radius: var(--radius-card);
		background: var(--color-surface-2);
	}
	.verse a,
	.verse .unlinked {
		flex: 1;
		color: inherit;
		text-decoration: none;
		display: flex;
		gap: 0.6rem;
		align-items: baseline;
	}
	.verse a:hover .vtext {
		text-decoration: underline;
	}
	.num {
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
		color: var(--color-accent);
	}
	.vtext {
		font-size: var(--fs-small);
		line-height: 1.55;
	}
	/* How many chapters treat this verse — the reason it earned its own page. */

</style>
