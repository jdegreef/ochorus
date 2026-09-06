<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import type { ReadingStats } from '$lib/readingStats';

	/**
	 * The six reading totals as a tile row — in progress, finished, highlights,
	 * notes, favourites, bookmarks. Shared by the home dashboard and Settings ›
	 * Activity so the two can't drift in which totals they show or their order.
	 */
	let { stats }: { stats: ReadingStats } = $props();
	const t = i18n.t;

	const tiles = $derived([
		{ label: t('settings.statInProgress'), value: stats.inProgress },
		{ label: t('settings.statFinished'), value: stats.finished },
		{ label: t('settings.statHighlights'), value: stats.highlights },
		{ label: t('settings.statNotes'), value: stats.notes },
		{ label: t('settings.statFavorites'), value: stats.favorites },
		{ label: t('settings.statBookmarks'), value: stats.bookmarks }
	]);
</script>

<!-- A zero total is real information but shouldn't shout as loudly as a "70":
     dim the whole tile so the numbers that carry momentum lead the eye. -->
<div class="grid grid-cols-3 gap-3 sm:grid-cols-6">
	{#each tiles as tile (tile.label)}
		<div
			class="rounded-card border border-border bg-surface-2 px-3 py-4 text-center"
			class:opacity-60={tile.value === 0}
		>
			<div class="font-display text-h2 font-semibold text-text">{tile.value}</div>
			<div class="mt-0.5 text-eyebrow text-muted">{tile.label}</div>
		</div>
	{/each}
</div>
