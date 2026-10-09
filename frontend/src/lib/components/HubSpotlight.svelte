<script lang="ts">
	import * as m from '$lib/paraglide/messages.js';
	import type { BookSummary, EditionRung } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { contentLang, readingMinutes } from '$lib/reading';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import BookCover from './BookCover.svelte';
	import EditionLadder from './EditionLadder.svelte';
	import ShareButton from './ShareButton.svelte';

	/**
	 * The one story a hub sells hardest (`AUDIENCE_SPOTLIGHTS`), as a banner:
	 * the cover large, the book's own one-line pitch (`hook`, translated with
	 * the edition), how long a sitting is, one "Begin the journey", and the
	 * work's edition ladder — so a teen sees the full original waiting above
	 * the retelling.
	 */
	let {
		book,
		ladder,
		onstart,
		onclimb,
		onshare
	}: {
		book: BookSummary;
		ladder?: EditionRung[];
		onstart?: () => void;
		onclimb?: () => void;
		onshare?: () => void;
	} = $props();
	const t = i18n.t;

	const lang = $derived(contentLang(book.language));
	const pitch = $derived(book.hook || book.subtitle);
	const sitting = $derived(
		book.word_count && book.chapter_count
			? m.series_chapter_minutes({ minutes: readingMinutes(book.word_count / book.chapter_count) })
			: ''
	);
</script>

<section class="spotlight mb-12" aria-labelledby="spotlight-heading">
	<a class="spotlight-cover" href={localizeHref(`/books/${book.slug}`)} tabindex="-1" aria-hidden="true">
		<BookCover {book} />
	</a>
	<div class="min-w-0">
		<p class="eyebrow text-gold">{t('audience.spotlightEyebrow')}</p>
		<h2
			id="spotlight-heading"
			class="mt-1 text-balance font-display text-h2 font-semibold leading-tight"
			lang={lang}
			dir="auto"
		>
			{book.title}
		</h2>
		{#if pitch}
			<p class="pitch mt-3 font-display" {lang} dir="auto">{pitch}</p>
		{/if}
		<p class="mt-3 text-small text-muted">
			<span class="whitespace-nowrap"
				>{book.chapter_count}
				{book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')}</span
			>{#if sitting}<span class="opacity-50">{' · '}</span><span class="whitespace-nowrap"
					>{sitting}</span
				>{/if}
		</p>
		<div class="mt-5 flex flex-wrap items-center gap-3">
			<a class="btn btn-primary" href={localizeHref(`/books/${book.slug}`)} onclick={onstart}>
				{t('audience.spotlightCta')}
			</a>
			<!-- A story travels friend to friend: the book page, with its pitch. -->
			<ShareButton
				url={`${SITE_URL}${localizeHref(`/books/${book.slug}`)}`}
				title={pitch ? `${book.title}: ${pitch}` : book.title}
				label={t('audience.spotlightShare')}
				showLabel
				{onshare}
			/>
		</div>
		{#if ladder && ladder.length > 1}
			<div class="mt-6">
				<p class="section-label mb-2">{t('audience.spotlightLadder')}</p>
				<EditionLadder rungs={ladder} current={book.slug} {onclimb} />
			</div>
		{/if}
	</div>
</section>

<style>
	/* A dark, cinematic band — the one place on the hub that is a poster rather
	   than a shelf — in the theme's ink, so it inverts sensibly in lamplight. */
	.spotlight {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 1.5rem;
		padding: 1.5rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background:
			radial-gradient(120% 90% at 0% 0%, color-mix(in oklab, var(--audience-teens) 22%, transparent), transparent 60%),
			var(--surface);
	}
	.spotlight-cover {
		display: block;
		width: 8.5rem;
	}
	.pitch {
		max-width: 34rem;
		font-size: var(--fs-h3);
		line-height: 1.35;
		color: var(--text);
	}
	@media (min-width: 640px) {
		.spotlight {
			grid-template-columns: 12rem minmax(0, 1fr);
			gap: 2.5rem;
			padding: 2rem 2.25rem;
			align-items: start;
		}
		.spotlight-cover {
			width: 100%;
		}
	}
</style>
