<script lang="ts">
	import type { BookSummary } from '$lib/library';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
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
	class="group block hover:no-underline"
	data-testid="book-card"
	aria-label={showAuthor ? `${book.title} — ${book.author.name}` : book.title}
>
	<div class="relative transition-transform group-hover:-translate-y-1">
		<BookCover {book} />
		{#if translated}
			<span
				class="absolute left-2 top-2 rounded-full bg-black/55 px-2 py-0.5 text-[0.62rem] font-semibold uppercase tracking-wide text-white backdrop-blur"
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

	<div class="mt-2 px-0.5">
		<div class="text-small font-medium leading-snug text-text">{book.title}</div>
		{#if showAuthor}
			<div class="text-[0.8rem] text-muted">{book.author.name}</div>
		{/if}
		{#if book.subtitle}
			<div class="line-clamp-1 text-[0.78rem] italic text-muted">{book.subtitle}</div>
		{/if}
		<div class="mt-0.5 text-[0.78rem] text-muted">
			{chapters}{#if book.word_count}
				<span class="opacity-50"> · </span>{readingTime(book.word_count)}{/if}
		</div>
	</div>
</a>
