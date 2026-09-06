<script lang="ts">
	import { type AuthorBio, type BookSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumbLd, hreflangAll } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { eraOf, eraById } from '$lib/eras';
	import AuthorBioCard from '$lib/components/AuthorBioCard.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Seo from '$lib/components/Seo.svelte';

	const t = i18n.t;

	let { data } = $props();
	const era = $derived(eraById(data.eraId)!);
	const authors = $derived<AuthorBio[]>(data.authors);
	const loadError = $derived<boolean>(data.loadError);
	const books = $derived<BookSummary[]>(data.books ?? []);

	// Group the library's books by author slug for the per-writer cover strips.
	const booksByAuthor = $derived.by(() => {
		const m = new Map<string, BookSummary[]>();
		for (const b of books) {
			const arr = m.get(b.author.slug);
			if (arr) arr.push(b);
			else m.set(b.author.slug, [b]);
		}
		return m;
	});

	// The "Full life" badge only carries information when full bios actually split
	// the roster — judged over the WHOLE locale, not this era's slice, so a card's
	// badge doesn't flicker between era pages. Mirrors the biographies index.
	const showFullLife = $derived.by(() => {
		if (!authors.length) return false;
		const share = authors.filter((a) => a.has_long_bio).length / authors.length;
		return share >= 0.05 && share <= 0.85;
	});

	// Writers in this era, earliest-born first (undated sink to the end) — the
	// same order the index uses inside an era group.
	const inEra = $derived(
		authors
			.filter((a) => eraOf(a.birth_year) === era.id)
			.sort(
				(a, b) => (a.birth_year ?? 9999) - (b.birth_year ?? 9999) || a.name.localeCompare(b.name)
			)
	);

	const path = $derived(`/biographies/era/${era.id}`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const eraName = $derived(t(era.k));
	const pageTitle = $derived(`${eraName} · ${t('bios.eyebrow')} — Ochorus`);

	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('bios.eyebrow'), href: '/biographies' },
		{ name: eraName, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));

	// CollectionPage whose mainEntity is the era's roster of Person entities —
	// the same shape as the biographies index, scoped to this era.
	const peopleLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: pageTitle,
			url: absUrl(localizeHref(path)),
			description: t('bios.metaDescription'),
			mainEntity: {
				'@type': 'ItemList',
				name: eraName,
				numberOfItems: inEra.length,
				itemListElement: inEra.map((a, i) => ({
					'@type': 'ListItem',
					position: i + 1,
					item: {
						'@type': 'Person',
						name: a.name,
						url: absUrl(localizeHref(`/authors/${a.slug}`)),
						image: a.photo_url ? absUrl(a.photo_url) : undefined,
						description: a.bio || undefined,
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
	description={t('bios.metaDescription')}
	{canonical}
	hreflang={hreflangAll(path)}
	ogImage="{SITE_URL}/og/biographies.png"
	structuredData={[peopleLd, crumbsLd]}
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />
	<header class="mb-8">
		<p class="eyebrow mb-2 text-accent">{t('bios.eyebrow')}</p>
		<h1 class="text-h1 mb-2 flex flex-wrap items-baseline gap-x-3">
			{eraName}
			{#if era.range}<span class="text-h3 font-normal text-muted">{era.range}</span>{/if}
		</h1>
		<p class="max-w-2xl text-body text-muted">{t('bios.tagline')}</p>
	</header>

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if inEra.length === 0}
		<EmptyState message={t('bios.noResults')} />
	{:else}
		<div class="grid items-start gap-5 md:grid-cols-2">
			{#each inEra as author (author.slug)}
				<AuthorBioCard {author} {showFullLife} shelf={booksByAuthor.get(author.slug) ?? []} />
			{/each}
		</div>
	{/if}

	<div class="mt-12 border-t border-border pt-6">
		<a
			href={localizeHref('/biographies')}
			class="text-small font-semibold text-accent hover:underline">← {t('bios.eyebrow')}</a
		>
	</div>
</div>
