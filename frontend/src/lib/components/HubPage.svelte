<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import AuthorBioCard from '$lib/components/AuthorBioCard.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import QandA from '$lib/components/QandA.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { SITE_URL } from '$lib/config';
	import { localizeHref } from '$lib/href';
	import { hubPath, hubShelf, hubWriters, relatedPlaces } from '$lib/hubs';
	import { i18n } from '$lib/i18n.svelte';
	import {
		fullLifeDiscriminates,
		type AuthorBio,
		type BookSummary,
		type Hub
	} from '$lib/library-public';
	import { absUrl, breadcrumbLd, hreflangFor, jsonLd, pickQa } from '$lib/seo';

	const t = i18n.t;

	/**
	 * A biography hub — the writers of one tradition or place (`$lib/hubs`).
	 * The era page's anatomy (breadcrumb, composite head, AuthorBioCard grid)
	 * plus the hub's own intro, a starter shelf, Q&A and links to its
	 * neighbours. Both hub routes render this; they differ only in which kinds
	 * they accept.
	 */
	let {
		hub,
		hubs,
		authors,
		books,
		loadError
	}: {
		hub: Hub;
		hubs: Hub[];
		authors: AuthorBio[];
		books: BookSummary[];
		loadError: boolean;
	} = $props();

	const writers = $derived(hubWriters(hub, authors));
	const bookCount = $derived(writers.reduce((n, w) => n + w.book_count, 0));
	const booksByAuthor = $derived.by(() => {
		const m = new Map<string, BookSummary[]>();
		for (const b of books) m.set(b.author.slug, [...(m.get(b.author.slug) ?? []), b]);
		return m;
	});
	const shelf = $derived(hubShelf(writers, books));
	// Judged over the whole roster, as the biographies index and the era pages do.
	const showFullLife = $derived(fullLifeDiscriminates(authors));
	const span = $derived.by(() => {
		const born = writers.map((w) => w.birth_year).filter((y): y is number => y != null);
		const died = writers.map((w) => w.death_year).filter((y): y is number => y != null);
		return born.length && died.length ? `${Math.min(...born)}–${Math.max(...died)}` : '';
	});
	// Neighbours: a place's region and sibling places, a region's places, and
	// for a tradition the other traditions.
	const related = $derived(
		hub.kind === 'tradition'
			? hubs.filter((h) => h.kind === 'tradition' && h.slug !== hub.slug)
			: relatedPlaces(hub, hubs)
	);

	const path = $derived(hubPath(hub));
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const pageTitle = $derived(`${hub.name} — Ochorus`);
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('bios.eyebrow'), href: '/biographies' },
		{ name: hub.name, href: path }
	]);
	const qa = $derived(pickQa(hub.qa, []));
	// CollectionPage over the hub's Person roster — the era pages' shape.
	const peopleLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: hub.name,
			url: absUrl(localizeHref(path)),
			description: hub.intro,
			mainEntity: {
				'@type': 'ItemList',
				name: hub.name,
				numberOfItems: writers.length,
				itemListElement: writers.map((a, i) => ({
					'@type': 'ListItem',
					position: i + 1,
					item: {
						'@type': 'Person',
						name: a.name,
						url: absUrl(localizeHref(`/authors/${a.slug}`)),
						image: a.photo_url ? absUrl(a.photo_url) : undefined,
						birthDate: a.birth_year ? String(a.birth_year) : undefined,
						deathDate: a.death_year ? String(a.death_year) : undefined
					}
				}))
			}
		})
	);
</script>

<Seo
	title={pageTitle}
	description={hub.intro}
	{canonical}
	hreflang={hreflangFor(path, hub.available_languages)}
	ogImage="{SITE_URL}/og/biographies.png"
	structuredData={[peopleLd, breadcrumbLd(crumbs), qa.ld].filter(Boolean)}
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<header class="mb-8">
		<p class="eyebrow mb-2 text-accent">{t('bios.eyebrow')}</p>
		<h1 class="text-h1 mb-2 flex flex-wrap items-baseline gap-x-3">
			{hub.name}
			{#if span}<span class="text-h3 font-normal text-muted">{span}</span>{/if}
		</h1>
		{#if writers.length}
			<p class="mb-3 text-small text-muted">
				<span class="whitespace-nowrap"
					>{writers.length} {writers.length === 1 ? t('common.authorOne') : t('common.authorMany')}</span
				>{#if bookCount}{' · '}<span class="whitespace-nowrap"
						>{bookCount} {bookCount === 1 ? t('common.bookOne') : t('common.bookMany')}</span
					>{/if}
			</p>
		{/if}
		<p class="max-w-2xl text-body text-muted">{hub.intro}</p>
	</header>

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if writers.length === 0}
		<EmptyState message={t('bios.noResults')} />
	{:else}
		<section aria-labelledby="hub-writers">
			<h2 id="hub-writers" class="section-heading">{t('hubs.writers')}</h2>
			<div class="grid items-start gap-5 md:grid-cols-2">
				{#each writers as author (author.slug)}
					<AuthorBioCard {author} {showFullLife} shelf={booksByAuthor.get(author.slug) ?? []} />
				{/each}
			</div>
		</section>

		{#if shelf.length > 1}
			<section class="mt-12" aria-labelledby="hub-start">
				<h2 id="hub-start" class="section-heading">{t('hubs.startReading')}</h2>
				<div class="book-grid">
					{#each shelf as book (book.slug)}
						<BookCard {book} showAuthor />
					{/each}
				</div>
			</section>
		{/if}
	{/if}

	<QandA items={qa.items} title={t('qa.sectionTitle')} headingClass="section-heading" />

	{#if related.length}
		<section class="mt-12" aria-labelledby="hub-related">
			<h2 id="hub-related" class="section-label mb-3">{t('hubs.alsoBrowse')}</h2>
			<ul class="flex flex-wrap gap-2">
				{#each related as h (h.slug)}
					<li><a class="tag" href={localizeHref(hubPath(h))}>{h.name}</a></li>
				{/each}
			</ul>
		</section>
	{/if}

	<div class="mt-12 border-t border-border pt-6">
		<a
			href={localizeHref('/biographies')}
			class="text-small font-semibold text-accent hover:underline"><Arrow back /> {t('bios.eyebrow')}</a
		>
	</div>
</div>
