<script lang="ts">
	import { onMount } from 'svelte';
	import type { BookSummary } from '$lib/library-public';
	import { loadDayVerse, type TodayPicks } from '$lib/todayPicks';
	import { pickDailyChapter, type DailyChapter } from '$lib/dailyChapter';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { lang } from '$lib/lang.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	/**
	 * The /bible hub's opening: the day's verse, set large, and the chapter
	 * of the day beside it on its book's painted art — the first thing the eye
	 * lands on is Scripture, not a heading and a paragraph.
	 *
	 * Both picks are the home page's Today card's ($lib/todayPicks,
	 * $lib/dailyChapter), so the two pages never disagree about today. They
	 * are chosen by the reader's LOCAL date, so after mount: the prerender
	 * draws the box at its size with nothing in it (no shift when it fills),
	 * and a language or a day with no OWB verse keeps only the chapter. With
	 * neither, the box goes.
	 */
	let { books }: { books: readonly BookSummary[] } = $props();
	const t = i18n.t;
	/** Whether the day's verse is the Open Word Bible's here (English only). */
	const withVerse = lang.current === 'en';

	let verse = $state<TodayPicks['verse']>(null);
	let chapter = $state<DailyChapter | null>(null);
	let ready = $state(false);
	onMount(() => {
		const now = new Date();
		chapter = pickDailyChapter(now, lang.current);
		// Scripture on the hub is the Open Word Bible's own wording. The day's
		// verse is in the OWB only in English (`loadDayVerse`); elsewhere it is
		// the devotional's own Bible, so here it is left out and the chapter of
		// the day stands alone.
		if (!withVerse) {
			ready = true;
			return;
		}
		loadDayVerse(now, lang.current)
			.then((v) => (verse = v), () => (verse = null))
			.finally(() => (ready = true));
	});
	const book = $derived(chapter ? books.find((b) => b.slug === chapter!.slug) : undefined);
	// Gone once loaded with nothing to show; until then, the reserved box.
	// Chapter only (no OWB verse here): drawn once the chapter is picked.
	const show = $derived(withVerse ? !ready || !!verse || !!book : !!book);
</script>

{#if show}
	<section
		class="today card-tint"
		class:solo={!withVerse}
		aria-label={withVerse ? t('home.todayVerse') : t('home.todayChapter')}
		aria-busy={!ready}
	>
		<div class="words">
			{#if verse}
				<p class="eyebrow text-accent">{t('home.todayVerse')}</p>
				<blockquote class="verse" lang={verse.lang} dir="auto">{verse.text}</blockquote>
				<p class="ref">{verse.ref}</p>
			{:else if !ready && withVerse}
				<span class="ghost" aria-hidden="true"></span>
			{:else if !withVerse && chapter && book}
				<!-- No verse here: the chapter itself is the headline. -->
				<p class="eyebrow text-accent">{t('home.todayChapter')}</p>
				<p class="verse">{chapter.title}</p>
			{/if}
			{#if chapter && book && !withVerse}
				<a class="btn btn-primary btn-solid read" href={localizeHref(chapter.href)}
					>{t('home.startReading')} <Arrow /></a
				>
			{:else if chapter && book}
				<a class="btn btn-primary btn-solid read" href={localizeHref(chapter.href)}
					>{t('home.todayChapter')}: {chapter.title} <Arrow /></a
				>
			{/if}
		</div>
		{#if chapter && book}
			<a class="art" href={localizeHref(chapter.href)} tabindex="-1" aria-hidden="true">
				<BookCover {book} rounded="rounded-sm" />
			</a>
		{/if}
	</section>
{/if}

<style>
	.today {
		display: flex;
		align-items: center;
		gap: 1.5rem;
		min-block-size: 12rem;
		margin: 0.5rem 0 2rem;
	}
	/* Chapter only: nothing to reserve room for. */
	.today.solo {
		min-block-size: 0;
		padding: 1.5rem 1.75rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
	}
	.words {
		flex: 1;
		min-inline-size: 0;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.5rem;
	}
	.verse {
		margin: 0;
		font-family: var(--font-display);
		font-size: var(--fs-h2);
		line-height: 1.3;
		color: var(--text);
		text-wrap: pretty;
		max-inline-size: 34ch;
	}
	.ref {
		font-size: var(--fs-small);
		color: var(--muted);
	}
	.read {
		margin-block-start: 0.75rem;
	}
	.ghost {
		display: block;
		inline-size: min(100%, 26rem);
		block-size: 5.5rem;
		border-radius: var(--radius-sm);
		background: var(--surface-2);
	}
	.art {
		flex: none;
		inline-size: 7.5rem;
		transition: transform 0.2s;
	}
	.art:hover {
		transform: translateY(-2px);
	}
	@media (max-width: 639.98px) {
		.today {
			padding: 1.25rem;
			gap: 1rem;
			align-items: flex-start;
		}
		.verse {
			font-size: var(--fs-h3);
		}
		.art {
			inline-size: 4.5rem;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.art,
		.art:hover {
			transform: none;
			transition: none;
		}
	}
</style>
