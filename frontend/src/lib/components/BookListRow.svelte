<script lang="ts">
	import type { BookSummary } from '$lib/library';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { readingTime } from '$lib/reading';
	import BookCover from './BookCover.svelte';

	let { book, showAuthor = true }: { book: BookSummary; showAuthor?: boolean } = $props();
	const t = i18n.t;

	const translated = $derived(book.source_type !== 'public_domain');
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
		<BookCover {book} rounded="rounded-md" />
	</div>
	<div class="min-w-0 flex-1">
		<div class="flex items-center gap-2">
			<span class="truncate text-body font-medium text-text">{book.title}</span>
			{#if translated}
				<span
					class="shrink-0 rounded-full border border-border px-1.5 py-0.5 text-[0.6rem] font-semibold uppercase tracking-wide text-muted"
				>
					{t('books.badgeTranslated')}
				</span>
			{/if}
		</div>
		{#if showAuthor}
			<div class="truncate text-small text-muted">{book.author.name}</div>
		{/if}
		{#if book.subtitle}
			<div class="truncate text-[0.8rem] italic text-muted">{book.subtitle}</div>
		{/if}
	</div>
	<div class="shrink-0 text-right text-[0.78rem] text-muted">
		<div>{chapters}</div>
		{#if book.word_count}<div>{readingTime(book.word_count)}</div>{/if}
	</div>
</a>
