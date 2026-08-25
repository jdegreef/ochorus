<script lang="ts">
	import { isTranslated, type BookSummary } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';
	import BookCover from './BookCover.svelte';
	import SourceBadge from './SourceBadge.svelte';

	let {
		book,
		showAuthor = false,
		/**
		 * Above the fold: load eagerly with an intrinsic size and high fetch
		 * priority. The LCP element on the two most-linked pages was
		 * `loading="lazy"` and started at opacity-0, which defers the preload
		 * scanner and makes some LCP implementations discount it entirely.
		 */
		priority = false
	}: { book: BookSummary; showAuthor?: boolean; priority?: boolean } = $props();
	const t = i18n.t;

	const translated = $derived(isTranslated(book.source_type));
	const chapters = $derived(
		`${book.chapter_count} ${book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')}`
	);
</script>

<a
	href={localizeHref(`/books/${book.slug}`)}
	class="book-card group"
	data-testid="book-card"
	aria-label={showAuthor ? `${book.title} — ${book.author.name}` : book.title}
>
	<!-- The query container is the cover, and only when something is going to sit
	     on it: SourceBadge's overlay hides itself below 6rem of artwork, and the
	     English shelf is entirely public-domain, so this is 0 containment roots
	     there rather than one per card. -->
	<div class="relative" class:cover-container={translated}>
		<BookCover {book} {priority} />
		{#if translated}
			<SourceBadge sourceType={book.source_type} variant="overlay" class="absolute start-2 top-2" />
		{/if}
		<span
			class="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-end gap-1 rounded-b-card bg-gradient-to-t from-black/60 to-transparent px-3 pb-2 pt-6 text-small font-semibold text-white opacity-0 transition-opacity group-hover:opacity-100"
		>
			{t('book.beginReading')} →
		</span>
	</div>

	<div class="mt-2 flex flex-1 flex-col px-0.5">
		<div class="line-clamp-2 text-small font-medium leading-snug text-text">{book.title}</div>
		{#if showAuthor}
			<div class="truncate text-small text-muted">{book.author.name}</div>
		{/if}
		<!-- mt-auto pins the meta to the card's bottom, so a one-line title and a
		     two-line title still bottom out level across a grid row. -->
		<div class="mt-auto pt-0.5 text-eyebrow text-muted">
			{chapters}{#if book.word_count}
				<span class="opacity-50"> · </span>{readingTime(book.word_count)}{/if}
		</div>
	</div>
</a>

<style>
	.cover-container {
		container-type: inline-size;
	}
</style>
