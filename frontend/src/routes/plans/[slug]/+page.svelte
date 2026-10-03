<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { planDayPath } from '$lib/editionHref';
	import type { PlanDay, PlanDetail, PlanSummary } from '$lib/library-public';
	import { planProgress } from '$lib/planProgress.svelte';
	import { planTimeLeft, readingMinutes, readingTime } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { authorPath } from '$lib/originals';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumbLd } from '$lib/seo';
	import { LANDSCAPE_HEIGHT, LANDSCAPE_WIDTH } from '$lib/coverArt';
	import { planCardUrl } from '$lib/planCard';
	import { localizeHref } from '$lib/href';
	import { getLang } from '$lib/lang.svelte';
	import LanguageFallbackNotice from '$lib/components/LanguageFallbackNotice.svelte';
	import { editionSeo, languageFallback } from '$lib/languageFallback';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import PlanShelfCard from '$lib/components/PlanShelfCard.svelte';
	import { groupPlanDays, weeksOf, type PlanGroup } from '$lib/planGroups';
	import Icon from '$lib/components/Icon.svelte';

	let { data } = $props();
	const plan = $derived<PlanDetail>(data.plan);
	/** "More like this": up to three plans sharing a book or writer (see relatedPlans), from the loader. */
	const related = $derived<PlanSummary[]>(data.related);
	const t = i18n.t;

	// Self-referential canonical + hreflang — an English canonical here would
	// deindex the translated plan pages. A plan materializes per language only
	// once its source books are all translated, so hreflang lists only the
	// locales this plan actually exists in.
	const path = $derived(`/plans/${plan.slug}/`);
	// A missing edition renders the English one (see languageFallback).
	const fallback = $derived(languageFallback(getLang(), plan.language));
	const seo = $derived(editionSeo(path, plan.available_languages, fallback));
	const hreflang = $derived(seo.hreflang);
	const canonical = $derived(seo.canonical);
	/** The day list's sections: runs of days by book (see planGroups). One run
	 *  (a single-book plan) draws no section chrome — the header already says it. */
	const groups = $derived(groupPlanDays(plan.days));
	const grouped = $derived(groups.length > 1);
	// The distinct books the plan reads through, in first-appearance order, for
	// the ItemList JSON-LD. Article days are left out: they have no book page.
	const planBooks = $derived([
		...new Map(groups.filter((g) => g.bookSlug).map((g) => [g.bookSlug, g.bookTitle]))
	].map(([slug, title]) => ({ slug, title })));
	const coverBySlug = $derived(new Map(plan.covers.map((c) => [c.slug, c])));
	/** "Daughters of the King: Three Months with God" set as a title over its
	 *  subtitle, as a book's is (plans have no subtitle field of their own). */
	const titleParts = $derived.by(() => {
		const m = plan.title.match(/^(.+?)\s*[:：]\s+(.+)$/u);
		return m ? { main: m[1], sub: m[2] } : { main: plan.title, sub: '' };
	});
	const groupWords = (g: PlanGroup) => g.days.reduce((s, d) => s + (d.word_count || 0), 0);
	/** The line under a day's title: its book, or "Article" on an article day. */
	const daySource = (d: PlanDay) => (d.article_slug ? t('search.typeArticle') : d.book_title);
	/** A day's title — the API has already dropped the book's own "Day 13 — ",
	 *  which would contradict the plan day in the circle. */
	const dayTitle = (d: PlanDay) => d.chapter_title || `${t('plans.day')} ${d.day}`;
	const dayRange = (g: { first: number; last: number }) =>
		g.first === g.last
			? `${t('plans.day')} ${g.first}`
			: `${t('plans.daysLabel')} ${g.first}–${g.last}`;
	const planLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'ItemList',
			name: plan.title,
			description: plan.description || undefined,
			numberOfItems: plan.day_count,
			inLanguage: plan.language,
			url: canonical,
			itemListElement: planBooks.map((b, i) => ({
				'@type': 'ListItem',
				position: i + 1,
				name: b.title,
				url: `${SITE_URL}${localizeHref(`/books/${b.slug}`)}`
			}))
		})
	);
	// One crumb trail feeds both the visible <Breadcrumb> and the JSON-LD.
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('plans.title'), href: '/plans' },
		{ name: plan.title, href: `/plans/${plan.slug}` }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));

	const started = $derived(planProgress.isStarted(plan.slug));
	const next = $derived(planProgress.nextDay(plan.slug, plan.day_count));
	const doneSet = $derived(new Set(planProgress.doneDays(plan.slug)));
	const doneCount = $derived(doneSet.size);
	const pct = $derived(plan.day_count ? Math.round((doneCount / plan.day_count) * 100) : 0);
	const daysLeft = $derived(Math.max(0, plan.day_count - doneCount));
	/** Words still to read across the days not yet marked done. */
	const wordsLeft = $derived(
		plan.days.filter((d) => !doneSet.has(d.day)).reduce((s, d) => s + (d.word_count || 0), 0)
	);

	const nextDay = $derived(next === null ? undefined : plan.days.find((d) => d.day === next));
	/** Where the day list opens: the next reading as of arriving on this plan.
	 *  Held, not derived from `next`, so ticking a day off doesn't snap its week
	 *  shut under the reader's cursor (and a week they opened stays open). Set
	 *  in an effect so it lands after hydration: the prerender opened on Day 1,
	 *  and progress is client-only. */
	let openAt = $state<number | null>(1);
	$effect(() => {
		void plan.slug;
		openAt = untrack(() => next);
	});
	// "Day 5 of 31 · 27 days left · 4 hr 11 min left" — the read card's eyebrow.
	const progressLine = $derived(
		[
			`${t('plans.day')} ${next} ${t('plans.of')} ${plan.day_count}`,
			t('plans.daysLeft').replace('%n%', String(daysLeft)),
			wordsLeft ? planTimeLeft(readingMinutes(wordsLeft)) : ''
		]
			.filter(Boolean)
			.join(' · ')
	);

	/** Today, once mounted — the finish date is the reader's, never the build's:
	 *  a prerendered date would be stale by the next morning. */
	let today = $state<Date | null>(null);
	onMount(() => (today = new Date()));
	const finishDate = $derived.by(() => {
		if (!today) return '—';
		const end = new Date(today);
		end.setDate(end.getDate() + daysLeft - 1);
		return new Intl.DateTimeFormat(getLang(), { month: 'short', day: 'numeric' }).format(end);
	});
	/** The plan's shape at a glance: how long, how much a day, how many books,
	 *  and when a reader going a day at a time from today would finish. */
	const facts = $derived(
		[
			{ value: String(plan.day_count), label: t('plans.days') },
			plan.total_words && plan.day_count
				? { value: `~${readingMinutes(plan.total_words / plan.day_count)}`, label: t('plans.minPerDay') }
				: null,
			planBooks.length
				? {
						value: String(planBooks.length),
						label: planBooks.length === 1 ? t('common.bookOne') : t('common.bookMany')
					}
				: null,
			next === null ? null : { value: finishDate, label: t('plans.finishLabel') }
		].filter((f) => f !== null)
	);

	const dayHref = (day: number) => {
		const d = plan.days.find((x) => x.day === day);
		return d ? localizeHref(planDayPath(plan.slug, d)) : '#';
	};
</script>

<!-- The plan's own card, in the language of the plan shown (a page that fell
     back names that language's card) — drawn by scripts/build-plan-cards.mjs. -->
<Seo
	title="{plan.title} — Ochorus"
	description={plan.description}
	{canonical}
	{hreflang}
	ogImage={absUrl(planCardUrl(plan.slug, plan.language))}
	ogImageWidth={LANDSCAPE_WIDTH}
	ogImageHeight={LANDSCAPE_HEIGHT}
	ogImageAlt={plan.title}
	structuredData={[planLd, crumbsLd]}
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<LanguageFallbackNotice {fallback} alternates={hreflang.alternates} browsePath="/plans" />

	<!-- The hero: the plan's books fanned large beside its title (the covers
	     ARE the picture, as on /originals), and its shape as four facts — how
	     long, how much a day, how many books, and when you'd finish. -->
	<section class="plan-hero">
		<div class="min-w-0">
			<p class="eyebrow mb-1 text-muted">
				{t('search.typePlan')} · {plan.day_count} {t('plans.days')}{#if plan.total_words} ·
					{readingTime(plan.total_words)}{/if}
			</p>
			<h1 class="text-h1" dir="auto">{titleParts.main}</h1>
			{#if titleParts.sub}
				<!-- As the book page draws a subtitle. -->
				<p class="mt-1 text-h3 text-muted" dir="auto">{titleParts.sub}</p>
			{/if}
			{#if plan.description}
				<p class="mt-3 max-w-xl text-body text-muted" dir="auto">{plan.description}</p>
			{/if}
			<dl class="plan-facts">
				{#each facts as f (f.label)}
					<div class="plan-fact">
						<dt class="text-eyebrow text-muted">{f.label}</dt>
						<dd class="font-display text-h3 font-semibold text-text tabular-nums">{f.value}</dd>
					</div>
				{/each}
			</dl>
		</div>
		{#if plan.covers.length}
			<div class="plan-hero-fan">
				<CoverStrip covers={plan.covers} size="fan" priority />
			</div>
		{/if}
	</section>

	<!-- Two columns from a laptop up: the day list, and beside it a panel that
	     stays put while it scrolls — the next reading, Save/Share, the writers.
	     On a phone the panel comes first, so the one action leads. -->
	<div class="plan-body">
		<aside class="plan-aside">
			<!-- The read card, as on the book page: the reading that's next, named —
			     its book and length, and for a started plan how far through you are —
			     with the one read verb. A first visit (and the prerender, since plan
			     progress is client-only) gets Day 1 with the "Free to read · No account
			     needed" reassurance. Save and Share sit quietly beneath. -->
			{#if next !== null}
				<div class="read-card">
					<div class="read-card-body">
						{#if started}
							<p class="text-small text-muted">{progressLine}</p>
						{:else}
							<p class="text-small">
								<span class="font-medium text-accent">{t('book.freeToRead')}</span><span
									class="px-1.5 opacity-50">·</span
								><span class="text-muted">{t('book.noAccount')}</span>
							</p>
						{/if}
						{#if nextDay}
							<p class="read-card-title" dir="auto">
								{dayTitle(nextDay)}
							</p>
							<p class="text-small text-muted" dir="auto">
								<!-- The separator as an expression: literal spaces at an {#if}
								     boundary are compiler-trimmed ("Prayer·9 min"). -->
								{daySource(nextDay)}{#if nextDay.word_count}<span class="opacity-60">{' · '}</span
									>{readingMinutes(nextDay.word_count)} {t('common.min')}{/if}
							</p>
						{/if}
						{#if started}
							<div class="mt-2">
								<ProgressBar
									percent={pct}
									label="{plan.title}: {doneCount} {t('plans.of')} {plan.day_count} {t('plans.days')}"
								/>
							</div>
						{/if}
					</div>
					<div class="read-card-cta">
						<a href={dayHref(next)} class="btn btn-primary" onclick={() => planProgress.start(plan.slug)}>
							{started ? t('plans.continue') : t('plans.start')}
						</a>
					</div>
				</div>
			{:else}
				<!-- A status line, not a control: a finished plan has no action, so it
				     must not wear a button's chrome (it read as a disabled button). -->
				<p class="text-small font-medium text-muted">✓ {t('plans.finished')}</p>
			{/if}

			<div class="mt-3 flex flex-wrap items-center gap-2">
				<FavoriteButton kind="plan" slug={plan.slug} showLabel />
				<ShareButton url={canonical} title={plan.title} showLabel />
			</div>

			<!-- The writers this plan reads through — a link to each author page, so a
			     plan is a way into their work, not only a sequence of chapters. Reuses the
			     shared "Authors" label, so it is already translated in every locale. -->
			{#if plan.authors?.length}
				<section class="mt-6">
					<h2 class="section-heading">{t('search.groupAuthors')}</h2>
					<p class="text-body">
						{#each plan.authors as a, i (a.slug)}<a
								href={localizeHref(authorPath(a.slug))}
								class="font-medium text-text hover:text-accent hover:underline">{a.name}</a
							>{i < plan.authors.length - 1 ? ' · ' : ''}{/each}
					</p>
				</section>
			{/if}
		</aside>

		<div class="plan-main">
			<!-- The day list, shaped: grouped by the book each run of days reads (a
			     collapsible section per book, the current one open), and each long run
			     cut into weeks (the current week open) — so a 96-day plan reads as three
			     books of five weeks, not one column of 96 rows. Native <details>: every
			     day stays in the prerendered HTML for crawlers and no-JS readers, and the
			     open state needs no script. Progress is client-only, so the prerender
			     opens on Day 1 and hydration moves it to where the reader is. -->
			<section aria-labelledby="plan-days-heading">
				<h2 id="plan-days-heading" class="section-heading">{t('plans.inThisPlan')}</h2>
				{#each groups as g, gi (g.key)}
					{@const hasNext = openAt !== null && openAt >= g.first && openAt <= g.last}
					{#if grouped}
						{@const read = g.days.filter((d) => doneSet.has(d.day)).length}
						{@const cover = g.bookSlug ? coverBySlug.get(g.bookSlug) : undefined}
						<details class="plan-group" open={hasNext || (openAt === null && gi === 0)}>
							<summary class="plan-group-head">
								{#if cover}<CoverStrip covers={[cover]} max={1} />{/if}
								<span class="min-w-0 flex-1">
									<span class="eyebrow block text-muted">{dayRange(g)}</span>
									<span class="plan-group-title" dir="auto">{g.bookTitle || t('search.groupArticles')}</span>
									<span class="block text-small text-muted">
										{#if started && read}
											{t('plans.readOf').replace('%n%', String(read)).replace('%m%', String(g.days.length))}
										{:else}
											{g.days.length} {t('plans.days')} · {readingTime(groupWords(g))}
										{/if}
									</span>
								</span>
								<Icon name="chevron-right" size={20} class="chevron" mirror={false} />
							</summary>
							<div class="plan-group-body">
								{#if g.bookSlug}
									<a href={localizeHref(`/books/${g.bookSlug}`)} class="text-small font-medium text-accent hover:underline"
										>{t('plans.aboutBook')}<Icon name="chevron-right" size={14} class="ms-0.5 inline" /></a
									>
								{/if}
								{@render weekList(g.days, hasNext)}
							</div>
						</details>
					{:else}
						{@render weekList(g.days, hasNext)}
					{/if}
				{/each}
			</section>
		</div>
	</div>

	<!-- A run of days, in weeks when it is longer than one. The week holding the
	     next reading opens; in a run that doesn't hold it, the first week does. -->
	{#snippet weekList(days: PlanDay[], hasNext: boolean)}
		{@const weeks = weeksOf(days)}
		{#if weeks.length > 1}
			{#each weeks as w, wi (w[0].day)}
				{@const last = w[w.length - 1]}
				<details class="plan-week" open={hasNext ? openAt! >= w[0].day && openAt! <= last.day : wi === 0}>
					<summary class="plan-week-head">
						<span class="font-semibold text-text">{t('plans.week').replace('%n%', String(wi + 1))}</span>
						<span class="min-w-0 flex-1 truncate text-muted">
							{dayRange({ first: w[0].day, last: last.day })}<span class="hidden sm:inline"
								>{' · '}{dayTitle(w[0])} – {dayTitle(last)}</span
							>
						</span>
						{#if started}
							<span class="sr-only"
								>{t('plans.readOf')
									.replace('%n%', String(w.filter((d) => doneSet.has(d.day)).length))
									.replace('%m%', String(w.length))}</span
							>
						{/if}
						<span class="week-dots" aria-hidden="true">
							{#each w as d (d.day)}<span class="week-dot" class:done={doneSet.has(d.day)}></span>{/each}
						</span>
						<Icon name="chevron-right" size={16} class="chevron" mirror={false} />
					</summary>
					{@render dayRows(w)}
				</details>
			{/each}
		{:else}
			{@render dayRows(days)}
		{/if}
	{/snippet}

	{#snippet dayRows(days: PlanDay[])}
		<ol class="divide-y divide-border">
			{#each days as d (d.day)}
				{@const done = doneSet.has(d.day)}
				{@const isNext = d.day === next}
				{@const markLabel = t('plans.markDayDoneNum').replace('%n%', String(d.day))}
				<li
					class="flex items-center gap-4 py-3 transition-opacity hover:opacity-100"
					class:opacity-55={done && !isNext}
				>
					<button
						type="button"
						onclick={() => planProgress.toggleDone(plan.slug, d.day)}
						aria-pressed={done}
						aria-label={markLabel}
						title={done ? t('plans.dayDoneNum').replace('%n%', String(d.day)) : markLabel}
						class="day-toggle flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-small font-semibold transition-colors hover:border-accent"
						class:border-accent={isNext}
						class:text-accent={isNext && !done}
						class:border-border={!isNext}
						class:bg-accent={done}
						class:text-accent-contrast={done}
						class:text-muted={!done && !isNext}
					>
						{done ? '✓' : d.day}
					</button>
					<a
						href={dayHref(d.day)}
						class="flex min-w-0 flex-1 items-center gap-4 hover:no-underline"
						onclick={() => planProgress.start(plan.slug)}
					>
						<span class="min-w-0 flex-1">
							<span class="block truncate text-body text-text" class:font-semibold={isNext} dir="auto">
								{dayTitle(d)}
							</span>
							<!-- The book is named once, on its section — not under every day. -->
							<span class="block text-small text-muted">
								{#if d.article_slug}{t('search.typeArticle')}<span class="opacity-60">{' · '}</span>{/if}{#if d.key_verse}<span
										class="sm:hidden">{d.key_verse}<span class="opacity-60">{' · '}</span></span
									>{/if}{readingMinutes(d.word_count || 0)} {t('common.min')}
							</span>
						</span>
						{#if d.key_verse}
							<span class="tag verse-chip hidden sm:inline-flex">{d.key_verse}</span>
						{/if}
						{#if isNext}
							<span class="shrink-0 text-small font-semibold text-accent">{t('plans.today')}</span>
						{/if}
					</a>
				</li>
			{/each}
		</ol>
	{/snippet}

	<!-- More like this: where to go once this plan is done — the plans sharing
	     its books or writers, drawn as they are on the /plans shelf. Computed in
	     the load so it prerenders; absent (no heading) when nothing relates or
	     the list failed to load. Reuses the book page's "More like this" key. -->
	{#if related.length}
		<section class="mt-12">
			<h2 class="section-heading">{t('book.related')}</h2>
			<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
				{#each related as rel (rel.slug)}
					<PlanShelfCard plan={rel} headingLevel={3} />
				{/each}
			</div>
		</section>
	{/if}
</div>

<style>
	/* A book's run of days: a card whose summary is the book (cover, span,
	   progress) and whose body is its weeks. */
	.plan-group {
		margin-top: 0.75rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.plan-group-head {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 0.875rem 1rem;
		cursor: pointer;
		list-style: none;
		border-radius: inherit;
	}
	.plan-group-head::-webkit-details-marker,
	.plan-week-head::-webkit-details-marker {
		display: none;
	}
	.plan-group-title {
		display: block;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		line-height: 1.25;
		color: var(--text);
	}
	.plan-group-body {
		padding: 0 1rem 0.5rem;
	}
	/* Down when closed, up when open (QandA's turn) — a rotation, so no RTL flip. */
	summary > :global(.chevron) {
		flex-shrink: 0;
		color: var(--muted);
		transform: rotate(90deg);
		transition: transform var(--duration-fast) ease;
	}
	details[open] > summary > :global(.chevron) {
		transform: rotate(-90deg);
	}
	@media (prefers-reduced-motion: reduce) {
		summary > :global(.chevron) {
			transition: none;
		}
	}
	/* A week: a quiet header line with one dot per day (filled once read). */
	.plan-week {
		border-top: 1px solid var(--border);
	}
	.plan-group-body > a + .plan-week,
	.plan-group-body > a + ol {
		margin-top: 0.5rem;
	}
	.plan-week-head {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		min-height: 2.75rem;
		font-size: var(--fs-small);
		cursor: pointer;
		list-style: none;
	}
	.week-dots {
		display: flex;
		gap: 0.25rem;
	}
	.week-dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 999px;
		border: 1.5px solid var(--border-strong);
	}
	.week-dot.done {
		border-color: var(--accent);
		background: var(--accent);
	}
	/* The verse a day opens on: a .tag pill, as a label rather than a link. */
	.verse-chip {
		flex-shrink: 0;
		color: var(--muted);
	}
	.verse-chip:hover {
		border-color: var(--border);
	}
	/* The hero: words beside the fan; on a phone the fan leads, centred. */
	.plan-hero {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 20rem;
		gap: 2.5rem;
		align-items: center;
		padding-block: 0.5rem 2rem;
	}
	.plan-facts {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 0.625rem;
		max-width: 40rem;
		margin-top: 1.5rem;
	}
	.plan-fact {
		display: flex;
		flex-direction: column-reverse;
		justify-content: flex-end;
		padding: 0.75rem 0.875rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface-2);
	}
	/* minmax(0, 1fr), not the implicit auto track: a truncating week summary's
	   min-content width would otherwise widen the column past a phone. */
	.plan-body {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 2rem;
	}
	@media (min-width: 1024px) {
		.plan-body {
			grid-template-columns: minmax(0, 1fr) 20rem;
			align-items: start;
			gap: 3rem;
		}
		.plan-main {
			grid-column: 1;
			grid-row: 1;
		}
		.plan-aside {
			grid-column: 2;
			grid-row: 1;
			position: sticky;
			top: calc(var(--pinned-offset, var(--appnav-h, 0px)) + 1rem);
		}
	}
	@media (max-width: 640px) {
		.plan-hero {
			grid-template-columns: minmax(0, 1fr);
			gap: 0.5rem;
			padding-block: 0 1.5rem;
		}
		.plan-hero-fan {
			order: -1;
			width: min(18rem, 80%);
			margin-inline: auto;
		}
		.plan-facts {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
</style>
