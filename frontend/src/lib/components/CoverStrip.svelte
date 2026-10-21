<script lang="ts">
	import { assetSrcset, assetUrl } from '$lib/assetUrl';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { coverGradient, coverSrcset } from '$lib/coverArt';
	import { tileFace, type BookTile } from '$lib/library-public';
	import BookCover from './BookCover.svelte';

	/**
	 * Book covers fanned together. Decorative (aria-hidden); falls back to the
	 * book's cover colour when there's no image.
	 *
	 * `size`: `sm` is a small strip (a plan's book sections); `lg` a larger one
	 * (a series page's hero); `fan` is a page's hero picture — a deck: one big
	 * featured cover in front and up to two more stepped up and out behind it,
	 * with a "+N" chip when the list holds more than the deck shows, filling
	 * the width it is given (the plan page, /originals, /for). `priority`
	 * loads the featured cover eagerly for a fan that is the page's largest
	 * paint.
	 *
	 * BOOKS ONLY, by type. A topic's fan can also hold sermon tiles, which are
	 * drawn as emblem chips rather than covers (`ShelfCard`); this one cannot
	 * receive them, because a plan's days reference `book_slug` and no sermon
	 * can appear. Taking `BookTile[]` makes that a compiler error rather than a
	 * silently blank rectangle.
	 */
	let {
		covers,
		max = 4,
		size = 'sm',
		priority = false
	}: { covers: BookTile[]; max?: number; size?: 'sm' | 'lg' | 'fan'; priority?: boolean } =
		$props();
	// The fan's geometry holds three. Of three, the middle one is featured —
	// callers put their lead there (audienceHub.heroCovers) — and the other two
	// stand behind it in order; otherwise the first leads.
	const shown = $derived.by(() => {
		const list = covers.slice(0, size === 'fan' ? Math.min(max, 3) : max);
		return size === 'fan' && list.length === 3 ? [list[1], list[0], list[2]] : list;
	});
	const more = $derived(size === 'fan' ? covers.length - shown.length : 0);
</script>

{#if covers.length}
	<div class="covers" class:strip={size !== 'fan'} class:lg={size === 'lg'} class:fan={size === 'fan'} aria-hidden="true">
		{#each shown as cover, i (cover.slug ?? cover.title)}
			{@const face = tileFace(cover)}
			{@const eager = priority && i === 0}
			<div class="cover">
				{#if face}
					<!-- Drawn, not a bare image: a plate ground has no words. -->
					<BookCover book={face} rounded="" priority={eager} />
				{:else if cover.cover_url}
					{@const source = { src: assetUrl(cover.cover_url), srcset: assetSrcset(coverSrcset(cover.cover_url)) || undefined }}
					<img
						src={source.src}
						srcset={source.srcset}
						use:hydrateSrc={source}
						alt=""
						loading={eager ? 'eager' : 'lazy'}
					/>
				{:else}
					<div class="cover-fallback" style="background: {coverGradient(cover.cover_color)}"></div>
				{/if}
			</div>
		{/each}
		{#if more > 0}<span class="more"><bdi dir="ltr">+{more}</bdi></span>{/if}
	</div>
{/if}

<style>
	.covers {
		display: flex;
	}
	.cover {
		width: 2.5rem;
		aspect-ratio: 3 / 4;
		border-radius: 0.25rem;
		overflow: hidden;
		box-shadow: var(--shadow-card);
		background: var(--surface);
	}
	/* The strip: overlapped, every cover standing straight (a book is never
	   drawn on a slant — coverStraight.test.ts). */
	.strip .cover {
		margin-inline-start: -0.7rem;
	}
	.lg .cover {
		width: 4.75rem;
		margin-inline-start: -1.4rem;
	}
	.strip .cover:first-child {
		margin-inline-start: 0;
	}
	/* The deck sizes off its width (cqw): the featured cover stands in front at
	   the inline start, and each one behind is smaller, set further toward the
	   inline end and raised, so it peeks out above and beside the one before —
	   a stack seen at an angle, every cover upright (coverStraight.test.ts).
	   Logical offsets, so in Arabic the deck steps the other way. */
	.fan {
		position: relative;
		display: block;
		aspect-ratio: 100 / 68;
		container-type: inline-size;
	}
	.fan .cover {
		position: absolute;
		bottom: 0;
		inset-inline-start: 26cqw;
		width: 48cqw;
		border-radius: 0.375rem;
		box-shadow: var(--shadow-card), var(--shadow-popover);
	}
	/* The spine: a shade down the bound edge, so each reads as a book. */
	.fan .cover::after {
		content: '';
		position: absolute;
		inset: 0;
		pointer-events: none;
		background: linear-gradient(
			to right,
			rgb(0 0 0 / 0.22),
			rgb(255 255 255 / 0.1) 3%,
			rgb(0 0 0 / 0.08) 5.5%,
			transparent 11%
		);
	}
	.fan .cover:first-child {
		z-index: 3;
	}
	.fan .cover:first-child:not(:only-of-type) {
		inset-inline-start: 6cqw;
	}
	.fan .cover:nth-child(2) {
		z-index: 2;
		bottom: 10cqw;
		inset-inline-start: 30cqw;
		width: 42cqw;
		filter: brightness(0.97);
	}
	.fan .cover:nth-child(2):last-of-type {
		inset-inline-start: 46cqw;
	}
	.fan .cover:nth-child(3) {
		z-index: 1;
		bottom: 20cqw;
		inset-inline-start: 52cqw;
		width: 36cqw;
		filter: brightness(0.93);
	}
	/* How many more the list holds: under the back of the deck. */
	.more {
		position: absolute;
		z-index: 4;
		bottom: 4cqw;
		inset-inline-end: 4cqw;
		padding: 0.3em 0.8em;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: var(--surface);
		box-shadow: var(--shadow-card);
		color: var(--text);
		font-size: clamp(0.75rem, 3.2cqw, 1rem);
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		line-height: 1;
	}
	.cover img,
	.cover-fallback {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
</style>
