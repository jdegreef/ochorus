<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { coverGradient, coverSrcset } from '$lib/coverArt';
	import { tileFace, type BookTile } from '$lib/library-public';
	import BookCover from './BookCover.svelte';

	/**
	 * A small fanned "shelf peek" of book covers — the plan page's strip.
	 * Decorative (aria-hidden); falls back to the book's cover colour when
	 * there's no image.
	 *
	 * BOOKS ONLY, by type. A topic's fan can also hold sermon tiles, which are
	 * drawn as emblem chips rather than covers (`ShelfCard`); this one cannot
	 * receive them, because a plan's days reference `book_slug` and no sermon
	 * can appear. Taking `BookTile[]` makes that a compiler error rather than a
	 * silently blank rectangle.
	 */
	// `size`: `sm` is a small peek; `lg` is a series page's hero, where the
	// covers ARE the page's picture; `fan` is the plan page's hero — up to three
	// large covers fanned from a shared bottom edge, as on /originals, filling
	// the width it is given.
	let {
		covers,
		max = 4,
		size = 'sm'
	}: { covers: BookTile[]; max?: number; size?: 'sm' | 'lg' | 'fan' } = $props();
	const shown = $derived(covers.slice(0, size === 'fan' ? Math.min(max, 3) : max));
</script>

{#if covers.length}
	<div class="covers" class:lg={size === 'lg'} class:fan={size === 'fan'} data-n={shown.length} aria-hidden="true">
		{#each shown as cover, i (cover.slug ?? cover.title)}
			{@const face = tileFace(cover)}
			<div class="cover" data-i={i}>
				{#if face}
					<!-- Drawn, not a bare image: a plate ground has no words. -->
					<BookCover book={face} rounded="" />
				{:else if cover.cover_url}
					{@const source = { src: cover.cover_url, srcset: coverSrcset(cover.cover_url) || undefined }}
					<img
						src={source.src}
						srcset={source.srcset}
						use:hydrateSrc={source}
						alt=""
						loading="lazy"
					/>
				{:else}
					<div class="cover-fallback" style="background: {coverGradient(cover.cover_color)}"></div>
				{/if}
			</div>
		{/each}
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
		margin-inline-start: -0.7rem;
		background: var(--surface);
		transform: rotate(-3deg);
	}
	.lg .cover {
		width: 4.75rem;
		margin-inline-start: -1.4rem;
	}
	.cover:first-child {
		margin-inline-start: 0;
	}
	.cover:nth-child(2) {
		transform: rotate(1deg);
	}
	.cover:nth-child(3) {
		transform: rotate(4deg);
	}
	.cover:nth-child(4) {
		transform: rotate(7deg);
	}
	/* The fan sizes off its width: a 46%-wide 3:4 cover is 0.61 of the width
	   tall, the tilted pair's outer corners drop a little more, and the 1rem
	   the side covers sit below the middle one rides on as padding. Symmetric,
	   so it needs no RTL flip. */
	.fan {
		position: relative;
		display: block;
		box-sizing: content-box;
		aspect-ratio: 100 / 68;
		padding-top: 1rem;
	}
	.fan .cover {
		position: absolute;
		top: 1rem;
		inset-inline-start: 27%;
		width: 46%;
		margin: 0;
		transform: none;
		transform-origin: bottom center;
	}
	.fan[data-n='3'] .cover[data-i='0'] {
		transform: rotate(-10deg) translateX(-36%);
	}
	.fan[data-n='3'] .cover[data-i='1'] {
		z-index: 1;
		top: 0;
	}
	.fan[data-n='3'] .cover[data-i='2'] {
		transform: rotate(10deg) translateX(36%);
	}
	.fan[data-n='2'] .cover[data-i='0'] {
		transform: rotate(-6deg) translateX(-26%);
	}
	.fan[data-n='2'] .cover[data-i='1'] {
		transform: rotate(6deg) translateX(26%);
	}
	.cover img,
	.cover-fallback {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
</style>
