<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { getLang } from '$lib/lang.svelte';
	import { readingTime } from '$lib/reading';
	import { offerFinish, unmarkFinished } from '$lib/progress';
	import { splitEdition } from '$lib/edition';
	import { shelfHref, type ShelfBook } from '$lib/bookshelf';
	import BookCover from './BookCover.svelte';
	import Icon from './Icon.svelte';
	import ProgressBar from './ProgressBar.svelte';

	/**
	 * One cell of a Bookshelf row: a strip of the case's back wall with the book
	 * standing in it, the length of plank it stands on, and its label below the
	 * plank. The row is a gapless grid, so neighbouring cells' walls and planks
	 * join into one continuous shelf; `item = null` is an empty cell, drawn to
	 * carry the plank to the end of a part-filled row (see Bookshelf.svelte).
	 *
	 * The status shows on the book as it would on a real one — a ribbon marker
	 * hanging from a book being read, a gold check on a finished one — and again
	 * in the label's last line: the chapter meter, the month it was finished, or
	 * (for a book still to read) how long it is.
	 *
	 * A reading book links straight back to the exact paragraph; anything else to
	 * the book's page. A corner button finishes a book being read (with Undo), or
	 * puts a finished one back on the Reading shelf, without opening it.
	 */
	let { item }: { item: ShelfBook | null } = $props();
	const t = i18n.t;

	const finishedOn = $derived(
		item?.status === 'finished'
			? new Intl.DateTimeFormat(getLang(), { month: 'short', year: 'numeric' }).format(item.at)
			: ''
	);
	const meter = $derived(
		item?.order
			? `${t('continue.chapter')} ${item.order} / ${item.book.chapter_count} · ${item.pct}%`
			: ''
	);
	const toggleLabel = $derived(
		item?.status === 'finished' ? t('settings.unfinish') : t('continue.markFinished')
	);

	function toggleFinished(e: Event) {
		e.preventDefault();
		if (!item) return;
		if (item.status === 'finished') unmarkFinished(item.book.slug, 'book');
		else offerFinish(item.book.slug, 'book');
	}
</script>

{#if item}
	{@const book = item.book}
	{@const edition = splitEdition(book.slug, book.title)}
	<li class="cell group">
		<div class="wall">
			<a
				href={localizeHref(shelfHref(item))}
				class="book block hover:no-underline"
				aria-label={item.status === 'reading' ? `${book.title} — ${t('reader.resume')}` : book.title}
			>
				<BookCover {book} rounded="rounded-[3px]" />
				<!-- The binding's crease: a soft shade down the spine edge, so a flat
				     cover reads as a bound book standing on the shelf. -->
				<span class="spine" aria-hidden="true"></span>
				{#if item.status === 'reading'}
					<span class="ribbon" aria-hidden="true"></span>
				{:else if item.status === 'finished'}
					<span
						class="absolute bottom-1.5 end-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-gold text-accent-contrast shadow"
						aria-hidden="true"
					>
						<Icon name="check" size={14} />
					</span>
				{/if}
			</a>
			{#if item.status !== 'toRead'}
				<button
					type="button"
					onclick={toggleFinished}
					title={toggleLabel}
					aria-label="{toggleLabel}: {book.title}"
					class="absolute end-3 top-4 z-10 flex h-7 w-7 items-center justify-center rounded-full border border-border bg-surface-2 text-muted opacity-80 transition hover:text-accent focus-visible:opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
				>
					<Icon name={item.status === 'finished' ? 'skip-back' : 'check'} size={14} />
				</button>
			{/if}
		</div>
		<div class="plank" aria-hidden="true"></div>
		<div class="label">
			<a
				href={localizeHref(shelfHref(item))}
				class="line-clamp-2 text-small font-medium leading-snug text-text hover:no-underline"
				title={book.title}
				tabindex="-1">{edition ? edition.base : book.title}</a
			>
			{#if edition}
				<div class="text-eyebrow font-medium text-accent">{edition.audience}</div>
			{/if}
			<div class="truncate text-micro text-muted" title={book.author.name}>{book.author.name}</div>
			<div class="mt-1.5">
				{#if item.status === 'reading'}
					<ProgressBar percent={item.pct} label="{book.title}: {meter}" />
					<div class="mt-1 text-micro text-muted">{meter}</div>
				{:else if item.status === 'finished'}
					<div class="text-micro text-muted">
						<span class="text-gold" aria-hidden="true">✓</span>
						{finishedOn}
					</div>
				{:else}
					<div class="text-micro text-muted">
						{book.chapter_count}
						{book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')}{#if book.word_count}<span
								class="opacity-50"
							>
								· </span
							>{readingTime(book.word_count)}{/if}
					</div>
				{/if}
			</div>
		</div>
	</li>
{:else}
	<li class="cell" aria-hidden="true">
		<div class="wall"><div class="aspect-[3/4]"></div></div>
		<div class="plank"></div>
	</li>
{/if}

<style>
	.cell {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	/* The case's back wall, one cell wide. Its top shade is the shelf above
	   casting down; the cells in a row join into one wall. */
	.wall {
		position: relative;
		padding: 1.1rem clamp(0.4rem, 1.4vw, 0.9rem) 0;
		/* A gradient, not an inset shadow: an inset shadow shades each cell's
		   sides too, which shows as seams where the cells meet. */
		background:
			linear-gradient(to bottom, rgb(0 0 0 / 0.22), transparent 1.1rem),
			var(--shelf-back);
	}
	.book {
		position: relative;
		transform-origin: bottom center;
		box-shadow:
			0 1px 0 rgb(0 0 0 / 0.25),
			4px -2px 10px -4px rgb(0 0 0 / 0.45);
		border-radius: 3px;
	}
	@media (prefers-reduced-motion: no-preference) {
		.book {
			transition: transform var(--duration-fast) ease;
		}
		/* Reaching for a book: it rises off the plank a little. */
		.cell:hover .book,
		.book:focus-visible {
			transform: translateY(-6px);
		}
	}
	.spine {
		position: absolute;
		inset-block: 0;
		inset-inline-start: 0;
		width: 9%;
		border-start-start-radius: 3px;
		border-end-start-radius: 3px;
		background: linear-gradient(
			to right,
			rgb(0 0 0 / 0.32),
			rgb(255 255 255 / 0.1) 55%,
			rgb(0 0 0 / 0.08)
		);
		pointer-events: none;
	}
	:global([dir='rtl']) .spine {
		background: linear-gradient(
			to left,
			rgb(0 0 0 / 0.32),
			rgb(255 255 255 / 0.1) 55%,
			rgb(0 0 0 / 0.08)
		);
	}
	/* A ribbon marker hanging out of the top of the book being read. */
	.ribbon {
		position: absolute;
		top: -0.55rem;
		inset-inline-start: 20%;
		width: 0.7rem;
		height: 2.1rem;
		background: var(--color-accent);
		clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 80%, 0 100%);
		box-shadow: 0 2px 4px rgb(0 0 0 / 0.3);
	}
	/* The plank's face and its darker lip; cells join it into one board. */
	.plank {
		height: 0.95rem;
		background: linear-gradient(
			to bottom,
			rgb(255 255 255 / 0.18) 0 1px,
			var(--shelf-wood) 1px 60%,
			var(--shelf-wood-edge) 60% 100%
		);
		box-shadow: 0 7px 9px -6px rgb(0 0 0 / 0.45);
		position: relative;
		z-index: 1;
	}
	.label {
		padding: 0.6rem clamp(0.4rem, 1.4vw, 0.9rem) 0;
	}
</style>
