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
	 * hex-ok-file: the spine is painted in the book's `cover_color` — data, not a
	 * theme surface — with white ink, which that colour is floored to carry at AA
	 * where it is minted (`covers.ink_safe`), as on BookCover's plate.
	 */
	let {
		item,
		width,
		height,
		selected,
		onselect
	}: {
		item: ShelfBook;
		width: number;
		height: number;
		selected: boolean;
		onselect: (el: HTMLButtonElement) => void;
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
	@media (prefers-reduced-motion: no-preference) {
		.spine {
			transition: transform var(--duration-fast) ease;
		}
	}
	.spine:hover {
		transform: translateY(-4px);
	}
	/* Pulled half out, while its panel is open. */
	.spine.selected {
		transform: translateY(-12px);
		outline: 2px solid var(--color-accent);
		outline-offset: 2px;
	}
	.band {
		flex: none;
		width: 70%;
		height: 3px;
		border-block: 1px solid rgb(255 255 255 / 0.45);
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
