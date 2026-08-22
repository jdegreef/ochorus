<script lang="ts">
	import { coverGradient } from '$lib/coverArt';
	import type { BookTile } from '$lib/library';

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
	let { covers, max = 4 }: { covers: BookTile[]; max?: number } = $props();
</script>

{#if covers.length}
	<div class="covers" aria-hidden="true">
		{#each covers.slice(0, max) as cover (cover.title)}
			<div class="cover">
				{#if cover.cover_url}
					<img src={cover.cover_url} alt="" loading="lazy" />
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
