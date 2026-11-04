<script lang="ts">
	import { splitEdition } from '$lib/edition';
	import { i18n } from '$lib/i18n.svelte';
	import type { ShelfBook } from '$lib/bookshelf';

	/**
	 * One book standing spine-out, for the Bookshelf's spines view: the book's
	 * own cover colour, its title running down the spine, two gilt bands, and
	 * the same status marks the covers view uses — a ribbon hanging from a book
	 * being read, a gold check at the foot of a finished one.
	 *
	 * A button, not a link: pressing it pulls the book out (it rises) and the
	 * shelf opens its panel underneath, with the cover and the actions. Size is
	 * decided by the shelf (spineSize × its scale).
	 *
	 * Pointing at it (a mouse) or tabbing to it lifts it and tips its head
	 * toward the reader, the way a finger hooks a book off a shelf, and tells
	 * the shelf (`onpeek`) so it can letter the title above it — the spine's
	 * own lettering is too small to read at a glance.
	 *
	 * hex-ok-file: the spine is painted in the book's `cover_color` — data, not a
	 * theme surface — with white ink, which that colour is floored to carry at AA
	 * where it is minted (`covers.ink_safe`), as on BookCover's plate.
	 */
	let {
		item,
		width,
		height,
		selected,
		onselect,
		onpeek
	}: {
		item: ShelfBook;
		width: number;
		height: number;
		selected: boolean;
		onselect: (el: HTMLButtonElement) => void;
		/** This spine pointed at or tabbed to (its button), or let go (null). */
		onpeek?: (el: HTMLButtonElement | null) => void;
	} = $props();
	const t = i18n.t;

	const title = $derived(splitEdition(item.book.slug, item.book.title)?.base ?? item.book.title);
	let el = $state<HTMLButtonElement>();
</script>

<button
	bind:this={el}
	type="button"
	class="spine"
	class:selected
	class:paused={item.paused}
	style:width="{width}px"
	style:height="{height}px"
	style:background-color={item.book.cover_color || 'var(--shelf-wood-edge)'}
	aria-expanded={selected}
	aria-label="{item.book.title} — {item.book.author.name}{item.status === 'reading'
		? ` · ${t('fav.shelfReading')}`
		: item.status === 'finished'
			? ` · ${t('fav.shelfFinished')}`
			: ''}"
	title="{item.book.title} — {item.book.author.name}"
	onclick={() => el && onselect(el)}
	onpointerenter={(e) => e.pointerType === 'mouse' && el && onpeek?.(el)}
	onpointerleave={() => onpeek?.(null)}
	onfocus={() => el?.matches(':focus-visible') && onpeek?.(el)}
	onblur={() => onpeek?.(null)}
>
	<span class="band" aria-hidden="true"></span>
	<span class="title" class:small={width < 30} aria-hidden="true">{title}</span>
	<span class="band" aria-hidden="true"></span>
	{#if item.status === 'reading'}
		<span class="ribbon" aria-hidden="true"></span>
	{:else if item.status === 'finished'}
		<span class="done" aria-hidden="true">✓</span>
	{/if}
</button>

<style>
	/* A paused book (unopened for weeks) rests quieter on the shelf. */
	.spine.paused {
		filter: grayscale(0.55);
		opacity: 0.8;
	}
	.spine {
		position: relative;
		flex: none;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.45rem;
		padding: 0.6rem 0 0.7rem;
		border: 0;
		border-radius: 2px 2px 0 0;
		color: white;
		cursor: pointer;
		/* Rounded spine: light down the middle, shade at both edges. */
		background-image: linear-gradient(
			to right,
			rgb(0 0 0 / 0.3),
			rgb(255 255 255 / 0.12) 45%,
			rgb(0 0 0 / 0.08) 70%,
			rgb(0 0 0 / 0.32)
		);
		box-shadow: 1px 0 0 rgb(0 0 0 / 0.25);
	}
	.spine {
		transform-origin: center bottom;
	}
	@media (prefers-reduced-motion: no-preference) {
		.spine {
			/* A little spring in the lift: it overshoots and settles. */
			transition:
				transform 300ms cubic-bezier(0.3, 1.4, 0.5, 1),
				box-shadow 300ms ease;
		}
	}
	/* Pointed at (a real hover only — a tap would leave it stuck) or tabbed
	   to: lifted, and its head tipped toward the reader off the shelf — a turn
	   toward the reader, not a slant across the row (coverStraight.test). */
	@media (hover: hover) {
		.spine:hover {
			transform: translateY(-10px) perspective(24rem) rotateX(-12deg);
			box-shadow:
				1px 0 0 rgb(0 0 0 / 0.25),
				0 10px 14px -6px rgb(0 0 0 / 0.45);
		}
	}
	.spine:focus-visible {
		transform: translateY(-10px) perspective(24rem) rotateX(-12deg);
	}
	/* Pulled half out, while its panel is open. */
	.spine.selected {
		transform: translateY(-12px);
		outline: 2px solid var(--color-accent);
		outline-offset: 2px;
	}
	/* Gilt bands, struck in the frame metal the home hero hangs its painting
	   in (--hero-gilt: gold, silver in the cool palettes) — a lit top edge, a
	   shaded foot, the way leaf catches light on a rounded spine. The title
	   stays white: the spine colour is floored to carry white at AA, not gold. */
	.band {
		flex: none;
		width: 72%;
		height: 4px;
		border-radius: 1px;
		background: linear-gradient(
			to bottom,
			color-mix(in srgb, var(--hero-gilt) 55%, white),
			var(--hero-gilt) 45%,
			var(--hero-gilt-deep)
		);
		box-shadow: 0 1px 1px rgb(0 0 0 / 0.35);
	}
	.title {
		flex: 1;
		min-height: 0;
		writing-mode: vertical-rl;
		font-family: var(--font-display);
		font-size: var(--fs-eyebrow);
		line-height: 1.1;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		text-shadow: 0 1px 1px rgb(0 0 0 / 0.35);
	}
	.title.small {
		font-size: var(--fs-micro);
	}
	.ribbon {
		position: absolute;
		top: -0.5rem;
		inset-inline-start: 50%;
		width: 0.55rem;
		height: 1.9rem;
		margin-inline-start: -0.275rem;
		background: var(--color-accent);
		clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 80%, 0 100%);
	}
	.done {
		position: absolute;
		bottom: 0.25rem;
		inset-inline-start: 50%;
		margin-inline-start: -0.5rem;
		width: 1rem;
		height: 1rem;
		border-radius: 999px;
		background: var(--color-gold);
		color: var(--color-accent-contrast);
		font-size: var(--fs-micro);
		line-height: 1rem;
		text-align: center;
	}
</style>
