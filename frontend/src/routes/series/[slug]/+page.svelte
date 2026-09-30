<script lang="ts">
	import { onMount } from 'svelte';
	import * as m from '$lib/paraglide/messages.js';
	import { toBookTile, type SeriesDetail } from '$lib/library-public';
	import { bookProgressReader } from '$lib/progress';
	import { contentLang } from '$lib/reading';
	import { nextInSeries, seriesAges, seriesProgress, seriesProgressLabel } from '$lib/series';
	import { volumeNumeral } from '$lib/coverStyles';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumbLd, hreflangFor } from '$lib/seo';
	import { shareCard } from '$lib/coverArt';
	import { localizeHref } from '$lib/href';
	import BookCard from '$lib/components/BookCard.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import SeriesCard from '$lib/components/SeriesCard.svelte';
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
	const manyAuthors = $derived(new Set(series.books.map((b) => b.author.slug)).size > 1);
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
			? nextInSeries(series.books, bookProgressReader())
			: series.books.length
				? { book: series.books[0], resume: false }
				: null
	);
	const readCount = $derived(
		progressed ? seriesProgress(series.books.map((b) => b.slug), bookProgressReader()).done : 0
	);

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
		{ name: t('nav.series'), href: '/series/' },
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
	const ages = $derived(seriesAges(series));
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
				{t('nav.series')} · {volumeNumeral(count, lang) ?? count}
				{count === 1 ? t('common.bookOne') : t('common.bookMany')}
				{#if ages}· {ages}{/if}
			</p>
			<h1 class="text-h1 mb-2" dir="auto">{series.title}</h1>
			{#if series.description}
				<p class="mb-6 max-w-xl text-body text-muted" dir="auto">{series.description}</p>
			{/if}
		</div>
		<div class="hidden shrink-0 pt-1 sm:block">
			<CoverStrip
				covers={series.books.map(toBookTile)}
				max={5}
				size="lg"
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
				{seriesProgressLabel(readCount, count, lang)}
			</span>
		{/if}
	</div>

	<section class="mt-10">
		<h2 class="section-label mb-4">{t('nav.books')}</h2>
		<!-- The cover grid the shelves use. Each cover already carries its volume
		     numeral; the author rides the card only when the books have more than
		     one — The Key Teachings is a collection, but every volume is by Ochorus
		     Originals, and thirty cards saying so would be noise. -->
		<div class="book-grid">
			{#each series.books as book (book.slug)}
				<BookCard {book} showAuthor={manyAuthors} showSeries={false} />
			{/each}
		</div>
	</section>

	{#if data.others.length}
		<!-- The way on to the next series, and up to the index: the leaf page's
		     capped "More …" block, in the index's own (compact) card. -->
		<section class="mt-12">
			<div class="mb-4 flex items-baseline justify-between gap-3">
				<h2 class="section-label">{t('series.more')}</h2>
				<a href={localizeHref('/series/')} class="shrink-0 text-small font-medium">
					{t('series.seeAll')}
				</a>
			</div>
			<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-4">
				{#each data.others as s (s.slug)}
					<SeriesCard series={s} compact />
				{/each}
			</div>
		</section>
	{/if}
</div>
