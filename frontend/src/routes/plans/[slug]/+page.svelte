<script lang="ts">
	import { scrollEdges } from '$lib/actions/scrollEdges';
	import { onMount, untrack } from 'svelte';
	import { page } from '$app/state';
	import { planDayPath } from '$lib/editionHref';
	import type { PlanDay, PlanDetail, PlanSummary } from '$lib/library-public';
	import { planProgress } from '$lib/planProgress.svelte';
	import { contentLang, planMinutesPerDay, planTimeLeft, readingMinutes, readingTime } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { ORIGINALS_SLUG, authorPath } from '$lib/originals';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumbLd } from '$lib/seo';
	import { LANDSCAPE_HEIGHT, LANDSCAPE_WIDTH } from '$lib/coverArt';
	import { planCardUrl } from '$lib/planCard';
	import { localizeHref } from '$lib/href';
	import { getLang } from '$lib/lang.svelte';
	import ForPromo from '$lib/components/ForPromo.svelte';
	import LanguageFallbackNotice from '$lib/components/LanguageFallbackNotice.svelte';
	import { editionSeo, languageFallback } from '$lib/languageFallback';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import PlanTogetherBanner from '$lib/components/PlanTogetherBanner.svelte';
	import PlanTogetherShare from '$lib/components/PlanTogetherShare.svelte';
	import PlanStartRemind from '$lib/components/PlanStartRemind.svelte';
	import Portrait from '$lib/components/Portrait.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import PlanGarden from '$lib/components/PlanGarden.svelte';
	import { planMeta } from '$lib/emblemNames';
	import PlanShelfCard from '$lib/components/PlanShelfCard.svelte';
	import { groupPlanDays, weeksOf, type PlanGroup } from '$lib/planGroups';
	import { elementVisible, jumpToSection } from '$lib/scrollSpy.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import PlanCalendar from '$lib/components/PlanCalendar.svelte';
	import ReadBar from '$lib/components/ReadBar.svelte';
	import { readJSON, writeJSON } from '$lib/persisted';

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
	/** Too many books for a label each (the Bible in a Year's 66): the rail
	 *  draws each book as one bar, filled as far as it is read, unlabelled. A
	 *  one-book plan keeps its ticks however long it is. */
	const denseRail = $derived(groups.length > 12);
	// The distinct books the plan reads through, in first-appearance order, for
	// the ItemList JSON-LD. Article days are left out: they have no book page.
	const planBooks = $derived([
		...new Map(groups.filter((g) => g.bookSlug).map((g) => [g.bookSlug, g.bookTitle]))
	].map(([slug, title]) => ({ slug, title })));
	const coverBySlug = $derived(new Map(plan.covers.map((c) => [c.slug, c])));
	/** The writers to meet — not the house imprint (see the hero byline). */
	const writers = $derived((plan.authors ?? []).filter((a) => a.slug !== ORIGINALS_SLUG));
	/** "Daughters of the King: Three Months with God" set as a title over its
	 *  subtitle, as a book's is (plans have no subtitle field of their own). */
	const titleParts = $derived.by(() => {
		const m = plan.title.match(/^(.+?)\s*[:：]\s+(.+)$/u);
		return m ? { main: m[1], sub: m[2] } : { main: plan.title, sub: '' };
	});
	const groupWords = (g: PlanGroup) => g.days.reduce((s, d) => s + (d.word_count || 0), 0);
	/** The line under a day's title: its book, or "Article" on an article day. */
	const daySource = (d: PlanDay) =>
		d.article_slug ? t('search.typeArticle') : (bookName.get(d.book_slug) ?? d.book_title);
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
	/** The day the reader has just marked read here, which the garden grows
	 *  into flower — only a tap on this page, never progress synced in. Held
	 *  just long enough for the grow to play (sprout included), then let go,
	 *  so a sync or a later render draws rather than grows. */
	let justRead = $state<number | null>(null);
	const GROW_MS = 3000;
	let growTimer: ReturnType<typeof setTimeout> | undefined;
	function grewDay(day: number) {
		justRead = day;
		clearTimeout(growTimer);
		growTimer = setTimeout(() => (justRead = null), GROW_MS);
	}
	$effect(() => () => clearTimeout(growTimer));
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
		justRead = null; // a tap on the last plan opened grows nothing on this one
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
	/** The date `n` days from today (call only once `today` is set). */
	const dayFrom = (n: number) => {
		const d = new Date(today!);
		d.setDate(d.getDate() + n);
		return d;
	};
	// Built once per language, not on every progress change.
	const dateFmt = $derived({
		monthDay: new Intl.DateTimeFormat(getLang(), { month: 'long', day: 'numeric' }),
		weekday: new Intl.DateTimeFormat(getLang(), { weekday: 'short' }),
		day: new Intl.DateTimeFormat(getLang(), { day: 'numeric' })
	});
	const finishDate = $derived(today ? dateFmt.monthDay.format(dayFrom(daysLeft - 1)) : '');
	/** One read count for a run of days — a book section, a week, a rail segment. */
	const readIn = (days: PlanDay[]) => days.filter((d) => doneSet.has(d.day)).length;
	const perDay = $derived(planMinutesPerDay(plan));
	/** The plan's shape in one sentence (design review #24, in place of the
	 *  stat boxes): "12 days · about 8 minutes a day · finish on 17 November if
	 *  you start today". The finish date is the reader's, so it joins once
	 *  mounted; a started plan counts from the days still to read. */
	const factsLine = $derived(
		[
			`${plan.day_count} ${t('plans.days')}`,
			// "1 book" says nothing the cover beside it doesn't.
			planBooks.length > 1 ? `${planBooks.length} ${t('common.bookMany')}` : '',
			perDay ? t('plans.aboutMinPerDay').replace('%n%', String(perDay)) : '',
			next !== null && finishDate
				? t(started ? 'plans.finishReadingDaily' : 'plans.finishIfStart').replace('%d%', () => finishDate)
				: ''
		]
			.filter(Boolean)
			.join(' · ')
	);

	/** The jump chips' targets and labels: one per book section. Volumes of ONE
	 *  series (a shared cover title, distinct series_position) are named by
	 *  their number ("Book 1"); anything else by its title. */
	const groupId = (g: PlanGroup) => `plan-${g.key}`;
	const groupLabels = $derived.by(() => {
		const tiles = groups.map((g) => coverBySlug.get(g.bookSlug));
		const positions = tiles.map((c) => c?.series_position);
		const series = new Set(tiles.map((c) => c?.cover_title));
		const numbered =
			positions.every((n) => n) &&
			new Set(positions).size === positions.length &&
			series.size === 1 &&
			!series.has('');
		return groups.map((g, i) => {
			if (!numbered) return { chip: g.bookTitle || t('search.groupArticles'), name: g.bookTitle };
			// A series' volumes share one long title ("Daughters of the King – 30
			// Days with God for Girls – Book 1"); what tells them apart is the
			// number and the subtitle's head ("Beloved: who you are…"), so they
			// are named "Book 1 · Beloved" — the whole title is a tap away on
			// the book's page.
			const chip = t('originals.volume').replace('%n%', String(positions[i]));
			// Only a "Head: the rest" subtitle has a head to borrow; any other
			// shape keeps the book's own title.
			const head = tiles[i]?.subtitle?.match(/^(.{1,40}?)\s*[:：]/u)?.[1];
			return { chip, name: head ? `${chip} · ${head}` : g.bookTitle };
		});
	});
	/** Each book's display name, by slug — the section heads and the read card. */
	const bookName = $derived(
		new Map(groups.map((g, i) => [g.bookSlug, groupLabels[i].name] as const).filter(([s]) => s))
	);
	/** A chip opens the section it jumps to — a closed <details> would land the
	 *  reader on a bare header — then jumps the shared way (reduced-motion aware). */
	const openSection = (e: MouseEvent, id: string) => {
		const el = document.getElementById(id);
		if (!(el instanceof HTMLDetailsElement)) return;
		e.preventDefault();
		el.open = true;
		jumpToSection(id);
	};

	const nextCover = $derived(nextDay?.book_slug ? coverBySlug.get(nextDay.book_slug) : undefined);
	/** The next few unread days after today's, each with the date it falls on
	 *  for a reader going a day at a time (client-only, like the finish date). */
	const comingUp = $derived.by(() => {
		if (!started || next === null) return [];
		const out: (PlanDay & { date: string })[] = [];
		for (let i = plan.days.findIndex((d) => d.day > next); i >= 0 && i < plan.days.length; i++) {
			const d = plan.days[i];
			if (doneSet.has(d.day)) continue;
			const on: Date | null = today ? dayFrom(out.length + 1) : null;
			// "Sat 3": weekday then day, whatever order a combined format picks.
			out.push({ ...d, date: on ? `${dateFmt.weekday.format(on)} ${dateFmt.day.format(on)}` : '' });
			if (out.length === 3) break;
		}
		return out;
	});

	/** The phone's bottom bar shows the read verb only once the read card has
	 *  scrolled away — never two primaries on screen (the book page's rule). */
	let readCardEl = $state<HTMLElement>();
	/** The pinned book chips' height, measured, for --pinned-offset. */
	let jumpH = $state(0);
	/** The day list as a list, or laid on real dates. The calendar is about the
	 *  reader's today, so it exists only once mounted (the prerender is the list). */
	let view = $state<'list' | 'calendar'>('list');
	const VIEW_KEY = 'ochorus:plan-view';
	// The reader's last choice of view, as a device preference (grid/list on
	// the shelves is the same idea); read on mount, so the prerender is the list.
	// `?view=calendar` (the end of a plan day's "Add to my calendar") opens the
	// calendar for this visit only, at the days, without changing that choice.
	// An effect on the URL, not a mount: the read card's "Add to my calendar"
	// (PlanStartRemind) links here from this same page, which a client-side
	// navigation doesn't remount. (In an effect, so the prerender never reads
	// the query.)
	onMount(() => {
		if (readJSON<string>(VIEW_KEY, 'list') === 'calendar') view = 'calendar';
	});
	$effect(() => {
		if (page.url.searchParams.get('view') !== 'calendar') return;
		view = 'calendar';
		requestAnimationFrame(() => document.getElementById('plan-days-heading')?.scrollIntoView());
	});
	// "Start the plan" starts it and opens day 1 — nothing in between. The
	// daily reminder is offered beside it as one quiet line (PlanStartRemind,
	// design review #24), never a sheet in the way: one here asked about
	// tomorrow before they had read a line (2026-10 UX audit). The end of each
	// day offers it again (PlanDayRemind signed in, ChapterEndAsk signed out).
	function startPlan() {
		planProgress.start(plan.slug);
	}

	const setView = (v: 'list' | 'calendar') => {
		view = v;
		writeJSON(VIEW_KEY, v);
	};
	const sections = $derived(groups.map((g, i) => ({ key: g.key, label: groupLabels[i].chip, days: g.days })));
	const cardSeen = elementVisible(() => readCardEl, { initial: true });

	/** Each day's link, built once per plan — the list, the read card, Coming
	 *  up and the phone bar all look theirs up. */
	const hrefByDay = $derived(new Map(plan.days.map((d) => [d.day, localizeHref(planDayPath(plan.slug, d))])));
	const dayHref = (day: number) => hrefByDay.get(day) ?? '#';
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

<!-- --pinned-offset: the app nav plus the book chips pinned over the list —
     what every section jump clears. -->
<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {jumpH}px)">
	<Breadcrumb items={crumbs} />

	<LanguageFallbackNotice {fallback} alternates={hreflang.alternates} browsePath="/plans" />

	<!-- The hero, as the book page's (design review #24): the plan's books
	     beside its title — a fan of its covers, or the one cover — then its
	     writers, its shape in one sentence, and the read card right under that,
	     where the eye already is, on every width. -->
	<section class="plan-hero" class:no-art={!plan.covers.length}>
		{#if plan.covers.length}
			{@const solo = plan.covers.length === 1}
			<div class="plan-hero-art" class:solo>
				<CoverStrip covers={plan.covers} size={solo ? 'one' : 'fan'} priority />
			</div>
		{/if}
		<div class="plan-hero-head min-w-0">
			<p class="eyebrow mb-1 text-muted">
				<!-- The separator as an expression: a literal space at an {#if}
				     boundary is compiler-trimmed ("Reading plan· 3 hr"). The day
				     count leads the facts line below, so it isn't said twice. -->
				{t('search.typePlan')}{#if plan.total_words}{' · '}{readingTime(plan.total_words)}{/if}
			</p>
			<!-- The whole title stays the h1's text; its subtitle is drawn as the
			     book page draws one. -->
			<h1 class="text-h1" dir="auto" lang={contentLang(plan.language)}>
				{titleParts.main}{#if titleParts.sub}<span class="sr-only">{': '}</span><span
						class="mt-1 block text-h3 font-normal text-muted">{titleParts.sub}</span
					>{/if}
			</h1>
			<!-- The writers this plan reads through, each a small portrait and a
			     link to their page — so a plan is a way into their work. The house
			     imprint alone (an Ochorus Originals plan) is no writer to meet. -->
			{#if writers.length}
				<ul class="plan-byline">
					{#each writers as a (a.slug)}
						<li>
							<a href={localizeHref(authorPath(a.slug))} class="plan-writer text-body text-accent hover:underline">
								<Portrait slug={a.slug} name={a.name} url={a.photo_url} px={28} class="h-7 w-7" initialsClass="text-micro" decorative />
								<span>{a.name}</span>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
		<div class="plan-hero-about min-w-0">
			{#if plan.description}
				<p class="max-w-xl text-body text-muted" dir="auto">{plan.description}</p>
			{/if}
			<p class="mt-3 text-small font-medium text-text">{factsLine}</p>
		</div>

		<div class="plan-hero-start min-w-0">
			<PlanTogetherBanner slug={plan.slug} dayCount={plan.day_count} {today} {dayHref} />
			<!-- The read card, as on the book page: the reading that's next, named —
			     its book and length, and for a started plan how far through you are —
			     with the one read verb. A first visit (and the prerender, since plan
			     progress is client-only) gets Day 1 with the "Free to read · No account
			     needed" reassurance, and the daily reminder offered beside Start. -->
			{#if next !== null}
				<div class="read-card" bind:this={readCardEl}>
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
							<!-- Today's reading, named and pictured: its book's cover beside
							     the title, and the verse the day opens on. -->
							<div class="mt-1 flex items-start gap-3">
								<!-- One book: the hero's cover already is this one. -->
								{#if nextCover && planBooks.length > 1}<CoverStrip covers={[nextCover]} size="lg" max={1} />{/if}
								<div class="min-w-0">
									<p class="read-card-title" dir="auto">
										{dayTitle(nextDay)}
									</p>
									<p class="text-small text-muted" dir="auto">
										<!-- The separator as an expression: literal spaces at an {#if}
										     boundary are compiler-trimmed ("Prayer·9 min"). -->
										{daySource(nextDay)}{#if nextDay.word_count}<span class="opacity-60">{' · '}</span
											>{readingMinutes(nextDay.word_count)} {t('common.min')}{/if}
									</p>
									{#if nextDay.key_verse}
										<span class="tag verse-chip mt-2">{nextDay.key_verse}</span>
									{/if}
								</div>
							</div>
						{/if}
						{#if started}
							<!-- How far through, as a garden: a flower for each day read, a
							     sprout for today, seeds for the days ahead (PlanGarden). -->
							<div class="mt-3">
								<PlanGarden
									dayCount={plan.day_count}
									done={doneSet}
									{next}
									grow={justRead}
									hue={planMeta(plan.slug).accent}
									label="{plan.title}: {doneCount} {t('plans.of')} {plan.day_count} {t('plans.days')}"
								/>
							</div>
						{/if}
					</div>
					<div class="read-card-cta">
						<a href={dayHref(next)} class="btn btn-primary btn-solid" onclick={startPlan}>
							{started ? t('plans.continue') : t('plans.start')}
						</a>
						{#if started}
							<button type="button" class="btn btn-ghost" onclick={() => {
									if (next === null) return;
									grewDay(next);
									planProgress.markDone(plan.slug, next);
								}}
							>
								{t('plans.markDone')}
							</button>
						{/if}
					</div>
					{#if !started}
						<div class="read-card-remind">
							<PlanStartRemind slug={plan.slug} />
						</div>
					{/if}
				</div>
			{:else}
				<!-- A status line, not a control: a finished plan has no action, so it
				     must not wear a button's chrome (it read as a disabled button). -->
				<p class="text-small font-medium text-muted">✓ {t('plans.finished')}</p>
				<!-- The garden in full flower — and on the tap that finished the plan,
				     its last flower grows in here (justRead), not lost with the card. -->
				<div class="mt-3">
					<PlanGarden
						dayCount={plan.day_count}
						done={doneSet}
						next={null}
						grow={justRead}
						hue={planMeta(plan.slug).accent}
						label="{plan.title}: {doneCount} {t('plans.of')} {plan.day_count} {t('plans.days')}"
					/>
				</div>
				<ForPromo place="plan-done" class="mt-2" />
			{/if}

			<div class="mt-3 flex flex-wrap items-center gap-2">
				<FavoriteButton kind="plan" slug={plan.slug} showLabel />
				<ShareButton url={canonical} title={plan.title} showLabel />
			</div>
		</div>
	</section>

	<!-- The day list, and from a laptop up a panel beside it that stays put
	     while it scrolls — the secondary things only: reading it with a group,
	     and (once started) the next few days. The one action is in the hero.
	     On a phone the panel follows the days. -->
	<div class="plan-body">
		<div class="plan-main">
			<!-- The day list, shaped: grouped by the book each run of days reads (a
			     collapsible section per book, the current one open), and each long run
			     cut into weeks (the current week open) — so a 96-day plan reads as three
			     books of five weeks, not one column of 96 rows. Native <details>: every
			     day stays in the prerendered HTML for crawlers and no-JS readers, and the
			     open state needs no script. Progress is client-only, so the prerender
			     opens on Day 1 and hydration moves it to where the reader is. -->
			<!-- The journey rail, once started: every day as a tick in its book's
			     run — read, today, still to come, in the series segments' colours.
			     Decorative: the read card's progress bar says it in words. -->
			{#if started}
				<div class="plan-rail" class:dense={denseRail} aria-hidden="true">
					{#each groups as g, gi (g.key)}
						<div class="rail-seg" style="flex-grow: {g.days.length}">
							{#if denseRail}
								<div
									class="rail-bar stage-mark"
									class:reading={next !== null && next >= g.first && next <= g.last}
								>
									<span class="stage-mark done" style="width: {(readIn(g.days) / g.days.length) * 100}%"></span>
								</div>
							{:else}
							<div class="rail-ticks">
								{#each g.days as d (d.day)}
									<span
										class="rail-tick stage-mark"
										class:done={doneSet.has(d.day)}
										class:reading={d.day === next}
									></span>
								{/each}
							</div>
							<div class="rail-label text-micro text-muted">
								<span>{grouped ? groupLabels[gi].chip : dayRange(g)}</span><span class="tabular-nums"
									>{readIn(g.days)}/{g.days.length}</span
								>
							</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			<section aria-labelledby="plan-days-heading">
				<h2 id="plan-days-heading" class="section-heading">{t('plans.inThisPlan')}</h2>
				{#if today}
					<!-- The view toggle on its own row under the heading, as the shelves
					     place theirs. -->
					<div class="seg mb-4 w-fit" role="group" aria-labelledby="plan-days-heading">
						<button type="button" class:active={view === 'list'} aria-pressed={view === 'list'} onclick={() => setView('list')}
							>{t('plans.viewList')}</button
						>
						<button
							type="button"
							class:active={view === 'calendar'}
							aria-pressed={view === 'calendar'}
							onclick={() => setView('calendar')}>{t('plans.viewCalendar')}</button
						>
					</div>
				{/if}
				{#if view === 'calendar' && today}
					<!-- Keyed on the plan: its choices are seeded per plan, so moving to
					     another plan re-seeds rather than carrying these over. -->
					{#key plan.slug}
						<PlanCalendar {plan} {today} {started} {doneSet} {sections} {dayHref} {dayTitle} />
					{/key}
				{:else}
					<!-- One chip per book, pinned while the list scrolls: a jump to (and
					     open of) that book's section. Anchors, so every day stays in the
					     prerendered page. -->
					{#if grouped}
						<nav
							class="plan-jump chip-scroller"
							use:scrollEdges
							aria-label={t('nav.books')}
							bind:clientHeight={jumpH}
						>
							{#each groups as g, gi (g.key)}
								<a class="tag" href="#{groupId(g)}" onclick={(e) => openSection(e, groupId(g))} dir="auto"
									>{groupLabels[gi].chip}</a
								>
							{/each}
						</nav>
					{/if}
					{#each groups as g, gi (g.key)}
						{@const hasNext = openAt !== null && openAt >= g.first && openAt <= g.last}
						{#if grouped}
							{@const read = readIn(g.days)}
							{@const cover = g.bookSlug ? coverBySlug.get(g.bookSlug) : undefined}
							<details id={groupId(g)} class="plan-group" open={hasNext || (openAt === null && gi === 0)}>
								<summary class="plan-group-head">
									{#if cover}<CoverStrip covers={[cover]} max={1} size="lg" />{/if}
									<span class="min-w-0 flex-1">
										<span class="eyebrow block text-muted">{dayRange(g)}</span>
										<span class="plan-group-title" dir="auto"
											>{groupLabels[gi].name || t('search.groupArticles')}</span
										>
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
				{/if}
			</section>
		</div>
		<aside class="plan-aside">
			<!-- "Read together", said in one line before it is offered (its
			     button names it, so no heading says it twice). -->
			<p class="mb-2 text-small text-muted">{t('together.hint')}</p>
			<PlanTogetherShare slug={plan.slug} title={plan.title} url={canonical} {today} />

			<!-- What comes after today: the next few days, dated for a reader going
			     a day at a time. -->
			{#if comingUp.length}
				<section class="mt-8" aria-labelledby="coming-up-heading">
					<h2 id="coming-up-heading" class="section-heading">{t('plans.comingUp')}</h2>
					<ol class="divide-y divide-border">
						{#each comingUp as d (d.day)}
							<li>
								<a href={dayHref(d.day)} class="coming-row">
									<span class="coming-date text-small font-semibold text-muted tabular-nums">{d.date}</span>
									<span class="min-w-0 flex-1">
										<span class="block truncate text-body text-text" dir="auto">{dayTitle(d)}</span>
										<span class="block text-small text-muted"
											>{t('plans.day')} {d.day} · {readingMinutes(d.word_count || 0)} {t('common.min')}</span
										>
									</span>
								</a>
							</li>
						{/each}
					</ol>
				</section>
			{/if}
		</aside>
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
									.replace('%n%', String(readIn(w)))
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
						onclick={() => {
							if (!done) grewDay(d.day);
							planProgress.toggleDone(plan.slug, d.day);
						}}
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
								{#if d.article_slug}{t('search.typeArticle')}<span class="sep">{' · '}</span>{/if}{#if d.key_verse}<span
										class="sm:hidden">{d.key_verse}<span class="sep">{' · '}</span></span
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

	<!-- A leader reading this with a group: the page made for them — at the
	     end, once the plan itself has been seen (design review #24). -->
	<ForPromo place="plan" class="mt-12" />
</div>

<!-- Once the read card scrolls away, the read verb rides a bar at the foot of
     the screen (ReadBar, shared with the book page) — on every width: the card
     is in the hero now, not in a panel that sticks. -->
<ReadBar
	show={next !== null && !!nextDay && !cardSeen.visible}
	eyebrow="{t('plans.day')} {next} {t('plans.of')} {plan.day_count}"
	title={nextDay ? dayTitle(nextDay) : ''}
	href={next === null ? '#' : dayHref(next)}
	label={started ? t('plans.continue') : t('plans.start')}
	onread={() => planProgress.start(plan.slug)}
/>

<style>
	/* A book's run of days: a card whose summary is the book (cover, span,
	   progress) and whose body is its weeks. */
	.plan-group,
	.plan-rail {
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	/* "Add to my calendar" (`?view=calendar`) lands on the days, clear of the
	   app nav and the pinned chips too. */
	#plan-days-heading {
		scroll-margin-top: calc(var(--pinned-offset) + 0.5rem);
	}
	/* A book section lands clear of the app nav and the pinned chips. */
	.plan-group {
		margin-top: 0.75rem;
		scroll-margin-top: calc(var(--pinned-offset) + 0.5rem);
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
		border-radius: var(--radius-pill);
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
	/* The hero, the book page's shape: the picture beside the title, the
	   about lines and the read card full width beneath on a phone; from 640px
	   the picture spans the rows and everything else stacks beside it. */
	.plan-hero {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		column-gap: 1rem;
		align-items: start;
		padding-block: 0.5rem 2rem;
	}
	.plan-hero-art {
		width: 9.5rem;
	}
	.plan-hero-art.solo {
		width: 6.5rem;
	}
	.plan-hero-about,
	.plan-hero-start {
		grid-column: 1 / -1;
		margin-top: 1rem;
	}
	.plan-hero-start {
		max-width: 36rem;
	}
	.plan-byline {
		display: flex;
		flex-wrap: wrap;
		gap: 0.375rem 1rem;
		margin-top: 0.75rem;
	}
	.plan-writer {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}
	.read-card-remind {
		flex-basis: 100%;
		padding-top: 0.625rem;
		border-top: 1px solid var(--border);
	}
	@media (min-width: 640px) {
		.plan-hero {
			grid-template-rows: auto auto auto 1fr;
			column-gap: 2rem;
		}
		.plan-hero-art {
			grid-row: 1 / -1;
			width: 16rem;
		}
		.plan-hero-art.solo {
			width: 11rem;
		}
		.plan-hero-about,
		.plan-hero-start {
			grid-column: 2;
		}
	}
	@media (min-width: 1024px) {
		.plan-hero-art {
			width: 19rem;
		}
		.plan-hero-art.solo {
			width: 12rem;
		}
	}
	/* No covers to show (an articles-only plan): one column, every width. */
	.plan-hero.no-art {
		grid-template-columns: minmax(0, 1fr);
	}
	.plan-hero.no-art > * {
		grid-column: 1;
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
			/* The app nav only: the pinned book chips live in the other column. */
			top: calc(var(--appnav-h, 0px) + 1rem);
			/* Taller than a short laptop screen: it scrolls itself rather than
			   hiding its foot until the page scrolls past it. */
			max-height: calc(100vh - var(--appnav-h, 0px) - var(--dockbar-h, 0px) - 2rem);
			max-height: calc(100dvh - var(--appnav-h, 0px) - var(--dockbar-h, 0px) - 2rem);
			overflow-y: auto;
		}
	}
	.plan-jump {
		position: sticky;
		top: var(--appnav-h, 0px);
		z-index: 10;
		padding-block: 0.5rem;
		background: var(--bg);
	}
	/* The rail: one tick a day, a book's run per segment. */
	.plan-rail {
		display: flex;
		gap: 0.75rem;
		margin-bottom: 2rem;
		padding: 1rem;
	}
	.rail-seg {
		flex-basis: 0;
		min-width: 0;
	}
	.rail-ticks {
		display: flex;
		align-items: flex-end;
		gap: 2px;
		height: 2rem;
	}
	/* Colours from .stage-mark (done / reading), as the series segments wear. */
	.rail-tick {
		flex: 1 1 0;
		min-width: 1px;
		height: 1.25rem;
		border-radius: 2px;
	}
	.rail-tick.reading {
		height: 2rem;
	}
	.plan-rail.dense {
		gap: 2px;
	}
	.rail-bar {
		display: flex;
		height: 1.25rem;
		overflow: hidden;
		border-radius: 2px;
	}
	.rail-label {
		display: flex;
		justify-content: space-between;
		gap: 0.5rem;
		margin-top: 0.5rem;
		white-space: nowrap;
	}
	/* Coming up: a date block beside each of the next few days. */
	.coming-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		min-height: 2.75rem;
		padding-block: 0.5rem;
		color: var(--text);
	}
	.coming-row:hover {
		text-decoration: none;
	}
	.coming-date {
		width: 3.5rem;
		flex-shrink: 0;
	}
</style>
