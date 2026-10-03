<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { coverGradient, coverSrcset } from '$lib/coverArt';
	import { tileFace, type BookTile } from '$lib/library-public';
	import BookCover from './BookCover.svelte';

	/**
	 * Book covers fanned together. Decorative (aria-hidden); falls back to the
	 * book's cover colour when there's no image.
	 *
	 * `size`: `sm` is a small strip (a plan's book sections); `lg` a larger one
	 * (a series page's hero); `fan` is a page's hero picture — up to three big
	 * covers fanned from a shared bottom edge, filling the width it is given
	 * (the plan page, /originals). `priority` loads the leading cover eagerly
	 * for a fan that is the page's largest paint.
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
	// The fan's geometry holds three; the middle one (or the only one) is in front.
	const shown = $derived(covers.slice(0, size === 'fan' ? Math.min(max, 3) : max));
	const front = $derived(shown.length === 3 ? 1 : 0);
</script>

{#if covers.length}
	<div class="covers" class:strip={size !== 'fan'} class:lg={size === 'lg'} class:fan={size === 'fan'} aria-hidden="true">
		{#each shown as cover, i (cover.slug ?? cover.title)}
			{@const face = tileFace(cover)}
			{@const eager = priority && i === front}
			<div class="cover">
				{#if face}
					<!-- Drawn, not a bare image: a plate ground has no words. -->
					<BookCover book={face} rounded="" priority={eager} />
				{:else if cover.cover_url}
					{@const source = { src: cover.cover_url, srcset: coverSrcset(cover.cover_url) || undefined }}
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
	/* The strip: overlapped and tilted a little more at each step. */
	.strip .cover {
		margin-inline-start: -0.7rem;
		transform: rotate(-3deg);
	}
	.lg .cover {
		width: 4.75rem;
		margin-inline-start: -1.4rem;
	}
	.strip .cover:first-child {
		margin-inline-start: 0;
	}
	.strip .cover:nth-child(2) {
		transform: rotate(1deg);
	}
	.strip .cover:nth-child(3) {
		transform: rotate(4deg);
	}
	.strip .cover:nth-child(4) {
		transform: rotate(7deg);
	}
	/* The fan sizes off its width: a 46%-wide 3:4 cover is 0.61 of the width
	   tall, the tilted pair's outer corners drop a little more, and the 1rem
	   the side covers sit below the middle one rides on as padding. Symmetric,
	   so it needs no RTL flip. One cover stands alone; two lean apart; three
	   lean out from a raised middle. */
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
		transform-origin: bottom center;
	}
	.fan .cover:first-child:nth-last-child(3) {
		transform: rotate(-10deg) translateX(-36%);
	}
	.fan .cover:nth-child(2):nth-last-child(2) {
		z-index: 1;
		top: 0;
	}
	.fan .cover:nth-child(3) {
		transform: rotate(10deg) translateX(36%);
	}
	.fan .cover:first-child:nth-last-child(2) {
		transform: rotate(-6deg) translateX(-26%);
	}
	.fan .cover:nth-child(2):last-child {
		transform: rotate(6deg) translateX(26%);
	}
	.cover img,
	.cover-fallback {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
</style>
