<script lang="ts">
	import type { ShelfBook as ShelfBookItem } from '$lib/bookshelf';
	import ShelfBook from './ShelfBook.svelte';

	/**
	 * One shelf of the Bookshelf page — "Currently reading", "To read" or
	 * "Finished" — drawn as a shelf in a bookcase: books standing on a wooden
	 * plank against a back wall, as many to a row as fit, and a fresh plank for
	 * each row.
	 *
	 * The row is a gapless grid of ShelfBook cells, each carrying its own strip of
	 * wall and plank, so a full row reads as one board. The column count is
	 * measured rather than left to `auto-fill` because a part-filled last row
	 * needs to know how many empty cells to add to carry the plank to the end —
	 * a shelf that stops halfway across looks broken, not unfinished.
	 *
	 * An empty shelf still draws: one bare board with the hint on the wall, so
	 * the three states are always visible and a new reader sees what the page is
	 * for.
	 */
	let {
		id,
		title,
		items,
		emptyHint
	}: {
		id: string;
		title: string;
		items: ShelfBookItem[];
		/** Written on the wall of an empty shelf. */
		emptyHint: string;
	} = $props();

	let width = $state(0);
	// Cells of at least ~108px on a phone (two across at 375px), ~150px from `sm`
	// up — up to eight across on the widest page column.
	const cols = $derived(width ? Math.max(2, Math.floor(width / (width < 640 ? 108 : 150))) : 3);
	const fillers = $derived(items.length % cols ? cols - (items.length % cols) : 0);
</script>

<section {id} class="scroll-mt-24 pt-10" aria-labelledby="{id}-title">
	<div class="mb-4 flex items-baseline gap-3">
		<h2 id="{id}-title" class="text-h2">{title}</h2>
		<span class="rounded-full bg-surface-2 px-2.5 py-0.5 text-small font-semibold text-muted"
			>{items.length}</span
		>
	</div>

	<div bind:clientWidth={width}>
		{#if items.length}
			<ul class="shelf-rows" style:grid-template-columns="repeat({cols}, minmax(0, 1fr))">
				{#each items as item (item.book.slug)}
					<ShelfBook {item} />
				{/each}
				{#each { length: fillers } as _, i (i)}
					<ShelfBook item={null} />
				{/each}
			</ul>
		{:else}
			<div class="empty-wall">
				<p class="m-0 max-w-md text-center text-small text-muted">{emptyHint}</p>
			</div>
			<div class="empty-plank" aria-hidden="true"></div>
		{/if}
	</div>
</section>

<style>
	.shelf-rows {
		display: grid;
		column-gap: 0;
		row-gap: 1.75rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.empty-wall {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 7rem;
		padding: 1rem;
		/* The same wall and plank ShelfBook draws per cell, as one piece. */
		background:
			linear-gradient(to bottom, rgb(0 0 0 / 0.22), transparent 1.1rem),
			var(--shelf-back);
	}
	.empty-plank {
		height: 0.95rem;
		background: linear-gradient(
			to bottom,
			rgb(255 255 255 / 0.18) 0 1px,
			var(--shelf-wood) 1px 60%,
			var(--shelf-wood-edge) 60% 100%
		);
		box-shadow: 0 7px 9px -6px rgb(0 0 0 / 0.45);
	}
</style>
