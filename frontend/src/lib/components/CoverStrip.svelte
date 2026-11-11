<script lang="ts">
	import { assetSrcset, assetUrl } from '$lib/assetUrl';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { coverGradient, coverSrcset } from '$lib/coverArt';
	import { tileFace, type BookTile } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import BookCover from './BookCover.svelte';

	/**
	 * Book covers fanned together. Decorative (aria-hidden) unless `spread`;
	 * falls back to the book's cover colour when there's no image.
	 *
	 * `size`: `sm` is a small strip (a plan's book sections); `lg` a larger one
	 * (a series page's hero); `fan` is a page's hero picture — a deck: one big
	 * featured cover in front and up to two more stepped up and out behind it,
	 * with a "+N" chip when the list holds more than the deck shows, filling
	 * the width it is given (the plan page, /originals, /for). `spread` is the
	 * home hero: three covers side by side, the middle one larger, raised and
	 * in front — every cover WHOLE, none tucked behind another, so each title
	 * reads (the five-cover arc it replaced cut the outer ones to "The Pu… of G"
	 * and "…mber"). Each is a link to its own book, labelled with its title and
	 * author, since there the covers are the picture of the library and its
	 * first way in. Fewer than three → the deck. `one` is a lone cover dressed
	 * as the fan's featured one, filling the width it is given (a one-book
	 * plan's hero, beside its title). `priority` loads the featured cover
	 * eagerly for a fan that is the page's largest paint.
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
	}: {
		covers: BookTile[];
		max?: number;
		size?: 'sm' | 'lg' | 'fan' | 'spread' | 'one';
		priority?: boolean;
	} = $props();
	// The spread: three covers in their own left-to-right order — the middle
	// one leads. Fewer to be had → the deck.
	const spread = $derived(size === 'spread' && covers.length >= 3);
	const fan = $derived(size === 'fan' || (size === 'spread' && !spread));
	// The deck's geometry holds three. Of three, the middle one is featured —
	// callers put their lead there (audienceHub.heroCovers) — and the other two
	// stand behind it in order; otherwise the first leads.
	const shown = $derived.by(() => {
		if (spread) return covers.slice(0, 3);
		const list = covers.slice(0, fan ? Math.min(max, 3) : size === 'one' ? 1 : max);
		return fan && list.length === 3 ? [list[1], list[0], list[2]] : list;
	});
	const lead = $derived(spread ? 1 : 0);
	// The chip sits under the deck's back cover; the spread has no back corner
	// for it, so it shows no chip.
	const more = $derived(fan ? covers.length - shown.length : 0);
</script>

{#if covers.length}
	<div
		class="covers"
		class:strip={size === 'sm' || size === 'lg'}
		class:lg={size === 'lg'}
		class:fan={fan || spread}
		class:one={size === 'one'}
		class:spread
		aria-hidden={spread ? undefined : 'true'}
	>
		{#each shown as cover, i (cover.slug ?? cover.title)}
			{@const face = tileFace(cover)}
			{@const eager = priority && i === lead}
			<svelte:element
				this={spread ? 'a' : 'div'}
				class="cover"
				href={spread ? localizeHref(`/books/${cover.slug}`) : undefined}
			>
				{#if face}
					<!-- Drawn, not a bare image: a plate ground has no words. -->
					<BookCover book={face} rounded="" priority={eager} byline={spread} />
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
			</svelte:element>
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
	/* A lone cover (`one`) is dressed as the fan's featured one. */
	.fan .cover,
	.one .cover {
		border-radius: 0.375rem;
		box-shadow: var(--shadow-card), var(--shadow-popover);
	}
	.fan .cover {
		position: absolute;
		bottom: 0;
		inset-inline-start: 26cqw;
		width: 48cqw;
	}
	.one .cover {
		position: relative;
		width: 100%;
	}
	/* The spine: a shade down the bound edge, so each reads as a book. */
	.fan .cover::after,
	.one .cover::after {
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
	/* The spread (the home hero): three upright books side by side, the middle
	   one larger, raised and in front, the outer two a step back (smaller,
	   lower, a shade darker). They don't overlap — a 2cqw gap each side — so
	   every cover shows whole. Sized off the width (cqw) in a box whose
	   aspect-ratio is fixed, so nothing moves when the covers arrive.
	   Symmetric, so it needs no mirroring in a right-to-left locale. */
	.spread {
		aspect-ratio: 100 / 52;
	}
	.spread .cover,
	.spread .cover:first-child:not(:only-of-type) {
		bottom: 0;
		inset-inline-start: 0;
		width: 30cqw;
		filter: brightness(0.96);
		z-index: 1;
	}
	.spread .cover:nth-child(2) {
		bottom: 3.5cqw;
		inset-inline-start: 32cqw;
		width: 36cqw;
		filter: none;
		z-index: 2;
	}
	/* Restated in full: the deck's third-cover rule above is as specific. */
	.spread .cover:nth-child(3) {
		bottom: 0;
		inset-inline-start: 70cqw;
		width: 30cqw;
		filter: brightness(0.96);
		z-index: 1;
	}
	/* A lift on hover, as a shelf card's: each is a way into its book. */
	@media (hover: hover) and (prefers-reduced-motion: no-preference) {
		.spread .cover {
			transition: translate 0.2s ease;
		}
		.spread .cover:hover {
			translate: 0 -0.5cqw;
		}
	}
	.spread .cover:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 3px;
	}
	/* How many more the list holds: under the back of the deck. */
	.more {
		position: absolute;
		z-index: 4;
		bottom: 4cqw;
		inset-inline-end: 4cqw;
		padding: 0.3em 0.8em;
		border: 1px solid var(--border);
		border-radius: var(--radius-pill);
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
