<script lang="ts">
	import { type BookSummary } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';
	import BookCover from './BookCover.svelte';

	let { book, showAuthor = true }: { book: BookSummary; showAuthor?: boolean } = $props();
	const t = i18n.t;

	const chapters = $derived(
		`${book.chapter_count} ${book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')}`
	);
</script>

<a
	href={localizeHref(`/books/${book.slug}`)}
	class="card-tint group flex flex-wrap items-center gap-x-4 rounded-card border border-transparent px-2 py-2.5"
	data-testid="book-row"
>
	<div class="w-12 shrink-0 sm:w-14">
		<BookCover {book} rounded="rounded-sm" />
	</div>
	<div class="min-w-0 flex-1">
		<div class="flex flex-wrap items-center gap-x-2">
			<span class="text-body font-medium text-balance text-text">{book.title}</span>
		</div>
		{#if showAuthor}
			<div class="text-small text-muted">{book.author.name}</div>
		{/if}
		{#if book.subtitle}
			<div class="text-small italic text-muted">{book.subtitle}</div>
		{/if}
	</div>
	<!-- Below the title on a phone, beside it from `sm` up. The same block either
	     way: at 390px this column was taking a third of the row, which is what
	     truncated the titles — "The Inner Cha…", "Baptism with …". Wrapping it to
	     its own line gives the title the full width and costs one short line.
	     `ps-16` lines it up under the text rather than under the cover (w-12 plus
	     the gap-4); logical, so it flips in Arabic. -->
	<div
		class="mt-0.5 w-full shrink-0 ps-16 text-small text-muted sm:mt-0 sm:w-auto sm:ps-0 sm:text-end"
	>
		<span class="sm:block">{chapters}</span>
		{#if book.word_count}
			<span class="sm:hidden" aria-hidden="true">·</span>
			<span class="sm:block">{readingTime(book.word_count)}</span>
		{/if}
	</div>
</a>
