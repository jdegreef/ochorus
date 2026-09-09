<script lang="ts">
	import type { QuoteTopicSummary } from '$lib/library-public';
	import { quoteTopicHref, onPhrase } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, hreflangFor, absUrl } from '$lib/seo';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import AccountCta from '$lib/components/AccountCta.svelte';
	import { i18n } from '$lib/i18n.svelte';

	// English literals, like the /quotes index it sits beside: what it lists is
	// not localized.
	let { data } = $props();
	const topics = $derived<QuoteTopicSummary[]>(data.topics);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	const path = '/quotes/topics/';
	const canonical = `${SITE_URL}${path}`;
	const hreflang = hreflangFor(path, ['en']);

	const title = 'Christian quotes by topic — Ochorus';
	const description =
		'The classic Christian writers on prayer, faith, grace, the Holy Spirit, suffering ' +
		'and more — memorable quotations gathered by theme, each traced to the book, chapter ' +
		'and paragraph it comes from, and free to read in full.';

	const crumbs = [
		{ name: 'Home', href: '/' },
		{ name: 'Quotes', href: '/quotes/' },
		{ name: 'By topic', href: path }
	];
	const crumbsLd = breadcrumbLd(crumbs);
	const listLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: 'Christian quotes by topic',
			description,
			url: canonical,
			hasPart: topics.map((tp) => ({
				'@type': 'CreativeWork',
				name: `Quotes on ${onPhrase(tp.title)}`,
				url: `${SITE_URL}${quoteTopicHref(tp.slug)}`
			}))
		})
	);
</script>

<Seo
	{title}
	{description}
	{canonical}
	{hreflang}
	ogImage={absUrl('/og/quotes.png')}
	structuredData={[crumbsLd, listLd]}
/>

<div class="page-col px-5 py-10">
	<PageHeader
		title="Quotes by topic"
		tagline="The lines these writers are remembered for, gathered by theme — prayer, faith, grace, the Holy Spirit and more. Each one traced to the exact book, chapter and paragraph it comes from, and linked to the full work."
	/>

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if topics.length === 0}
		<EmptyState message="No topics here yet." />
	{:else}
		<ul class="grid gap-3 sm:grid-cols-2">
			{#each topics as tp (tp.slug)}
				<li>
					<a
						href={quoteTopicHref(tp.slug)}
						class="block h-full rounded-card border border-border bg-surface p-4 hover:no-underline"
					>
						<span class="flex items-baseline justify-between gap-3">
							<span class="text-h3 text-text">{tp.title}</span>
							<span class="text-small text-muted">{tp.count}</span>
						</span>
						<span class="mt-1 block text-small text-muted">{tp.blurb}</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}

	<AccountCta />
</div>

<style>
	a:hover {
		border-color: color-mix(in srgb, var(--color-accent) 40%, var(--color-border));
	}
</style>
