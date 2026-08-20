<script lang="ts">
	import { isTranslated, type BookSummary } from '$lib/library';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';
	import BookCover from './BookCover.svelte';
	import SourceBadge from './SourceBadge.svelte';

	let { book, showAuthor = true }: { book: BookSummary; showAuthor?: boolean } = $props();
	const t = i18n.t;

	const chapters = $derived(
		`${book.chapter_count} ${book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')}`
	);
</script>

<a
	href={localizeHref(`/books/${book.slug}`)}
	class="group flex items-center gap-4 rounded-card border border-transparent px-2 py-2.5 hover:border-border hover:bg-surface hover:no-underline"
	data-testid="book-row"
>
	<div class="w-12 shrink-0 sm:w-14">
		<BookCover {book} rounded="rounded-sm" />
	</div>
	<div class="min-w-0 flex-1">
		<div class="flex items-center gap-2">
			<span class="truncate text-body font-medium text-text">{book.title}</span>
			{#if isTranslated(book.source_type)}
				<SourceBadge sourceType={book.source_type} variant="inline" />
			{/if}
		</div>
		{#if showAuthor}
			<div class="truncate text-small text-muted">{book.author.name}</div>
		{/if}
		{#if book.subtitle}
			<div class="truncate text-small italic text-muted">{book.subtitle}</div>
		{/if}
	</div>
	<div class="shrink-0 text-end text-small text-muted">
		<div>{chapters}</div>
		{#if book.word_count}<div>{readingTime(book.word_count)}</div>{/if}
	</div>
</a>
