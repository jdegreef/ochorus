<script lang="ts">
	import { onMount } from 'svelte';
	import { watchToday } from '$lib/today';
	import { dateKey } from '$lib/dailyDate';
	import { loadTodayPicks, type TodayPicks } from '$lib/todayPicks';
	import { getLang } from '$lib/lang.svelte';
	import { contentLang, readingTime } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { loadCalendar, type Calendar } from '$lib/seasonCalendar';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	const t = i18n.t;

	/**
	 * Today (design #20): the day's verse, the devotional reading for this date
	 * and the sermon of the day, as three short columns in one quiet card
	 * (stacked on a phone), with a link to /today.
	 *
	 * The verse and the reading come from the dated devotionals' shelf — the
	 * one /today and DailyShelf draw — so outside English the verse is in the
	 * reader's language and Bible. English Scripture is the Open Word Bible
	 * (CLAUDE.md), so in English the shelf only supplies the day's references:
	 * the first one the Scripture API knows is shown in the OWB's words, tagged
	 * OWB. The sermon is SermonOfTheDay's pick (`pickDailySermon`). The three
	 * are fetched and chosen by $lib/todayPicks, shared with every other place
	 * that shows the day in one piece, so they agree. All of it
	 * is chosen CLIENT-SIDE with the reader's local date: home is prerendered,
	 * and a build-time pick would freeze on the day of the last deploy. So the
	 * baked HTML carries the card's skeleton, holding its height, and the real
	 * card takes its place at mount. A language with no devotional or no
	 * sermon drops that column; one with neither shows no card. The link to
	 * /today (every devotional's reading) goes with the devotionals: in a
	 * language with none, that page would only say so.
	 */

	let picks = $state<TodayPicks | null>(null);
	/** In Advent or Lent: the season's calendar ($lib/seasonCalendar), for the
	 *  row under the columns that leads to it on /today. Loaded with the picks,
	 *  so the card is drawn once. */
	let calendar = $state<Calendar | null>(null);
	let dateLabel = $state('');
	let pickedFor = '';

	// Re-picks only when the calendar day has moved: watchToday looks again on
	// a return to the tab and every few minutes while it is in view, so a page
	// left open over midnight turns over. Both lists are fetched fresh for the
	// new day — the sermon list too, as SermonOfTheDay does, so a failed fetch
	// is retried and the pick matches the sermons shelf's.
	async function loadToday(now: Date) {
		const key = dateKey(now);
		if (key === pickedFor) return;
		pickedFor = key;
		const lang = getLang();
		const [next, cal] = await Promise.all([loadTodayPicks(now, lang), loadCalendar(now, lang)]);
		if (key !== pickedFor) return;
		calendar = cal;
		dateLabel = now.toLocaleDateString(lang, { weekday: 'long', day: 'numeric', month: 'long' });
		picks = next;
	}

	onMount(() => watchToday((now) => void loadToday(now)));

	const columns = $derived(picks ? [picks.verse, picks.reading, picks.sermon].filter(Boolean).length : 3);
	// Static class names, so Tailwind sees each one.
	const GRID = ['', '', 'md:grid-cols-2', 'md:grid-cols-3'];
</script>

{#if !picks || columns}
	<section class="page-col px-5 pt-14" aria-busy={!picks}>
		<div class="rounded-2xl border border-border bg-surface px-5 py-6 sm:px-8 sm:py-7">
			{#if picks}
				<SectionHeader
					title={t('home.todayTitle')}
					subtitle={dateLabel}
					href={picks.reading ? localizeHref('/today') : ''}
					linkText={t('daily.seeAll')}
				/>
				<ul role="list" class="m-0 grid list-none p-0 {GRID[columns]}">
					{#if picks.verse}
						{@const v = picks.verse}
						<li class="col">
							<!-- Not a link: in English its words are the OWB's, elsewhere
							     another devotional's than the reading beside it, so no one
							     page stands for it. -->
							<span class="eyebrow block text-accent">{t('home.todayVerse')}</span>
							<span class="title verse mt-2 line-clamp-3 text-body" lang={v.lang} dir="auto">{v.text}</span>
							<span class="mt-2 block truncate text-small text-muted" lang={v.lang} dir="auto">{v.ref}</span>
						</li>
					{/if}
					{#if picks.reading}
						{@const r = picks.reading}
						<li class="col">
							<a class="today-link" href={localizeHref(`/today/${r.book.slug}/`)}>
								<span class="eyebrow block text-accent">{t('home.todayReading')}</span>
								<span class="title mt-2 line-clamp-2 text-h3" lang={contentLang(r.book.language)} dir="auto">{r.heading || r.book.title}</span>
								<span class="mt-2 block truncate text-small text-muted" lang={contentLang(r.book.language)} dir="auto"
									>{r.heading ? `${r.book.title} · ${r.book.author.name}` : r.book.author.name}</span
								>
							</a>
						</li>
					{/if}
					{#if picks.sermon}
						{@const s = picks.sermon}
						<li class="col">
							<a class="today-link" href={localizeHref(`/sermons/${s.slug}`)}>
								<span class="eyebrow block text-accent">{t('home.sermonOfDay')}</span>
								<span class="title mt-2 line-clamp-2 text-h3" dir="auto">{s.title}</span>
								<span class="mt-2 block truncate text-small text-muted"
									>{s.author.name} · {readingTime(s.word_count)}</span
								>
							</a>
						</li>
					{/if}
				</ul>
				{#if calendar}
					<a class="calendar-row mt-6 text-small font-semibold text-accent" href="{localizeHref('/today')}#calendar"
						>{t(calendar.window.season === 'advent' ? 'calendar.adventTitle' : 'calendar.lentTitle')} · {t(
							calendar.today ? 'calendar.openToday' : 'calendar.seeDoors'
						)} <Arrow /></a
					>
				{/if}
			{:else}
				<!-- The card's shape while the day is picked: the header's two lines,
				     then three columns of the same height as the real ones. -->
				<div aria-hidden="true">
					<div class="mb-6">
						<div class="skeleton h-8 w-28 rounded-md"></div>
						<div class="skeleton mt-2 h-4 w-44 rounded"></div>
					</div>
					<div class="grid {GRID[3]}">
						{#each [0, 1, 2] as i (i)}
							<div class="col">
								<div class="skeleton h-3 w-24 rounded"></div>
								<div class="skeleton mt-3 h-6 w-3/4 rounded"></div>
								<div class="skeleton mt-3 h-4 w-32 rounded"></div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</section>
{/if}

<style>
	/* Columns parted by a hairline: above each one after the first while they
	   stack, beside it once they sit in a row. In a row the height is the
	   tallest a column can be (eyebrow, three lines of verse, the reference),
	   so the skeleton and every mix of columns hold the same box. Stacked, it
	   is a typical column's (eyebrow, a one-line title, the byline), which the
	   skeleton's bars fit inside, rather than leave a gap under every short
	   one: a two-line title on a phone still grows the card a line. */
	.col {
		min-height: 6.5rem;
	}
	.col + .col {
		margin-block-start: 1.25rem;
		padding-block-start: 1.25rem;
		border-block-start: 1px solid var(--border);
	}
	@media (min-width: 48rem) {
		.col {
			min-height: 8.5rem;
		}
		.col + .col {
			margin-block-start: 0;
			padding-block-start: 0;
			border-block-start: 0;
			margin-inline-start: 1.5rem;
			padding-inline-start: 1.5rem;
			border-inline-start: 1px solid var(--border);
		}
	}
	/* A column is a link with no ground of its own, so it hovers the way the
	   Eight-for-today rows do: the title turns to accent, on hover and keyboard
	   focus alike. */
	.today-link {
		display: block;
		height: 100%;
		color: var(--color-text);
		text-decoration: none;
	}
	.title {
		font-family: var(--font-display);
		font-weight: 500;
		text-wrap: balance;
		transition: color var(--duration-fast);
	}
	/* The verse is read, not scanned: body size, book weight. No italic —
	   Arabic, Amharic and Hindi have none, and a browser would slant them. */
	.verse {
		font-weight: 400;
	}
	/* The season's calendar, under the columns: a hairline, then the link. */
	.calendar-row {
		display: block;
		padding-block-start: 1rem;
		border-block-start: 1px solid var(--border);
		text-decoration: none;
	}
	.today-link:hover .title,
	.today-link:focus-visible .title {
		color: var(--color-accent);
	}
</style>
