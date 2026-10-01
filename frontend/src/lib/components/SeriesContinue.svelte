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
	import Emblem from './Emblem.svelte';
	import SeriesSegments from './SeriesSegments.svelte';

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
	<section class="mb-12">
		<h2 class="section-label mb-4">{t('series.continueHeading')}</h2>
		<ul class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
			{#each rows as row (row.series.slug)}
				{@const meta = seriesMeta(row.series.slug)}
				{@const label = seriesCardProgressLabel(row.stages, lang)}
				<li>
					<a
						class="continue-row card-tint"
						style="--shelf-hue: {meta.accent}"
						href={localizeHref(`/books/${row.slug}`)}
					>
						<span class="emblem-chip continue-chip"><Emblem name={meta.emblem} /></span>
						<span class="flex min-w-0 flex-1 flex-col gap-1.5">
							<span class="continue-title truncate" dir="auto">
								{splitSeriesTitle(row.series.title).name}
							</span>
							<SeriesSegments stages={row.stages} {label} />
							<span class="text-small text-muted">{label}</span>
						</span>
						<span class="btn btn-sm btn-primary shrink-0">{t('plans.continue')}</span>
					</a>
				</li>
			{/each}
		</ul>
	</section>
{/if}

<style>
	.continue-row {
		display: flex;
		align-items: center;
		gap: 0.85rem;
		height: 100%;
		padding: 0.85rem 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		color: inherit;
		text-decoration: none;
	}
	.continue-chip {
		--chip-size: 2.75rem;
		--chip-hue: var(--shelf-hue);
	}
	.continue-title {
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--text);
	}
</style>
