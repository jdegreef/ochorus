<script lang="ts">
	import { onMount } from 'svelte';
	import type { SeriesSummary } from '$lib/library-public';
	import { bookProgressReader, bookReadTimes } from '$lib/progress';
	import {
		seriesCardProgressLabel,
		seriesToContinue,
		splitSeriesTitle
	} from '$lib/series';
	import { contentLang } from '$lib/reading';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { seriesMeta } from '$lib/emblemNames';
	import SeriesSegments from './SeriesSegments.svelte';
	import ContinueShelf from './ContinueShelf.svelte';
	import ContinueRow from './ContinueRow.svelte';

	/**
	 * The /series index's "Continue your series": up to three series the reader
	 * is partway through, most recently read first, each one tap from the book
	 * to open next. Read after mount — progress lives in localStorage, and the
	 * prerendered index must not bake one visitor's place into every page — so
	 * a first-time reader never sees the section at all — and again on
	 * `ochorus:sync`, when an account's progress lands after the page did.
	 */
	let { series }: { series: SeriesSummary[] } = $props();
	const t = i18n.t;

	let ticks = $state(0);
	onMount(() => {
		const bump = () => ticks++;
		bump();
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});
	const rows = $derived(
		ticks ? seriesToContinue(series, bookProgressReader(), bookReadTimes()) : []
	);
	const lang = $derived(contentLang(getLang()));
</script>

{#if rows.length}
	<ContinueShelf heading={t('series.continueHeading')}>
		{#each rows as row (row.series.slug)}
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
		{/each}
	</ContinueShelf>
{/if}

