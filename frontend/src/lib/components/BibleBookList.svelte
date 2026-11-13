<script lang="ts">
	import type { BookSummary } from '$lib/library-public';
	import { bibleChapters } from '$lib/bible';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import BookCover from '$lib/components/BookCover.svelte';
	import Icon from '$lib/components/Icon.svelte';

	/**
	 * One division of the /bible hub as a compact index: a row per book (a small
	 * cover, the title, its Hebrew or Greek name) linking to the book, and a
	 * chapter-count button that opens the book's chapters in place as the book
	 * page's chips, so any chapter is two taps from the hub. The chips are drawn
	 * only while open: 1,189 links on every load would bloat the prerendered page,
	 * and the book pages already link each chapter for crawlers.
	 */
	let { books, open = $bindable(null) }: { books: readonly BookSummary[]; open?: string | null } =
		$props();
	const t = i18n.t;
</script>

<ul class="bible-list">
	{#each books as book (book.slug)}
		{@const chapters = bibleChapters(book)}
		{@const isOpen = open === book.slug}
		{@const word = chapters.length === 1 ? t('book.chapterOne') : t('book.chaptersMany')}
		<li class="bible-row">
			<a class="bible-row-link" href={localizeHref(`/books/${book.slug}`)}>
				<!-- The title beside it names the link; the cover's own label would
				     only repeat it. -->
				<span class="bible-row-cover" aria-hidden="true"><BookCover {book} rounded="rounded-sm" /></span>
				<span class="bible-row-text">
					<span class="bible-row-title">{book.title}</span>
					{#if book.subtitle}<span class="bible-row-sub">{book.subtitle}</span>{/if}
				</span>
			</a>
			{#if chapters.length}
				<button
					type="button"
					class="bible-row-chapters"
					aria-expanded={isOpen}
					aria-controls="chapters-{book.slug}"
					aria-label="{book.title}: {chapters.length} {word}"
					onclick={() => (open = isOpen ? null : book.slug)}
				>
					<span class="tabular-nums">{chapters.length}</span>
					<span>{word}</span>
					<span class="bible-row-chevron" class:open={isOpen}><Icon name="chevron-right" size={16} /></span>
				</button>
				{#if isOpen}
					<ol class="bible-chapter-grid" id="chapters-{book.slug}">
						{#each chapters as ch (ch.n)}
							<li>
								<a class="bible-chapter-chip" href={localizeHref(ch.href)} aria-label={ch.name} title={ch.name}
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
	.bible-row-cover {
		display: block;
		flex: none;
		width: 2.5rem;
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
		transition: transform 0.15s ease;
	}
	.bible-row-chevron.open {
		transform: rotate(90deg);
	}
	@media (prefers-reduced-motion: reduce) {
		.bible-row-chevron {
			transition: none;
		}
	}
	/* The book page's chapter chips (`.chapter-chip` there), at the same tap size. */
	.bible-chapter-grid {
		grid-column: 1 / -1;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(2.75rem, 1fr));
		gap: 0.375rem;
		list-style: none;
		margin: 0.6rem 0 0.25rem;
		padding: 0;
	}
	.bible-chapter-chip {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 2.75rem;
		border: 1.5px solid var(--border-strong);
		border-radius: var(--radius-sm);
		background: var(--surface);
		font-size: var(--fs-small);
		font-variant-numeric: tabular-nums;
		color: var(--text);
		text-decoration: none;
	}
	.bible-chapter-chip:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
</style>
