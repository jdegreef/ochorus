<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import type { QuoteAuthorSummary, QuoteTopicSummary, SavedQuote } from '$lib/library-public';
	import { quoteTopicHref } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { hueForBirthYear } from '$lib/eras';
	import { initials, portraitPosition } from '$lib/portraits';
	import { jsonLd, breadcrumbLd, hreflangFor, absUrl } from '$lib/seo';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import AccountCta from '$lib/components/AccountCta.svelte';
	import QuoteText from '$lib/components/QuoteText.svelte';
	import TopicPill from '$lib/components/TopicPill.svelte';
	import FeaturedQuote from '$lib/components/FeaturedQuote.svelte';
	import { chapterSuffix } from '$lib/quoteSource';
	import { i18n } from '$lib/i18n.svelte';

	// English literals, as on the author pages and /scripture: this index is not
	// localized because what it lists is not.
	let { data } = $props();
	const authors = $derived<QuoteAuthorSummary[]>(data.authors);
	const featured = $derived<SavedQuote[]>(data.featured);
	const loadError = $derived<boolean>(data.loadError);
	// The first ten themes, in the API's curated order: all twenty stack eight
	// rows deep on a phone, pushing the writers off the first screen. The rest
	// sit one tap away behind "Browse quotes by topic".
	const TOPIC_CHIPS = 10;
	const topics = $derived<QuoteTopicSummary[]>(data.topics.slice(0, TOPIC_CHIPS));
	const t = i18n.t;

	const path = '/quotes/';
	const canonical = `${SITE_URL}${path}`;
	const hreflang = hreflangFor(path, ['en']);
	const total = $derived(authors.reduce((n, a) => n + a.count, 0));

	const title = 'Christian quotes, with their sources — Ochorus';
	const description =
		'Quotations from the classic Christian writers — Spurgeon, Andrew Murray, ' +
		'Thomas à Kempis, Augustine, John Wesley, Jonathan Edwards, E. M. Bounds — each ' +
		'one traced to the book, chapter and paragraph it comes from, and linked to the ' +
		'full text, free to read.';

	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.quotes'), href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
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

<Seo
	{title}
	{description}
	{canonical}
	{hreflang}
	ogImage={absUrl('/og/quotes.png')}
	structuredData={[crumbsLd, listLd]}
/>

<div class="page-col px-5 py-10">
	<!-- No visible breadcrumb: a top-level hub's only trail is Home > <this>
	     — Home is already the logo, <this> restates the H1 below, so it
	     carries nothing. The BreadcrumbList JSON-LD stays in the head; the
	     page's position is true even when we don't draw it. -->
	<PageHeader
		title={t('quotes.pageTitle')}
		tagline={t('quotes.tagline').replace('%count%', String(total))}
	/>

	<!-- One quotation first, fully cited: the thing the page promises. -->
	<FeaturedQuote pool={featured} start={data.featuredAt} />

	<!-- The other way in: by theme rather than by writer. A failed topics
	     fetch drops the chips and keeps the link. -->
	<nav class="mb-6" aria-label={t('quotes.byTopic')}>
		{#if topics.length}
			<ul class="mb-3 flex flex-wrap gap-2">
				{#each topics as tp (tp.slug)}
					<li>
						<TopicPill href={quoteTopicHref(tp.slug)} title={tp.title} count={tp.count} />
					</li>
				{/each}
			</ul>
		{/if}
		<a class="browse" href="/quotes/topics/">{t('quotes.browseByTopic')}</a>
	</nav>

	<!-- A card per author. The accent bar wears the author's era hue, the same
	     colour their row carries on the Biographies shelf and their quote page's
	     groups — one consistent visual key for "when". -->
	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if authors.length === 0}
		<EmptyState message={t('quotes.emptyIndex')} />
	{:else}
	<ul class="grid gap-3 sm:grid-cols-2">
		{#each authors as a (a.slug)}
			<li>
				<a
					href={`/quotes/${a.slug}/`}
					class="card-tint flex h-full items-center gap-4 rounded-card border border-border bg-surface p-4"
					style={`--hue: ${hueForBirthYear(a.birth_year)}`}
				>
					<span class="era-bar" aria-hidden="true"></span>
					{#if a.photo_url}
						<img
							src={a.photo_url}
							use:hydrateSrc={{ src: a.photo_url }}
							alt=""
							loading="lazy"
							width="96"
							height="96"
							class="h-14 w-14 shrink-0 rounded-full border border-border object-cover grayscale sm:h-16 sm:w-16"
							style="object-position: {portraitPosition(a.slug)}"
						/>
					{:else}
						<span
							class="font-display text-h3 flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-accent-soft font-semibold text-accent sm:h-16 sm:w-16"
						>
							{initials(a.name)}
						</span>
					{/if}
					<span class="min-w-0 flex-1">
						<span class="block text-h3 text-text">{a.name}</span>
						<span class="text-small text-muted">
							{(a.count === 1 ? t('quotes.countOne') : t('quotes.countMany')).replace(
								'%count%',
								String(a.count)
							)}{#if a.work_count > 0}
								· {(a.work_count === 1 ? t('quotes.worksOne') : t('quotes.worksMany')).replace(
									'%count%',
									String(a.work_count)
								)}{/if}
						</span>
						{#if a.teaser}
							<!-- A representative line — the author's shortest quote — turns
							     the directory into something to browse. It is the quotation
							     text itself (English, as on the author pages), so it is
							     printed as content, not a localized string; QuoteText repairs
							     the dashes and small caps the extraction flattened. Clamped to
							     two lines; the card's h-full keeps a row's two cards level. -->
							<span class="font-display text-small mt-1.5 line-clamp-2 italic text-muted"
								>“<QuoteText text={a.teaser} />”</span
							>
							{#if a.teaser_source}
								<!-- The teaser's citation — the promise the tagline makes. -->
								<span class="mt-0.5 block text-eyebrow text-muted"
									>— <cite class="italic">{a.teaser_source.work}</cite>{chapterSuffix(
										a.teaser_source.order
									)}</span
								>
							{/if}
						{/if}
					</span>
					<span class="text-muted"><Arrow /></span>
				</a>
			</li>
		{/each}
	</ul>
	{/if}

	<AccountCta />
</div>

<style>
	/* --hue is the era's hex (eras.ts); every use goes through color-mix, never
	   raw, the same rule the author quote page states. */
	.browse {
		color: var(--color-accent);
		text-decoration: none;
		font-size: var(--fs-small);
	}
	.browse:hover {
		text-decoration: underline;
	}
	.era-bar {
		width: 0.375rem;
		align-self: stretch;
		min-height: 2.5rem;
		border-radius: 999px;
		background: color-mix(in srgb, var(--hue) 60%, var(--color-surface));
	}
	/* Era-hue member of the row-tint recipe (like .sermon-row): the shared
	   .card-tint carries the motion; the hover border and ground are the era's
	   own hue rather than the neutral accent/surface-2. Scoped to .card-tint (not
	   a bare `a:hover`) so it can't reach the "Browse by topic" link, and so the
	   scoped rule outspecifies the global .card-tint:hover it overrides. */
	.card-tint:hover {
		border-color: color-mix(in srgb, var(--hue) 45%, var(--color-border));
		background: color-mix(in srgb, var(--hue) 4%, var(--color-surface));
	}
</style>
