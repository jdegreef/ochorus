<script lang="ts">
	import { onMount } from 'svelte';
	import { getTimeFit, type TimeFit } from '$lib/library-public';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { editionHref } from '$lib/editionHref';
	import { allProgress } from '$lib/progress';
	import { readingPace } from '$lib/readingPace.svelte';
	import { chapterNameIn, contentLang, readingTime } from '$lib/reading';
	import {
		DEFAULT_TIME,
		TIME_CHOICES,
		TIME_KEY,
		daySeed,
		parseTime,
		readingPlaces,
		wordWindow,
		type TimeChoice
	} from '$lib/timeFit';
	import BookCover from '$lib/components/BookCover.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';

	const t = i18n.t;

	/**
	 * "How long do you have?" — pick 5, 15, 30 or 60 minutes and get a chapter
	 * and a sermon that fit, at the reader's own pace (`$lib/timeFit`, the API's
	 * `/api/library/fit/`). The chapter carries on a book the reader is in the
	 * middle of where one fits, else opens a well-known one. Fetched on mount
	 * with the reader's places, pace and day, so it renders the same in the
	 * static build and the app: nothing about it is baked. The choice is
	 * remembered on this device (a preference, not reading data).
	 */
	let minutes = $state<TimeChoice>(DEFAULT_TIME);
	let fit = $state<TimeFit | null>(null);
	let failed = $state(false);
	let request = 0;

	function load() {
		const id = ++request;
		const { min, max } = wordWindow(minutes, readingPace.wpm);
		const language = getLang();
		getTimeFit({
			language,
			minWords: min,
			maxWords: max,
			seed: daySeed(new Date()),
			reading: readingPlaces(allProgress(), language)
		})
			.then((r) => {
				if (id !== request) return;
				fit = r;
				failed = false;
			})
			.catch(() => {
				if (id !== request) return;
				failed = true;
			});
	}

	function choose(m: TimeChoice) {
		if (m === minutes) return;
		minutes = m;
		try {
			localStorage.setItem(TIME_KEY, String(m));
		} catch {
			// Private mode / storage off: the choice just isn't remembered.
		}
		load();
	}

	onMount(() => {
		try {
			minutes = parseTime(localStorage.getItem(TIME_KEY));
		} catch {
			minutes = DEFAULT_TIME;
		}
		load();
	});

	const label = (m: TimeChoice) => (m === 60 ? t('today.timeHour') : `${m} ${t('common.min')}`);
</script>

<section aria-labelledby="time-picker">
	<h2 id="time-picker" class="section-label">{t('today.timeTitle')}</h2>
	<div class="seg time-seg mb-5" role="group" aria-label={t('today.timeTitle')}>
		{#each TIME_CHOICES as m (m)}
			<button
				type="button"
				class:active={minutes === m}
				aria-pressed={minutes === m}
				onclick={() => choose(m)}>{label(m)}</button
			>
		{/each}
	</div>

	<div aria-live="polite">
		{#if failed}
			<p class="text-muted">{t('common.loadError')}</p>
		{:else if fit && !fit.chapter && !fit.sermon}
			<p class="text-muted">{t('today.timeNone')}</p>
		{:else if fit}
			<div class="sermon-list">
				{#if fit.chapter}
					{@const c = fit.chapter}
					<a
						class="fit-row"
						href={editionHref(`/books/${c.book.slug}/${c.order}`, c.book.language)}
						lang={contentLang(c.book.language)}
					>
						<!-- Decorative: the row names the book in words. -->
						<span class="fit-cover" aria-hidden="true"><BookCover book={c.book} rounded="rounded-sm" /></span>
						<span class="min-w-0">
							<span class="eyebrow block text-accent" dir="auto"
								>{c.continuing ? t('today.timeContinue') : t('today.timeStart')} · {c.book.title}</span
							>
							<span class="fit-title" dir="auto">{chapterNameIn(c.order, c.title, c.book.title)}</span>
							<span class="block text-small text-muted"
								>{c.book.author.name}{' '}<span class="sep" aria-hidden="true">·</span>{' '}<span
									class="whitespace-nowrap">{readingTime(c.word_count)}</span
								></span
							>
						</span>
					</a>
				{/if}
				{#if fit.sermon}
					<SermonCard sermon={fit.sermon} showAuthor />
				{/if}
			</div>
		{:else}
			<div class="skeleton h-24 max-w-3xl rounded-card" aria-hidden="true"></div>
		{/if}
	</div>
</section>

<style>
	.time-seg {
		display: inline-flex;
	}
	/* The shape of a SermonCard row (hairline above, same padding), with the
	   book's cover where a sermon row has its words alone. */
	.fit-row {
		display: flex;
		align-items: flex-start;
		gap: 0.85rem;
		padding-block: 0.75rem;
		border-block-start: 1px solid var(--border);
		color: var(--text);
		text-decoration: none;
	}
	.fit-row:first-child {
		border-block-start-color: transparent;
	}
	.fit-cover {
		flex: none;
		width: 2.75rem;
	}
	.fit-title {
		display: block;
		margin-block: 0.15rem;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		line-height: 1.3;
		text-wrap: balance;
		transition: color var(--duration-fast);
	}
	.fit-row:hover .fit-title,
	.fit-row:focus-visible .fit-title {
		color: var(--accent);
		text-decoration: underline;
		text-underline-offset: 0.15em;
		text-decoration-thickness: 1px;
	}
</style>
