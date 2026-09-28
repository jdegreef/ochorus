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
	// `size`: `sm` is the plan page's peek; `lg` is a series page's hero, where
	// the covers ARE the page's picture.
	let {
		covers,
		max = 4,
		size = 'sm'
	}: { covers: BookTile[]; max?: number; size?: 'sm' | 'lg' } = $props();
</script>

{#if covers.length}
	<div class="covers" class:lg={size === 'lg'} aria-hidden="true">
		{#each covers.slice(0, max) as cover (cover.slug ?? cover.title)}
			{@const face = tileFace(cover)}
			<div class="cover">
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
	.cover img,
	.cover-fallback {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
</style>
