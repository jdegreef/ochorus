<script lang="ts">
	import { onMount } from 'svelte';
	import type { AudienceShelf, BookSummary, SeriesSummary } from '$lib/library-public';
	import { hubBooks } from '$lib/audienceHub';
	import { allProgress, bookProgressReader, bookReadTimes } from '$lib/progress';
	import { resumeOrderOf } from '$lib/reading-schema';
	import { chapterPath } from '$lib/editionHref';
	import {
		seriesCardProgressLabel,
		seriesToContinue,
		splitSeriesTitle,
		type BookStage
	} from '$lib/series';
	import { seriesMeta } from '$lib/emblemNames';
	import { contentLang } from '$lib/reading';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import ContinueShelf from './ContinueShelf.svelte';
	import ContinueRow from './ContinueRow.svelte';
	import SeriesSegments from './SeriesSegments.svelte';
	import BookCover from './BookCover.svelte';
	import ProgressBar from './ProgressBar.svelte';

	/**
	 * A returning reader's way back in, at the top of a young-reader hub: the
	 * hub's series they are partway through (the /series index's rows) and its
	 * loose books they have open (the /books shelf's rows), most recently read
	 * first, three at most. Device-local progress, read after mount and on
	 * `ochorus:sync` — a first visit, and the prerendered page, draw nothing.
	 * `exclude` is the series the challenge band already tracks.
	 */
	let { shelf, exclude }: { shelf: AudienceShelf; exclude?: string } = $props();
	const t = i18n.t;

	let ticks = $state(0);
	onMount(() => {
		const bump = () => ticks++;
		bump();
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	type Row =
		| { kind: 'series'; key: string; at: number; series: SeriesSummary; slug: string; stages: BookStage[] }
		| { kind: 'book'; key: string; at: number; book: BookSummary; order: number };

	const rows = $derived.by((): Row[] => {
		if (!ticks) return [];
		const times = bookReadTimes();
		const series: Row[] = seriesToContinue(
			shelf.series.filter((s) => s.slug !== exclude),
			bookProgressReader(),
			times
		).map((r) => ({
			kind: 'series',
			key: `series:${r.series.slug}`,
			at: Math.max(...(r.series.books ?? []).map(times)),
			...r
		}));
		const bySlug = new Map(hubBooks(shelf).map((b) => [b.slug, b]));
		const books: Row[] = allProgress()
			.filter((p) => p.kind === 'book' && p.finished_at == null && bySlug.has(p.slug))
			.map((p) => ({
				kind: 'book',
				key: `book:${p.slug}`,
				at: p.at,
				book: bySlug.get(p.slug)!,
				order: resumeOrderOf(p)
			}));
		return [...series, ...books].sort((a, b) => b.at - a.at).slice(0, 3);
	});
	const lang = $derived(contentLang(getLang()));
</script>

{#if rows.length}
	<ContinueShelf heading={t('books.continue')}>
		{#each rows as row (row.key)}
			{#if row.kind === 'series'}
				{@const meta = seriesMeta(row.series.slug)}
				{@const label = seriesCardProgressLabel(row.stages, lang)}
				<ContinueRow
					href={localizeHref(`/books/${row.slug}`)}
					title={splitSeriesTitle(row.series.title).name}
					caption={label}
					verb={t('plans.continue')}
					hue={meta.accent}
					emblem={meta.emblem}
				>
					{#snippet progress()}
						<SeriesSegments stages={row.stages} {label} />
					{/snippet}
				</ContinueRow>
			{:else}
				{@const of = row.book.chapter_count}
				{@const caption = `${t('continue.chapter')} ${row.order} ${t('plans.of')} ${of}`}
				<ContinueRow
					href={localizeHref(chapterPath(row.book.slug, row.order, row.book.has_modern_edition))}
					title={row.book.title}
					{caption}
					verb={t('plans.continue')}
				>
					{#snippet visual()}
						<span class="w-10 shrink-0"><BookCover book={row.book} /></span>
					{/snippet}
					{#snippet progress()}
						<ProgressBar percent={((row.order - 1) / of) * 100} label={`${row.book.title}: ${caption}`} />
					{/snippet}
				</ContinueRow>
			{/if}
		{/each}
	</ContinueShelf>
{/if}
