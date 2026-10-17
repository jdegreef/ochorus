<script lang="ts">
	import { onMount } from 'svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { downloadFile } from '$lib/dataExport';
	import type { ForChrome } from '$lib/forChrome';
	import type { ForSermon } from '$lib/forPages';
	import { seriesDates, seriesICS } from '$lib/forSeries';
	import { hrefInLocale } from '$lib/editionHref';
	import { IS_APP } from '$lib/platform';
	import { nextMonday } from '$lib/planTogether';
	import { readingTime } from '$lib/reading';
	import { absUrl } from '$lib/seo';
	import { localToday } from '$lib/streak';

	/**
	 * A sermon series on an "Ochorus for …" page, drawn as what it is — a
	 * term's journey, one stop a week — rather than a grid of cards: numbered
	 * stops on a line (across on a wide screen, down on a phone). Once the
	 * leader picks the first meeting, each stop carries its date, and the whole
	 * series goes onto their calendar as a file they can pass to the group
	 * ($lib/forSeries). Links are in the page's language, not the reader's UI
	 * one: the series is that language's sermons. The phone apps' WebView
	 * can't save a file, so there the dates show without the download.
	 */
	let {
		series,
		words,
		locale,
		onaction
	}: {
		series: { title: string; note: string; sermons: ForSermon[] };
		words: ForChrome;
		locale: string;
		onaction?: (action: string) => void;
	} = $props();

	let first = $state('');
	let todayIso = $state('');
	onMount(() => {
		todayIso = localToday(new Date());
		first = nextMonday(new Date());
	});
	const dates = $derived(seriesDates(first, series.sermons.length));
	const fmt = $derived(new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short' }));
	const id = $props.id();

	function addToCalendar() {
		if (!dates.length) return;
		const ics = seriesICS(series, first, {
			now: new Date(),
			week: words.week,
			sermonUrl: (slug) => absUrl(hrefInLocale(`/sermons/${slug}`, locale))
		});
		downloadFile('ochorus-series.ics', 'text/calendar;charset=utf-8', ics);
		onaction?.('series-calendar');
	}
</script>

<div class="mt-8">
	<GroupHeading name={series.title} as="h3" blurb={series.note} />
	<ol class="track">
		{#each series.sermons as w, i (w.slug)}
			<li class="stop">
				<span class="dot font-display" aria-hidden="true">{i + 1}</span>
				<div class="stop-body">
					<p class="text-eyebrow group-ink">
						{words.week(i + 1)}{#if dates[i]}{' '}<span class="text-muted"><span aria-hidden="true">·</span> {fmt.format(dates[i])}</span>{/if}
					</p>
					<a class="mt-1 block font-semibold text-text hover:underline" href={hrefInLocale(`/sermons/${w.slug}`, locale)}>{w.title}</a>
					<p class="mt-1 text-small text-muted">
						{w.author.name}{#if w.scripture_ref},{' '}{w.scripture_ref}{/if}
					</p>
					<p class="mt-1 text-small text-muted">
						{words.studyQuestions(w.questions)}{' '}<span class="opacity-50" aria-hidden="true">·</span>{' '}{readingTime(w.word_count)}
					</p>
				</div>
			</li>
		{/each}
	</ol>
	{#if !IS_APP}
	<div class="cal mt-6 rounded-card border border-border bg-surface p-4">
		<label class="block" for={id}>
			<span class="text-eyebrow text-muted">{words.seriesCalendar.first}</span>
			<input {id} class="field mt-1 block" type="date" min={todayIso} bind:value={first} />
		</label>
		<button type="button" class="btn btn-sm" onclick={addToCalendar} disabled={!dates.length}>
			<Icon name="calendar" size={15} />
			{words.seriesCalendar.add}
		</button>
		<p class="cal-note text-small text-muted">{words.seriesCalendar.note}</p>
	</div>
	{/if}
</div>

<style>
	/* A line through numbered stops: across on a wide screen, down on a phone. */
	/* One row from 1024px (a series is SERIES_WEEKS stops, so it never wraps
	   — a wrapped row would leave its last line pointing at nothing), a
	   column below. */
	.track {
		--dot: 2.25rem;
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: minmax(0, 1fr);
		gap: 1.25rem 1rem;
		margin-top: 1.25rem;
	}
	.stop {
		position: relative;
	}
	.stop::before {
		content: '';
		position: absolute;
		top: calc(var(--dot) / 2);
		inset-inline: calc(var(--dot) + 0.25rem) -1rem;
		border-top: 2px solid color-mix(in srgb, var(--group, var(--color-accent)) 35%, transparent);
	}
	.stop:last-child::before {
		display: none;
	}
	.dot {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: var(--dot);
		height: var(--dot);
		border-radius: 999px;
		font-weight: 600;
		color: var(--group, var(--color-accent));
		background: color-mix(in srgb, var(--group, var(--color-accent)) 14%, var(--color-surface));
		border: 2px solid color-mix(in srgb, var(--group, var(--color-accent)) 50%, transparent);
	}
	.stop-body {
		margin-top: 0.75rem;
	}
	.cal {
		display: flex;
		flex-wrap: wrap;
		align-items: end;
		gap: 0.75rem 1rem;
	}
	.cal-note {
		flex: 1 1 18rem;
	}
	@media (max-width: 1023.98px) {
		.track {
			grid-auto-flow: row;
			grid-template-columns: minmax(0, 1fr);
			gap: 0;
		}
		.stop {
			display: grid;
			grid-template-columns: var(--dot) minmax(0, 1fr);
			gap: 0.875rem;
			padding-bottom: 1.25rem;
		}
		.stop::before {
			top: calc(var(--dot) + 0.25rem);
			bottom: 0.25rem;
			inset-inline: calc(var(--dot) / 2 - 1px) auto;
			border-top: none;
			border-inline-start: 2px solid color-mix(in srgb, var(--group, var(--color-accent)) 35%, transparent);
		}
		.stop-body {
			margin-top: 0.25rem;
		}
	}
</style>
