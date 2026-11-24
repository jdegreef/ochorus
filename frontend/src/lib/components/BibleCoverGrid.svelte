<script lang="ts">
	import { tick } from 'svelte';
	import type { BibleBookLinks, BookSummary } from '$lib/library-public';
	import { bibleChapterCount, type BiblePlace } from '$lib/bible';
	import { chapterCount } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import BibleChapterPanel from '$lib/components/BibleChapterPanel.svelte';
	import BibleListenLink from '$lib/components/BibleListenLink.svelte';
	import BibleMoreLinks from '$lib/components/BibleMoreLinks.svelte';

	/**
	 * One division of the /bible hub as painted covers (the wide-screen default,
	 * #8416), with what the compact index offers a tap away: under each cover,
	 * Listen to the whole book and its chapters. A book's chapters open below the
	 * division's covers, not inside the grid — opening one never reflows the
	 * covers around it — with the book's name, where it leads in the library and
	 * a close button, then the same panel the index opens (`BibleChapterPanel`).
	 * One book open at a time across the page, shared with the index (`open`).
	 */
	let {
		books,
		open = $bindable(null),
		placeOf,
		linksOf
	}: {
		books: readonly BookSummary[];
		open?: string | null;
		placeOf?: (book: BookSummary) => BiblePlace | null;
		linksOf?: (book: BookSummary) => BibleBookLinks | undefined;
	} = $props();

	const t = i18n.t;
	const openBook = $derived(books.find((b) => b.slug === open) ?? null);

	// The panel opens below the division's covers, so take a keyboard or
	// screen-reader user to it rather than leave it a dozen stops away.
	async function show(slug: string) {
		open = slug;
		await tick();
		document.getElementById(`panel-title-${slug}`)?.focus();
	}

	async function close(slug: string) {
		open = null;
		// Back to the toggle that opened it, so a keyboard reader keeps their place.
		await tick();
		document.getElementById(`cover-toggle-${slug}`)?.focus();
	}
</script>

<!-- No author line: every book is the Open Word Bible's. No series line:
     every book is in the one series this page is. -->
<div class="book-grid">
	{#each books as book (book.slug)}
		{@const count = bibleChapterCount([book])}
		{@const isOpen = open === book.slug}
		<div class="bible-cover">
			<BookCard {book} showSeries={false} />
			{#if count}
				<div class="bible-cover-actions">
					<BibleListenLink {book} />
					<button
						type="button"
						id="cover-toggle-{book.slug}"
						class="bible-cover-chapters"
						aria-expanded={isOpen}
						aria-controls={isOpen ? `chapters-${book.slug}` : undefined}
						aria-label="{t('scripture.chaptersHeading')}: {book.title}, {chapterCount(count)}"
						onclick={() => (isOpen ? (open = null) : show(book.slug))}
					>
						{t('scripture.chaptersHeading')}
						<span class="bible-cover-chevron"><Icon name="chevron-right" size={16} /></span>
					</button>
				</div>
			{/if}
		</div>
	{/each}
</div>

{#if openBook}
	{@const links = linksOf?.(openBook)}
	<section
		class="bible-cover-panel"
		id="chapters-{openBook.slug}"
		aria-labelledby="panel-title-{openBook.slug}"
	>
		<div class="bible-cover-panel-head">
			<h4 id="panel-title-{openBook.slug}" class="bible-cover-panel-title" tabindex="-1">
				{openBook.title}
			</h4>
			<BibleMoreLinks {links} />
			<button
				type="button"
				class="btn btn-sm btn-ghost bible-cover-close"
				aria-label="{t('a11y.close')}: {openBook.title}"
				onclick={() => close(openBook.slug)}
			>
				{t('a11y.close')}
			</button>
		</div>
		<BibleChapterPanel
			book={openBook}
			place={placeOf?.(openBook) ?? null}
			intro={links?.intro ?? ''}
		/>
	</section>
{/if}

<style>
	/* The card above, its actions below, in one grid cell: the shared
	   .book-card is height:100% (it fills a shelf's cell), so here it takes the
	   free row and the actions keep their own. */
	.bible-cover {
		display: grid;
		grid-template-rows: 1fr auto;
		gap: 0.5rem;
		min-width: 0;
	}
	.bible-cover-actions {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}
	.bible-cover-chapters {
		display: inline-flex;
		flex: 1;
		align-items: center;
		justify-content: center;
		gap: 0.2rem;
		min-width: 0;
		min-height: 2.75rem;
		padding-inline: 0.5rem 0.3rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--surface);
		font-size: var(--fs-small);
		color: var(--muted);
		white-space: nowrap;
	}
	.bible-cover-chapters:hover,
	.bible-cover-chapters[aria-expanded='true'] {
		border-color: var(--accent);
		color: var(--accent);
	}
	.bible-cover-chevron {
		display: inline-flex;
		transition: transform var(--duration-base) ease;
	}
	.bible-cover-chapters[aria-expanded='true'] .bible-cover-chevron {
		transform: rotate(90deg);
	}
	@media (prefers-reduced-motion: reduce) {
		.bible-cover-chevron {
			transition: none;
		}
	}
	.bible-cover-panel {
		margin-top: 1rem;
		padding: 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.bible-cover-panel-head :global(.bible-more) {
		margin: 0;
	}
	.bible-cover-panel-head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.25rem 1rem;
		margin-bottom: 0.75rem;
	}
	.bible-cover-panel-title {
		margin: 0;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
	}
	.bible-cover-panel-title:focus {
		outline: none;
	}
	.bible-cover-panel-title:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.bible-cover-close {
		margin-inline-start: auto;
	}
</style>
