<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { authorPath } from '$lib/originals';
	import { localizeHref } from '$lib/href';
	import { getLang } from '$lib/lang.svelte';
	import { SITE_URL } from '$lib/config';
	import { readingActivity } from '$lib/readingActivity.svelte';
	import { readingGoal, BOOKS_GOAL_MAX, BOOKS_GOAL_MIN } from '$lib/readingGoal.svelte';
	import { readingPace } from '$lib/readingPace.svelte';
	import { localToday } from '$lib/streak';
	import { goalPace, yearStats, yearsWithData } from '$lib/yearInBooks';
	import type { BookSummary } from '$lib/library-public';
	import type { ProgressRecord, WorkKind } from '$lib/reading-schema';
	import BookCover from './BookCover.svelte';
	import Icon from './Icon.svelte';
	import ProgressBar from './ProgressBar.svelte';
	import ReadingHeatmap from './ReadingHeatmap.svelte';

	/**
	 * "Your year in books" on the Bookshelf: the yearly books goal and how the
	 * reader stands against it, the year in numbers, the covers finished, the
	 * reading calendar, and a Share. The numbers are yearInBooks.ts; the goal is
	 * readingGoal (a per-device target, like the weekly one).
	 *
	 * The year picker lists every year with a finished book or a day read; the
	 * goal can be set only for the current year (a goal for a year already gone
	 * isn't a goal), but a past year's goal still shows how it ended.
	 *
	 * `progress` comes from the page, which re-reads it on `ochorus:sync`; the
	 * activity log and the goal are reactive stores of their own.
	 */
	let {
		progress,
		books
	}: {
		progress: (ProgressRecord & { slug: string; kind: WorkKind })[];
		books: BookSummary[];
	} = $props();
	const t = i18n.t;

	const today = localToday();
	const thisYear = Number(today.slice(0, 4));
	const days = $derived(readingActivity.days());
	const years = $derived(yearsWithData(progress, days, thisYear));
	let year = $state(thisYear);

	const stats = $derived(
		yearStats({ progress, books, days, year, wpm: readingPace.wpm })
	);
	const goal = $derived(readingGoal.booksFor(year));
	const pace = $derived(goal ? goalPace(stats.finished, goal, today, year) : null);
	const hours = $derived(stats.words > 0 && stats.hours === 0 ? '<1' : String(stats.hours));

	// The calendar: this year so far, or the whole of a past one.
	const calendarEnd = $derived(year === thisYear ? today : `${year}-12-31`);
	const calendarWeeks = $derived.by(() => {
		const start = Date.parse(`${year}-01-01T00:00:00Z`);
		const end = Date.parse(`${calendarEnd}T00:00:00Z`);
		const jan1Weekday = new Date(start).getUTCDay();
		return Math.max(1, Math.ceil(((end - start) / 86_400_000 + 1 + jan1Weekday) / 7));
	});
	const yearDays = $derived(days.filter((d) => d.startsWith(`${year}-`)));

	let editing = $state(false);
	let draft = $state(12);
	function edit() {
		draft = goal ?? 12;
		editing = true;
	}
	function save(e: Event) {
		e.preventDefault();
		readingGoal.setBooks(year, draft);
		editing = false;
	}
	function removeGoal() {
		readingGoal.setBooks(year, null);
		editing = false;
	}

	let copied = $state(false);
	async function share() {
		const text = t('year.shareText')
			.replace('%y%', String(year))
			.replace('%b%', String(stats.finished))
			.replace('%h%', hours)
			.replace('%d%', String(stats.daysRead));
		const url = SITE_URL;
		if (typeof navigator.share === 'function') {
			try {
				await navigator.share({ text, url });
				return;
			} catch (err) {
				if ((err as Error)?.name === 'AbortError') return;
			}
		}
		try {
			await navigator.clipboard.writeText(`${text} ${url}`);
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch {
			/* no clipboard — nothing more to offer */
		}
	}

	const paceLabel = $derived.by(() => {
		if (!pace) return '';
		if (pace.status === 'met') return t('year.goalMet');
		if (pace.status === 'on') return t('year.paceOn');
		const key = pace.status === 'ahead' ? 'year.paceAhead' : 'year.paceBehind';
		return t(key).replace('%n%', String(pace.by));
	});
</script>

<section id="year" class="scroll-mt-24 pt-10" aria-labelledby="year-title">
	<div class="mb-4 flex flex-wrap items-baseline gap-3">
		<h2 id="year-title" class="text-h2">{t('year.title')}</h2>
		{#if years.length > 1}
			<select
				class="field w-auto"
				aria-label={t('year.choose')}
				value={year}
				onchange={(e) => {
					year = Number((e.currentTarget as HTMLSelectElement).value);
					editing = false;
				}}
			>
				{#each years as y (y)}
					<option value={y}>{y}</option>
				{/each}
			</select>
		{:else}
			<span class="rounded-full bg-surface-2 px-2.5 py-0.5 text-small font-semibold text-muted"
				>{year}</span
			>
		{/if}
	</div>

	<div class="rounded-card border border-border bg-surface p-4 sm:p-6">
		<!-- The goal: progress and pace, or the prompt to set one. -->
		{#if editing}
			<form class="flex flex-wrap items-end gap-3" onsubmit={save}>
				<label class="flex flex-col gap-1.5 text-small text-muted">
					{t('year.goalPrompt')}
					<input
						class="field w-28"
						type="number"
						inputmode="numeric"
						min={BOOKS_GOAL_MIN}
						max={BOOKS_GOAL_MAX}
						required
						bind:value={draft}
					/>
				</label>
				<button type="submit" class="btn btn-sm btn-primary">{t('common.save')}</button>
				<button type="button" class="btn btn-sm" onclick={() => (editing = false)}
					>{t('common.cancel')}</button
				>
				{#if goal}
					<button type="button" class="btn btn-sm btn-ghost text-danger" onclick={removeGoal}
						>{t('year.goalRemove')}</button
					>
				{/if}
			</form>
		{:else if goal && pace}
			<div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
				<div class="flex flex-wrap items-baseline gap-x-3">
					<span class="eyebrow text-accent">{t('year.goal')}</span>
					<span class="font-display text-h3 text-text"
						>{t('year.goalProgress')
							.replace('%n%', String(stats.finished))
							.replace('%g%', String(goal))}</span
					>
				</div>
				<span
					class="pace text-small font-semibold"
					class:met={pace.status === 'met'}
					class:behind={pace.status === 'behind'}
				>
					{#if pace.status === 'met' || pace.status === 'on' || pace.status === 'ahead'}
						<Icon name="check" size={14} />
					{/if}
					{paceLabel}
				</span>
			</div>
			<div class="mt-3">
				<ProgressBar
					size="md"
					percent={Math.min(100, Math.round((stats.finished / goal) * 100))}
					label="{t('year.goal')}: {stats.finished} / {goal}"
				/>
			</div>
			{#if year === thisYear}
				<button type="button" class="mt-2 text-small font-semibold text-accent" onclick={edit}
					>{t('year.goalChange')}</button
				>
			{/if}
		{:else if year === thisYear}
			<div class="flex flex-wrap items-center justify-between gap-3">
				<p class="m-0 text-body text-text">{t('year.goalPrompt')}</p>
				<button type="button" class="btn btn-sm btn-primary" onclick={edit}
					>{t('year.goalSet')}</button
				>
			</div>
		{/if}

		<!-- The year in numbers. -->
		<dl class="tiles mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
			<div class="tile">
				<dt>{t('year.statFinished')}</dt>
				<dd>{stats.finished}</dd>
			</div>
			<div class="tile">
				<dt>{t('year.statHours')}<span aria-hidden="true">*</span></dt>
				<dd>{hours}</dd>
			</div>
			<div class="tile">
				<dt>{t('year.statDays')}</dt>
				<dd>{stats.daysRead}</dd>
			</div>
			<div class="tile">
				<dt>{t('year.statLongest')}</dt>
				<dd>{stats.longestStreak}</dd>
			</div>
			{#if stats.topAuthor}
				<div class="tile col-span-2 sm:col-span-1">
					<dt>{t('year.statAuthor')}</dt>
					<dd class="name">
						<a href={localizeHref(authorPath(stats.topAuthor.slug))}>{stats.topAuthor.name}</a>
					</dd>
				</div>
			{/if}
		</dl>

		<!-- The covers finished that year. -->
		{#if stats.books.length}
			<ul class="mt-6 flex list-none flex-wrap gap-2 p-0">
				{#each stats.books as book (book.slug)}
					<li class="w-12 sm:w-14">
						<a href={localizeHref(`/books/${book.slug}`)} title={book.title} aria-label={book.title}>
							<BookCover {book} rounded="rounded-sm" />
						</a>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="mt-6 mb-0 text-small text-muted">{t('year.empty')}</p>
		{/if}

		<!-- Capped: stretched across the full page a year's cells grow to ~25px
		     and the calendar outweighs everything above it. -->
		<div class="mt-6 max-w-3xl">
			<ReadingHeatmap days={yearDays} today={calendarEnd} locale={getLang()} weeks={calendarWeeks} />
		</div>

		<div class="mt-5 flex flex-wrap items-center justify-between gap-3">
			<p class="m-0 max-w-prose text-micro text-muted">* {t('year.hoursNote')}</p>
			<button type="button" class="btn btn-sm" onclick={share} aria-live="polite">
				{copied ? t('year.copied') : t('year.share')}
			</button>
		</div>
	</div>
</section>

<style>
	.pace {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		color: var(--color-accent);
	}
	.pace.met {
		color: var(--color-gold);
	}
	.pace.behind {
		color: var(--color-muted);
	}
	.tile {
		display: block;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface-2);
		padding: 0.9rem 0.75rem;
		text-align: center;
	}
	.tile dt {
		font-size: var(--fs-eyebrow);
		color: var(--color-muted);
	}
	.tile dd {
		margin: 0.15rem 0 0;
		font-family: var(--font-display);
		font-size: var(--fs-h2);
		font-weight: 600;
		color: var(--color-text);
	}
	.tile dd.name {
		font-size: var(--fs-body);
		line-height: 1.3;
		margin-top: 0.4rem;
	}
</style>
