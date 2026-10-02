<script lang="ts">
	import { onMount } from 'svelte';
	import type { SeriesSummary } from '$lib/library-public';
	import { bookProgressReader } from '$lib/progress';
	import {
		nextInSeries,
		seriesCardProgressLabel,
		seriesProgress,
		splitSeriesTitle,
		cardLanguages
	} from '$lib/series';
	import { contentLang } from '$lib/reading';
	import { getLang, localeName } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { seriesMeta } from '$lib/emblemNames';
	import { seriesAges } from '$lib/series';
	import SeriesSegments from './SeriesSegments.svelte';
	import ShelfCard from './ShelfCard.svelte';

	/**
	 * A book series as a browse card — the Topics/Plans `ShelfCard`, so the
	 * /series index reads as a sibling of those two shelves, and the Books page's
	 * Book Series rail shows the same card a reader then meets on the index.
	 * `compact` is the rail's form: no description, and an <h3> title because
	 * the rail sits under its own "Book Series" <h2>; the index's cards sit
	 * directly under the page <h1>.
	 */
	let {
		series,
		compact = false,
		headingLevel = compact ? 3 : 2
	}: {
		series: SeriesSummary;
		compact?: boolean;
		/** Overrides the level `compact` implies — the index's full cards sit
		 *  under an audience <h2>, so they title themselves <h3>. */
		headingLevel?: 2 | 3;
	} = $props();
	const t = i18n.t;
	const meta = $derived(seriesMeta(series.slug));

	// The reader's progress through the series, read after mount: it lives in
	// localStorage, and the prerendered card must not bake one visitor's place
	// into every page. Read again on `ochorus:sync`, when an account's progress
	// lands after the page did. Drawn only once a book of the series is begun,
	// as one segment per book — an empty bar over "0 of 4 read" told a reader
	// halfway through book one that they had done nothing.
	let ticks = $state(0);
	onMount(() => {
		const bump = () => ticks++;
		bump();
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});
	// One parse of the progress map per read, shared by the meter and the button.
	const progressOf = $derived(ticks ? bookProgressReader() : null);
	const progress = $derived(
		progressOf && series.books ? seriesProgress(series.books, progressOf) : null
	);
	const progressLabel = $derived(
		progress ? seriesCardProgressLabel(progress.stages, contentLang(getLang())) : ''
	);
	const ages = $derived(seriesAges(series));
	// The languages the series can be read in, the reader's own first: a
	// multilingual library's best fact about a series, and already in the list
	// payload (for hreflang). Only drawn when there is more than one, and capped
	// so a ten-language series stays one line.
	const langs = $derived(cardLanguages(series.languages ?? [], getLang()));
	// The card's own way in (the full card only; the rail stays compact): the
	// book to open next, as the series page's button picks it — the first book
	// until mount, then the book in progress or the first unfinished — or, once
	// every book is read, a line saying so (the foot stays, so the card keeps
	// one shape from prerender to mount). Its title comes from the fan's tiles,
	// which cover the first four books; past those the verb stands alone.
	const slugs = $derived(series.books ?? []);
	const hasAction = $derived(!compact && slugs.length > 0);
	const next = $derived.by(() => {
		if (!hasAction) return null;
		const books = slugs.map((slug) => ({ slug }));
		return progressOf ? nextInSeries(books, progressOf) : { book: books[0], resume: false };
	});
	// "Continue" for any book past the first: a reader sent to volume 5 is
	// carrying on with the series, not beginning it.
	const continuing = $derived(!!next && (next.resume || next.book.slug !== slugs[0]));
	const nextTitle = $derived(
		next ? (series.covers.find((c) => c.slug === next.book.slug)?.title ?? '') : ''
	);
	// "Rooted – 30 Days with God for Youth" as a name over a subtitle, so the
	// title stays short enough to sit level with the count beside it.
	const heading = $derived(splitSeriesTitle(series.title));
</script>

<ShelfCard
	href={localizeHref(`/series/${series.slug}/`)}
	hue={meta.accent}
	emblem={meta.emblem}
	covers={series.covers}
	title={heading.name}
	subtitle={heading.subtitle}
	{headingLevel}
	action={hasAction ? nextAction : undefined}
>
	{#snippet aside()}
		{series.book_count}
		{series.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
	{/snippet}
	{#if ages}
		<!-- Ink, not accent: the whole card is one link, and an indigo line
		     inside it read as a second one that went nowhere. -->
		<p class="mt-0.5 text-small font-medium text-text">{ages}</p>
	{/if}
	{#if !compact && langs.shown.length}
		<p class="mt-1.5 flex flex-wrap items-center gap-1" dir="ltr">
			<span class="sr-only">{t('footer.languages')}:</span>
			{#each langs.shown as code (code)}
				<abbr class="lang-code" title={localeName(code)} lang={code}>{code.toUpperCase()}</abbr>
			{/each}
			{#if langs.more}<span class="lang-code">+{langs.more}</span>{/if}
		</p>
	{/if}
	{#if !compact && series.description}
		<p class="shelf-card-desc series-desc mt-1.5 text-small text-muted" dir="auto">
			{series.description}
		</p>
	{/if}
	{#if progress?.started}
		<!-- mt-auto: with the body's flex:1 this sits on the card's floor, so a
		     row of cards keeps its meters level. -->
		<div class="mt-auto flex flex-col gap-1.5 pt-3">
			<SeriesSegments stages={progress.stages} label={progressLabel} />
			<span class="text-small text-muted">{progressLabel}</span>
		</div>
	{/if}
</ShelfCard>

{#snippet nextAction()}
	{#if next}
		<a class="btn btn-sm btn-ghost max-w-full" href={localizeHref(`/books/${next.book.slug}`)}>
			{#if continuing}
				{t('plans.continue')}
			{:else if nextTitle}
				{t('author.startWith')}
			{:else}
				{t('book.beginReading')}
			{/if}
			{#if nextTitle}<span class="truncate" dir="auto">{nextTitle}</span>{/if}
		</a>
	{:else}
		<p class="text-small text-muted">{t('series.allRead')}</p>
	{/if}
{/snippet}


<style>
	/* Five lines, not the shelf's three: series blurbs run to ~210 characters
	   in English (longer in translation), and at three a three-up grid cut
	   Sons of the King off mid-word. Still a clamp, so no blurb sets a row. */
	/* A language code: a quiet bordered tag, not a link (the card is one). */
	.lang-code {
		border: 1px solid var(--border);
		border-radius: 0.25rem;
		padding: 0 0.3rem;
		font-size: var(--fs-micro);
		font-weight: 600;
		letter-spacing: 0.04em;
		color: var(--muted);
		text-decoration: none;
	}
	.series-desc {
		-webkit-line-clamp: 5;
		line-clamp: 5;
	}
</style>
