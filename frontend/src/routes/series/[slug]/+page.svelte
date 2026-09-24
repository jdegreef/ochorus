<script lang="ts">
	import { onMount } from 'svelte';
	import * as m from '$lib/paraglide/messages.js';
	import type { SeriesDetail } from '$lib/library-public';
	import { getProgress, isFinished } from '$lib/progress';
	import { contentLang } from '$lib/reading';
	import { nextInSeries } from '$lib/series';
	import { volumeNumeral } from '$lib/coverStyles';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumbLd, hreflangFor } from '$lib/seo';
	import { shareCard } from '$lib/coverArt';
	import { localizeHref } from '$lib/href';
	import BookCard from '$lib/components/BookCard.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';

	/**
	 * A series page: the volumes of one series in reading order (Brave for God,
	 * Rooted), or the books of a collection (The Key Teachings). A leaf page on
	 * the plan page's anatomy — a plan is the other ordered run of books — with
	 * one action that knows where the reader is in the series.
	 */
	let { data } = $props();
	const t = i18n.t;
	const series = $derived(data.series as SeriesDetail);
	const lang = $derived(contentLang(getLang()));

	// Where the reader is, read after mount: progress lives in localStorage, and
	// the prerendered HTML must not bake one visitor's place into every page.
	// Until then the action is the plain "start with the first book".
	let progressed = $state(false);
	onMount(() => {
		progressed = true;
	});
	const next = $derived(
		progressed
			? nextInSeries(series.books, (slug) => ({
					started: getProgress(slug) != null,
					finished: isFinished(slug)
				}))
			: series.books.length
				? { book: series.books[0], resume: false }
				: null
	);
	const readCount = $derived(progressed ? series.books.filter((b) => isFinished(b.slug)).length : 0);

	const path = $derived(`/series/${series.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const hreflang = $derived(hreflangFor(path, series.available_languages));
	// The first volume's share card stands in for the series: it is the cover a
	// reader meets first, and the series has no artwork of its own yet.
	const share = $derived(series.books[0] ? shareCard(series.books[0]) : null);
	const ogImage = $derived(absUrl(share?.url ?? '/og/books.png'));
	const description = $derived(
		series.description || m.series_meta_default({ series: series.title })
	);
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.books'), href: '/books' },
		{ name: series.title, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
	// schema.org's own type for this: a BookSeries whose parts are its volumes.
	const seriesLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'BookSeries',
			name: series.title,
			description,
			url: canonical,
			inLanguage: getLang(),
			hasPart: series.books.map((b) => ({
				'@type': 'Book',
				name: b.title,
				author: { '@type': 'Person', name: b.author.name },
				url: `${SITE_URL}${localizeHref(`/books/${b.slug}`)}`,
				...(b.series_position ? { position: b.series_position } : {})
			}))
		})
	);
	const count = $derived(series.books.length);
</script>

<Seo
	title="{series.title} — Ochorus"
	{description}
	{canonical}
	{hreflang}
	{ogImage}
	ogImageWidth={share?.width}
	ogImageHeight={share?.height}
	structuredData={[seriesLd, crumbsLd]}
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<div class="flex items-start justify-between gap-4">
		<div class="min-w-0 flex-1">
			<p class="eyebrow mb-1 text-muted">
				{t('series.kind')} · {volumeNumeral(count, lang) ?? count}
				{count === 1 ? t('common.bookOne') : t('common.bookMany')}
			</p>
			<h1 class="text-h1 mb-2" dir="auto">{series.title}</h1>
			{#if series.description}
				<p class="mb-6 max-w-xl text-body text-muted" dir="auto">{series.description}</p>
			{/if}
		</div>
		<div class="hidden shrink-0 pt-1 sm:block">
			<CoverStrip
				covers={series.books.map((b) => ({
					kind: 'book' as const,
					slug: b.slug,
					title: b.title,
					cover_url: b.cover_url,
					cover_color: b.cover_color
				}))}
				max={5}
			/>
		</div>
	</div>

	<div class="mt-2 flex flex-wrap items-center gap-3">
		{#if next}
			<a href={localizeHref(`/books/${next.book.slug}`)} class="btn btn-primary">
				{next.resume ? t('plans.continue') : t('author.startWith')}
				<span dir="auto">{next.book.title}</span>
			</a>
		{:else}
			<!-- A status line, not a control: nothing is left to start. -->
			<p class="text-small font-medium text-muted">{t('series.allRead')}</p>
		{/if}
		<ShareButton url={canonical} title={series.title} showLabel />
		{#if readCount && next}
			<span class="text-small text-muted">
				{m.series_progress({
					done: volumeNumeral(readCount, lang) ?? String(readCount),
					total: volumeNumeral(count, lang) ?? String(count)
				})}
			</span>
		{/if}
	</div>

	<section class="mt-10">
		<h2 class="section-label mb-4">{t('nav.books')}</h2>
		<!-- The cover grid the shelves use. Each cover already carries its volume
		     numeral; the author rides the card because a collection spans authors. -->
		<div class="book-grid">
			{#each series.books as book (book.slug)}
				<BookCard {book} showAuthor={!series.ordered} />
			{/each}
		</div>
	</section>
</div>
