<script lang="ts">
	import { isTranslated, type BookSummary } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { readingTime, bookProgressPercent } from '$lib/reading';
	import { getProgressRecord } from '$lib/progress';
	import BookCover from './BookCover.svelte';
	import SourceBadge from './SourceBadge.svelte';
	import ProgressBar from './ProgressBar.svelte';

	/**
	 * A saved book on the "My Library" page — the same cover-and-title tile as
	 * BookCard, but carrying the reader's own progress: a book already in
	 * progress shows a progress bar and links straight back to where they left
	 * off, while an untouched save links to the book page to begin.
	 *
	 * This is the upgrade over the old favorites shelf, which showed saved books
	 * as bare text pills — a saved book you were halfway through looked identical
	 * to one you had never opened.
	 */
	let { book }: { book: BookSummary } = $props();
	const t = i18n.t;

	// A saved AI-translated edition keeps its "awaiting native review" badge here
	// too — a translation must never be shown as an original (see CLAUDE.md).
	const translated = $derived(isTranslated(book.source_type));

	// Read once from localStorage per book (ssr=false, so this is always the
	// client). Re-derives if the card is reused for a different book.
	const rec = $derived(getProgressRecord(book.slug, 'book'));
	// "In progress" only past chapter 1: a reader who has merely opened chapter 1
	// gets the book page (to read the blurb and begin), not a resume deep-link
	// back to the very first paragraph.
	const inProgress = $derived(!!rec && rec.order > 1);
	const percent = $derived(rec ? bookProgressPercent(rec.order, book.chapter_count) : 0);

	// In-progress → resume the exact spot; otherwise the book page.
	const href = $derived(
		inProgress && rec
			? `/books/${book.slug}/${rec.order}?p=${rec.paragraph_index}`
			: `/books/${book.slug}`
	);
</script>

<a
	href={localizeHref(href)}
	class="book-card group"
	data-testid="library-book-card"
	aria-label={inProgress ? `${book.title} — ${t('reader.resume')}` : book.title}
>
	<div class="relative" class:cover-container={translated}>
		<BookCover {book} />
		{#if translated}
			<SourceBadge sourceType={book.source_type} variant="overlay" class="absolute start-2 top-2" />
		{/if}
		<span
			class="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-end gap-1 rounded-b-card bg-gradient-to-t from-black/60 to-transparent px-3 pb-2 pt-6 text-small font-semibold text-white opacity-0 transition-opacity group-hover:opacity-100"
		>
			{inProgress ? t('reader.resume') : t('book.beginReading')} →
		</span>
	</div>

	<div class="mt-2 flex flex-1 flex-col px-0.5">
		<div class="line-clamp-2 text-small font-medium leading-snug text-text">{book.title}</div>
		<div class="truncate text-small text-muted">{book.author.name}</div>
		<div class="mt-auto pt-1.5">
			{#if inProgress}
				<ProgressBar {percent} label="{book.title}: {t('reader.resume')}" />
				<div class="mt-1 text-eyebrow text-muted">
					{t('book.continueCh')}
					{rec!.order}<span class="opacity-50"> · </span>{percent}%
				</div>
			{:else}
				<div class="text-eyebrow text-muted">
					{book.chapter_count}
					{book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')}{#if book.word_count}<span
							class="opacity-50"
						>
							· </span
						>{readingTime(book.word_count)}{/if}
				</div>
			{/if}
		</div>
	</div>
</a>

<style>
	/* Only a translated book needs a containment root — the SourceBadge overlay
	   sizes itself against the cover width. Same rule BookCard uses. */
	.cover-container {
		container-type: inline-size;
	}
</style>
