<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import type { ReadingStats } from '$lib/readingStats';

	/**
	 * The six reading totals as a tile row — in progress, finished, highlights,
	 * notes, favourites, bookmarks. Shared by the home dashboard and Settings ›
	 * Activity so the two can't drift in which totals they show or their order.
	 *
	 * Each tile is a doorway to the page that lists what it counts — four of which
	 * already existed, so the mapping is mostly wiring: reading → /reading, the
	 * three annotation totals → the one /notebook that already unifies them
	 * (filtered), favourites → the "My Library" page. A tile only becomes a link
	 * when it has something to show: a zero total stays an inert, dimmed tile
	 * rather than a link to an empty page.
	 */
	let { stats }: { stats: ReadingStats } = $props();
	const t = i18n.t;

	const tiles = $derived([
		{ label: t('settings.statInProgress'), value: stats.inProgress, href: '/reading' },
		{ label: t('settings.statFinished'), value: stats.finished, href: '/reading#finished' },
		{ label: t('settings.statHighlights'), value: stats.highlights, href: '/notebook?view=highlights' },
		{ label: t('settings.statNotes'), value: stats.notes, href: '/notebook?view=notes' },
		{ label: t('settings.statFavorites'), value: stats.favorites, href: '/favorites' },
		{ label: t('settings.statBookmarks'), value: stats.bookmarks, href: '/notebook?view=bookmarks' }
	]);
</script>

<!-- A zero total is real information but shouldn't shout as loudly as a "70":
     dim the whole tile so the numbers that carry momentum lead the eye. A zero
     tile is also not a link — there is nothing to show — so it renders as a
     plain <div>; a non-zero one is an <a> that lifts and shows a ↗ on hover. -->
<div class="grid grid-cols-3 gap-3 sm:grid-cols-6">
	{#each tiles as tile (tile.label)}
		{#if tile.value > 0}
			<a
				href={localizeHref(tile.href)}
				class="stat-tile group relative rounded-card border border-border bg-surface-2 px-3 py-4 text-center transition hover:-translate-y-0.5 hover:border-accent hover:no-underline"
			>
				<span
					class="absolute end-2 top-2 text-eyebrow text-accent opacity-0 transition-opacity group-hover:opacity-100"
					aria-hidden="true">↗</span
				>
				<div class="font-display text-h2 font-semibold text-text">{tile.value}</div>
				<div class="mt-0.5 text-eyebrow text-muted">{tile.label}</div>
			</a>
		{:else}
			<div class="rounded-card border border-border bg-surface-2 px-3 py-4 text-center opacity-60">
				<div class="font-display text-h2 font-semibold text-text">{tile.value}</div>
				<div class="mt-0.5 text-eyebrow text-muted">{tile.label}</div>
			</div>
		{/if}
	{/each}
</div>

<style>
	/* The lift's shadow — `--shadow-card` is a token, not a Tailwind utility, so
	   it's applied here rather than as a `shadow-*` class that would no-op. */
	.stat-tile:hover {
		box-shadow: var(--shadow-card);
	}
</style>
