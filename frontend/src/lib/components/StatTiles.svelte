<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import type { IconName } from '$lib/components/Icon.svelte';
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
	 * when it has something to show: a zero total stays an inert tile rather than
	 * a link to an empty page.
	 *
	 * Each total wears one library-palette hue (app.css, "THE LIBRARY PALETTE")
	 * and an icon, so the row reads as six different things rather than six
	 * beige boxes. A zero tile drops the colour and says how to fill it instead.
	 */
	let {
		stats,
		compact = false
	}: {
		stats: ReadingStats;
		/** One line per tile (icon, number, label) — the dashboard's slim strip.
		 *  Settings keeps the tall tiles with their how-to-start hints. */
		compact?: boolean;
	} = $props();
	const t = i18n.t;

	type Hue = 'indigo' | 'cypress' | 'ochre' | 'plum' | 'oxblood' | 'slate';
	type Tile = { label: string; value: number; href: string; icon: IconName; hue: Hue; hint: string };

	const tiles = $derived<Tile[]>([
		{
			label: t('settings.statInProgress'),
			value: stats.inProgress,
			href: '/reading',
			icon: 'book',
			hue: 'indigo',
			hint: t('settings.statEmptyBooks')
		},
		{
			label: t('settings.statFinished'),
			value: stats.finished,
			href: '/reading#finished',
			icon: 'check',
			hue: 'cypress',
			hint: t('settings.statEmptyFinished')
		},
		{
			label: t('settings.statHighlights'),
			value: stats.highlights,
			href: '/notebook?view=highlights',
			icon: 'highlighter',
			hue: 'ochre',
			hint: t('settings.statEmptyPassage')
		},
		{
			label: t('settings.statNotes'),
			value: stats.notes,
			href: '/notebook?view=notes',
			icon: 'pen',
			hue: 'plum',
			hint: t('settings.statEmptyPassage')
		},
		{
			label: t('settings.statFavorites'),
			value: stats.favorites,
			href: '/favorites',
			icon: 'heart',
			hue: 'oxblood',
			hint: t('settings.statEmptyFavorites')
		},
		{
			label: t('settings.statBookmarks'),
			value: stats.bookmarks,
			href: '/notebook?view=bookmarks',
			icon: 'bookmark',
			hue: 'slate',
			hint: t('settings.statEmptyBookmarks')
		}
	]);
</script>

<!-- A non-zero tile is an <a> on its hue's soft ground that lifts and shows a ↗
     on hover. A zero total is real information but shouldn't shout as loudly
     as a "70", and there is nothing to link to: it renders as a plain <div>
     with a dashed edge, a muted icon and a one-line hint on how to start
     (wide screens only). -->
<div class="grid grid-cols-3 sm:grid-cols-6" class:gap-3={!compact} class:gap-2={compact} class:compact>
	{#each tiles as tile (tile.label)}
		{#if tile.value > 0}
			<a
				href={localizeHref(tile.href)}
				class="stat-tile group relative rounded-card px-3 py-4 text-center transition hover:-translate-y-0.5 hover:no-underline"
				style="--tile-hue: var(--hue-{tile.hue}); --tile-soft: var(--hue-{tile.hue}-soft)"
			>
				<span
					class="tile-hue absolute end-2 top-2 text-eyebrow opacity-0 transition-opacity group-hover:opacity-100"
					aria-hidden="true">↗</span
				>
				<span class="tile-icon tile-hue inline-flex"><Icon name={tile.icon} size={20} /></span>
				<div class="tile-value tile-hue font-display text-h2 font-semibold">{tile.value}</div>
				<div class="tile-label tile-hue mt-0.5 text-eyebrow">{tile.label}</div>
			</a>
		{:else}
			<div class="stat-empty rounded-card px-3 py-4 text-center">
				<span class="tile-icon inline-flex text-muted"><Icon name={tile.icon} size={20} /></span>
				<div class="tile-value font-display text-h2 font-semibold text-muted">{tile.value}</div>
				<div class="tile-label mt-0.5 text-eyebrow text-text">{tile.label}</div>
				<!-- Not on phones: in a three-column row a translated hint wraps to
				     four lines and stretches every tile beside it. Not in the slim
				     strip either, which is one line by design. -->
				{#if !compact}
					<div class="mt-1 hidden text-eyebrow text-muted sm:block">{tile.hint}</div>
				{/if}
			</div>
		{/if}
	{/each}
</div>

<style>
	.stat-tile {
		background: var(--tile-soft);
		border: 1px solid transparent;
	}
	.tile-hue {
		color: var(--tile-hue);
	}
	/* The lift's shadow — `--shadow-card` is a token, not a Tailwind utility, so
	   it's applied here rather than as a `shadow-*` class that would no-op. */
	.stat-tile:hover {
		border-color: var(--tile-hue);
		box-shadow: var(--shadow-card);
	}
	/* --border, not --border-strong: this tile is inert, and the strong edge
	   is the token for interactive controls (app.css). */
	.stat-empty {
		border: 1.5px dashed var(--border);
	}
	/* The slim strip: each tile two short lines — icon and number, then the
	   label — at about half the tall tile's height. Grid areas over the same
	   markup, so the two variants stay one template. */
	.compact .stat-tile,
	.compact .stat-empty {
		display: grid;
		grid-template-columns: auto auto;
		grid-template-areas: 'icon value' 'label label';
		justify-content: center;
		align-items: center;
		column-gap: 0.4rem;
		padding-block: 0.55rem;
	}
	.compact .tile-icon {
		grid-area: icon;
	}
	.compact .tile-value {
		grid-area: value;
		font-size: var(--fs-h3);
		line-height: 1.1;
	}
	.compact .tile-label {
		grid-area: label;
		margin-top: 0.1rem;
	}
</style>
