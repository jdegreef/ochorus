<script lang="ts">
	import type { BookSummary } from '$lib/library';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';
	import BookCover from './BookCover.svelte';

	let { book, showAuthor = false }: { book: BookSummary; showAuthor?: boolean } = $props();
	const t = i18n.t;

	const translated = $derived(book.source_type !== 'public_domain');
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
	<div class="relative">
		<BookCover {book} />
		{#if translated}
			<span
				class="eyebrow absolute start-2 top-2 rounded-full bg-black/55 px-2 py-0.5 text-white backdrop-blur"
			>
				{t('books.badgeTranslated')}
			</span>
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
