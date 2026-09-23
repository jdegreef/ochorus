<script lang="ts">
	import { type CoverBook } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';
	import { splitEdition } from '$lib/edition';
	import BookCover from './BookCover.svelte';

	let {
		book,
		showAuthor = false,
		/**
		 * Above the fold: load eagerly with an intrinsic size and high fetch
		 * priority. The LCP element on the two most-linked pages was
		 * `loading="lazy"` and started at opacity-0, which defers the preload
		 * scanner and makes some LCP implementations discount it entirely.
		 */
		priority = false,
		/**
		 * When set, this card is the first of its author's run in the by-author
		 * shelf and carries the `#author-<slug>` target the quick-nav jumps to.
		 */
		anchor
	}: { book: CoverBook; showAuthor?: boolean; priority?: boolean; anchor?: string } = $props();
	const t = i18n.t;

	const chapters = $derived(
		`${book.chapter_count} ${book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')}`
	);
	// A young-reader edition's "(For Teens)" / "(For Children)" can be clamped off
	// the title on a narrow card; pull it onto its own line so the two editions
	// don't look identical. Null for ordinary books.
	const edition = $derived(splitEdition(book.slug, book.title));
</script>

<a
	href={localizeHref(`/books/${book.slug}`)}
	id={anchor ? `author-${anchor}` : undefined}
	class={`book-card card-lift group${anchor ? ' scroll-mt-20' : ''}`}
	data-testid="book-card"
	aria-label={showAuthor ? `${book.title} — ${book.author.name}` : book.title}
>
	<div class="relative">
		<BookCover {book} {priority} />
		<span
			class="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-end gap-1 rounded-b-card bg-gradient-to-t from-black/60 to-transparent px-3 pb-2 pt-6 text-small font-semibold text-white opacity-0 transition-opacity group-hover:opacity-100"
		>
			{t('book.beginReading')} →
		</span>
	</div>

	<div class="mt-2 flex flex-1 flex-col px-0.5">
		<div class="line-clamp-2 text-small font-medium leading-snug text-text" title={book.title}>
			{edition ? edition.base : book.title}
		</div>
		{#if edition}
			<div class="text-eyebrow font-medium text-accent">{edition.audience}</div>
		{/if}
		{#if showAuthor}
			<div class="truncate text-small text-muted" title={book.author.name}>{book.author.name}</div>
		{/if}
		<!-- mt-auto pins the meta to the card's bottom, so a one-line title and a
		     two-line title still bottom out level across a grid row. -->
		<div class="mt-auto pt-0.5 text-eyebrow text-muted">
			{chapters}{#if book.word_count}
				<span class="opacity-50"> · </span>{readingTime(book.word_count)}{/if}
		</div>
	</div>
</a>
