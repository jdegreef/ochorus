<script lang="ts">
	import { tick } from 'svelte';
	import { packRows, spineSize, type ShelfBook as ShelfBookItem } from '$lib/bookshelf';
	import { i18n } from '$lib/i18n.svelte';
	import { readingTime } from '$lib/reading';
	import BookCover from './BookCover.svelte';
	import Icon from './Icon.svelte';
	import ProgressBar from './ProgressBar.svelte';
	import ShelfBook from './ShelfBook.svelte';
	import ShelfBookActions from './ShelfBookActions.svelte';
	import ShelfSpine from './ShelfSpine.svelte';
	import ShelfDownloadControl from './ShelfDownloadControl.svelte';

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
	 * In the SPINES view (`view = 'spines'`) the books stand spine-out instead,
	 * packed left to right into as many boards as they need — three or four times
	 * the books per row, for a long To read. The boards stack straight on top of
	 * each other like a real bookcase. Pressing a spine pulls the book out and
	 * opens a panel under its board with the cover, where the reader is, and the
	 * same actions the covers view's menu has; focus moves into the panel and
	 * back to the spine when it closes.
	 *
	 * An empty shelf still draws: one bare board with the hint on the wall, so
	 * the three states are always visible and a new reader sees what the page is
	 * for.
	 */
	let {
		id,
		title,
		items,
		emptyHint,
		view = 'covers'
	}: {
		id: string;
		title: string;
		items: ShelfBookItem[];
		view?: 'covers' | 'spines';
		/** Written on the wall of an empty shelf. */
		emptyHint: string;
	} = $props();

	let width = $state(0);
	// Cells of at least ~108px on a phone (two across at 375px), ~150px from `sm`
	// up — up to eight across on the widest page column.
	const cols = $derived(width ? Math.max(2, Math.floor(width / (width < 640 ? 108 : 150))) : 3);
	const fillers = $derived(items.length % cols ? cols - (items.length % cols) : 0);

	const t = i18n.t;
	// Spines: a little smaller on a phone. The wall's side padding (0.75rem)
	// comes off the width the rows can use.
	const GAP = 3;
	const scale = $derived(width && width < 640 ? 0.82 : 1);
	const sizes = $derived(
		items.map((i) => {
			const s = spineSize(i.book);
			return { width: Math.round(s.width * scale), height: Math.round(s.height * scale) };
		})
	);
	const rows = $derived(
		packRows(
			sizes.map((s) => s.width),
			Math.max(0, (width || 600) - 24),
			GAP
		)
	);

	let selected = $state<string | null>(null);
	let opener: HTMLButtonElement | null = null;
	let panel = $state<HTMLDivElement>();
	const selectedItem = $derived(items.find((i) => i.book.slug === selected) ?? null);

	async function select(slug: string, el: HTMLButtonElement) {
		if (selected === slug) return close();
		selected = slug;
		opener = el;
		await tick();
		panel?.focus();
	}
	function close() {
		selected = null;
		opener?.focus();
		opener = null;
	}
</script>

<svelte:window
	onkeydown={(e) => {
		if (selected && e.key === 'Escape') close();
	}}
/>

{#snippet pulledOut(item: ShelfBookItem)}
	{@const book = item.book}
	<div
		bind:this={panel}
		tabindex="-1"
		role="group"
		aria-label={book.title}
		class="pulled mt-4 mb-6 flex flex-col gap-4 rounded-card border border-border bg-surface p-4 sm:flex-row sm:items-start"
	>
		<div class="flex min-w-0 flex-1 gap-4">
			<div class="w-20 shrink-0 sm:w-24"><BookCover {book} rounded="rounded-sm" /></div>
			<div class="min-w-0 flex-1">
				<div class="text-h3 font-display text-text">{book.title}</div>
				<div class="mt-0.5 text-small text-muted">{book.author.name}</div>
				<div class="mt-3 max-w-xs text-micro text-muted">
					{#if item.status === 'reading'}
						<ProgressBar percent={item.pct} label="{book.title}: {item.pct}%" />
						<div class="mt-1">
							{t('continue.chapter')}
							{item.order} / {book.chapter_count} · {item.pct}%
						</div>
					{:else if item.status === 'finished'}
						<span class="text-gold" aria-hidden="true">✓</span>
						{t('fav.shelfFinished')}
					{:else}
						{book.chapter_count}
						{book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')}{#if book.word_count}
							· {readingTime(book.word_count)}{/if}
					{/if}
				</div>
			</div>
		</div>
		<div class="sm:w-60">
			<ShelfBookActions {item} onDone={close} />
		</div>
		<button
			type="button"
			class="btn btn-sm self-start"
			onclick={close}
			aria-label="{t('fav.closeBook')}: {book.title}"
		>
			<Icon name="close" size={14} />
			{t('fav.closeBook')}
		</button>
	</div>
{/snippet}

<section {id} class="scroll-mt-24 pt-10" aria-labelledby="{id}-title">
	<div class="mb-4 flex flex-wrap items-baseline gap-3">
		<h2 id="{id}-title" class="text-h2">{title}</h2>
		<span class="rounded-full bg-surface-2 px-2.5 py-0.5 text-small font-semibold text-muted"
			>{items.length}</span
		>
		<ShelfDownloadControl
			shelf={id}
			books={items.map((i) => ({ slug: i.book.slug, language: i.book.language }))}
		/>
	</div>

	<div bind:clientWidth={width}>
		{#if items.length && view === 'spines'}
			{#each rows as row, r (r)}
				<ul class="spine-wall" style:min-height="{Math.round(200 * scale)}px">
					{#each row as i (items[i].book.slug)}
						<li class="flex">
							<ShelfSpine
								item={items[i]}
								width={sizes[i].width}
								height={sizes[i].height}
								selected={selected === items[i].book.slug}
								onselect={(el) => select(items[i].book.slug, el)}
							/>
						</li>
					{/each}
				</ul>
				<div class="empty-plank" aria-hidden="true"></div>
				{#if selectedItem && row.some((i) => items[i].book.slug === selected)}
					{@render pulledOut(selectedItem)}
				{/if}
			{/each}
		{:else if items.length}
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
	.spine-wall {
		display: flex;
		align-items: flex-end;
		gap: 3px;
		list-style: none;
		margin: 0;
		padding: 1.1rem 0.75rem 0;
		background:
			linear-gradient(to bottom, rgb(0 0 0 / 0.22), transparent 1.1rem),
			var(--shelf-back);
	}
	.pulled:focus {
		outline: none;
	}
	.pulled:focus-visible {
		outline: 2px solid var(--color-accent);
		outline-offset: 2px;
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
