<script lang="ts">
	import type { BookSummary } from '$lib/library-public';
	import { bibleChapterCount, bibleChapters } from '$lib/bible';
	import { chapterCount } from '$lib/reading';
	import { localizeHref } from '$lib/href';
	import Icon from '$lib/components/Icon.svelte';

	/**
	 * One division of the /bible hub as a compact index: a row per book (its
	 * spine colour, the title, its Hebrew or Greek name) linking to the book,
	 * and a chapter-count button that opens the book's chapters in place as the
	 * book page's chips (`.chapter-grid` in app.css), so any chapter is two taps
	 * from the hub.
	 *
	 * No cover image: at list size a cover's type is unreadable, and 66 of them
	 * cost ~400 KB on a retina phone. The swatch is the book's `cover_color`, the
	 * colour its spine wears in the canon strip above. The chips are built and
	 * drawn only for the open book: 1,189 links on every load would bloat the
	 * prerendered page, and the book pages already link each chapter.
	 */
	let { books, open = $bindable(null) }: { books: readonly BookSummary[]; open?: string | null } =
		$props();
</script>

<ul class="bible-list">
	{#each books as book (book.slug)}
		{@const count = bibleChapterCount([book])}
		{@const isOpen = open === book.slug}
		<li class="bible-row">
			<a class="bible-row-link" href={localizeHref(`/books/${book.slug}`)}>
				<span class="bible-row-swatch" style:--swatch={book.cover_color || null} aria-hidden="true"></span>
				<span class="bible-row-text">
					<span class="bible-row-title">{book.title}</span>
					{#if book.subtitle}<span class="bible-row-sub">{book.subtitle}</span>{/if}
				</span>
			</a>
			{#if count}
				<button
					type="button"
					class="bible-row-chapters"
					aria-expanded={isOpen}
					aria-controls="chapters-{book.slug}"
					aria-label="{book.title}: {chapterCount(count)}"
					onclick={() => (open = isOpen ? null : book.slug)}
				>
					{chapterCount(count)}
					<span class="bible-row-chevron"><Icon name="chevron-right" size={16} /></span>
				</button>
				{#if isOpen}
					<ol class="chapter-grid bible-row-grid" id="chapters-{book.slug}">
						{#each bibleChapters(book) as ch (ch.n)}
							<li>
								<a class="chapter-chip" href={localizeHref(ch.href)} aria-label={ch.name} title={ch.name}
									>{ch.n}</a
								>
							</li>
						{/each}
					</ol>
				{/if}
			{/if}
		</li>
	{/each}
</ul>

<style>
	/* One column on a phone, two from the tablet up; a row's open chapter grid
	   stays in its own column. */
	.bible-list {
		display: grid;
		gap: 0 2rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	@media (min-width: 768px) {
		.bible-list {
			grid-template-columns: repeat(2, minmax(0, 1fr));
			align-items: start;
		}
	}
	.bible-row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: center;
		gap: 0 0.75rem;
		padding-block: 0.6rem;
		border-bottom: 1px solid var(--border);
	}
	.bible-row-link {
		display: flex;
		align-items: center;
		gap: 0.85rem;
		min-width: 0;
		color: inherit;
		text-decoration: none;
	}
	/* The book's spine, standing on its end: the canon strip's colour. */
	.bible-row-swatch {
		flex: none;
		align-self: stretch;
		width: 0.375rem;
		min-height: 2.25rem;
		border-radius: 2px;
		background: var(--swatch, var(--border-strong));
	}
	.bible-row-text {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	.bible-row-title {
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--text);
	}
	.bible-row-link:hover .bible-row-title {
		color: var(--accent);
	}
	.bible-row-sub {
		font-size: var(--fs-small);
		color: var(--muted);
		line-height: 1.4;
	}
	.bible-row-chapters {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		min-height: 2.75rem;
		padding-inline: 0.6rem 0.4rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--surface);
		font-size: var(--fs-small);
		font-variant-numeric: tabular-nums;
		color: var(--muted);
		white-space: nowrap;
	}
	.bible-row-chapters:hover,
	.bible-row-chapters[aria-expanded='true'] {
		border-color: var(--accent);
		color: var(--accent);
	}
	.bible-row-chevron {
		display: inline-flex;
		transition: transform var(--duration-base) ease;
	}
	.bible-row-chapters[aria-expanded='true'] .bible-row-chevron {
		transform: rotate(90deg);
	}
	@media (prefers-reduced-motion: reduce) {
		.bible-row-chevron {
			transition: none;
		}
	}
	.bible-row-grid {
		grid-column: 1 / -1;
		margin-block: 0.6rem 0.25rem;
	}
</style>
