<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import type { DailyReading, PlanDetail } from '$lib/library-public';
	import { planDayPath } from '$lib/editionHref';
	import { completePlanDay } from '$lib/planProgress.svelte';
	import { readingActivity } from '$lib/readingActivity.svelte';
	import { inputValue, isDateKey } from '$lib/dailyDate';
	import { assetHtml } from '$lib/assetUrl';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { contentLang } from '$lib/reading';
	import { authorPath } from '$lib/originals';
	import { bookChapterPath } from '$lib/reading-schema';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import PlanDayDone from '$lib/components/PlanDayDone.svelte';
	import PlanDayRemind from '$lib/components/PlanDayRemind.svelte';
	import PlanDayStrip from '$lib/components/PlanDayStrip.svelte';

	/**
	 * One day of a year-long devotional: just that entry, not its whole month —
	 * the verse and meditation under the book's own date line, with steps to
	 * the day either side, back to today, and into the book at this point.
	 * Client-rendered (see +page.ts); the book page's "Today's reading" leads
	 * here.
	 *
	 * Also a year-long plan's day (?plan=&day=, plan_seed.DAILY_PLANS): then the
	 * page is Day N of the plan, with the plan's bar, "mark day done" and its
	 * neighbouring days, in place of the calendar's.
	 */
	let {
		data
	}: {
		data: { reading: DailyReading; today: string; plan: PlanDetail | null; planDay: number };
	} = $props();
	const t = i18n.t;
	const r = $derived(data.reading);
	const book = $derived(r.book);
	const lang = $derived(contentLang(book.language));
	const isToday = $derived(r.requested === data.today);
	const bookHref = $derived(localizeHref(`/books/${book.slug}`));
	/** The day page for `d`, or for today. */
	const dayHref = (d?: string) => localizeHref(`/today/${book.slug}/${d ? `?d=${d}` : ''}`);
	// The month chapter, opened at this day's date line (the reader's ?p=). The
	// ORIGINAL edition on purpose, not `chapterPath`'s preferred one: the index
	// is counted on the original body, and a Modern English month's blocks need
	// not line up with it. Slashed before the query — the bare form is a 301.
	const inBook = $derived(
		localizeHref(`${bookChapterPath(book.slug, r.chapter, false)}/?p=${r.paragraph}`)
	);

	const plan = $derived(data.plan);
	const planDay = $derived(data.planDay);
	/** A neighbouring day of the plan, as a link, or "" past either end. */
	const planDayHref = (n: number) => {
		const d = plan?.days.find((x) => x.day === n);
		return plan && d ? localizeHref(planDayPath(plan.slug, d)) : '';
	};

	// Opening a day is reading, as opening a chapter is (saveProgress): it
	// counts toward the streak.
	onMount(() => readingActivity.recordToday());

	function completeDay() {
		if (plan) goto(localizeHref(completePlanDay(plan, planDay)));
	}

	// The trail's last crumb is this page (text, not a link).
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		...(plan
			? [
					{ name: t('nav.plans'), href: '/plans' },
					{ name: plan.title, href: `/plans/${plan.slug}` },
					{ name: `${t('plans.day')} ${planDay}`, href: `/plans/${plan.slug}#${planDay}` }
				]
			: [
					{ name: t('nav.books'), href: '/books' },
					{ name: book.title, href: `/books/${book.slug}` },
					{ name: t('plans.todaysReading'), href: `/today/${book.slug}` }
				])
	]);
	const eyebrow = $derived(
		plan ? `${t('plans.day')} ${planDay}` : isToday ? t('plans.todaysReading') : book.title
	);

	function pickDate(e: Event) {
		// yyyy-MM-DD → MM-DD
		const key = (e.currentTarget as HTMLInputElement).value.slice(5);
		if (isDateKey(key)) goto(dayHref(key));
	}
</script>

<svelte:head>
	<title>{r.label} — {book.title} — Ochorus</title>
	<!-- A different entry each day, drawn in the browser; the book page is the
	     one a crawler should have. -->
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="page-col daily-day px-5 py-10">
	<Breadcrumb items={crumbs} />

	{#if plan}
		<PlanDayStrip {plan} day={planDay} oncomplete={completeDay} class="mt-5" />
	{/if}

	<header class="mt-5 flex items-start gap-5">
		<a href={bookHref} class="w-16 shrink-0" aria-hidden="true" tabindex="-1">
			<BookCover {book} rounded="rounded-sm" />
		</a>
		<div class="min-w-0">
			<p class="eyebrow mb-1 text-accent">
				{eyebrow}
			</p>
			<h1 class="text-h1" {lang} dir="auto">{r.label}</h1>
			<p class="mt-1 text-muted">
				{#if isToday || plan}<a href={bookHref} class="hover:text-accent hover:underline" {lang} dir="auto">{book.title}</a>{' · '}{/if}<a
					href={localizeHref(authorPath(book.author.slug))}
					class="hover:text-accent hover:underline">{book.author.name}</a
				>
			</p>
		</div>
	</header>

	{#if r.date !== r.requested}
		<p class="mt-6 rounded-card border border-border bg-surface-2 px-4 py-3 text-small text-muted">
			{t('daily.missingDay')}
		</p>
	{/if}

	<article class="mt-8" {lang} dir="auto">
		{#if r.heading}<h2 class="text-h2 mb-4">{r.heading}</h2>{/if}
		<!-- Server-sanitized chapter HTML: the entry's own blocks, sliced from the
		     month chapter's served body (library/daily_readings). -->
		<!-- eslint-disable-next-line svelte/no-at-html-tags -->
		<div class="reading">{@html assetHtml(r.html)}</div>
	</article>

	{#if plan}
		{@const prev = planDayHref(planDay - 1)}
		{@const next = planDayHref(planDay + 1)}
		<nav class="mt-10 border-t border-border pt-6" aria-label={plan.title}>
			<div class="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
				{#if prev}
					<a href={prev} class="btn btn-ghost btn-sm justify-self-start" rel="prev"
						><Arrow back /> {t('plans.day')} {planDay - 1}</a
					>
				{/if}
				<div class="col-start-2"><PlanDayDone slug={plan.slug} day={planDay} oncomplete={completeDay} /></div>
				{#if next}
					<a href={next} class="btn btn-ghost btn-sm col-start-3 justify-self-end" rel="next"
						>{t('plans.day')} {planDay + 1} <Arrow /></a
					>
				{/if}
			</div>
			<div class="mt-5 text-small">
				<a href={inBook} class="font-semibold text-accent">{t('daily.inContext')} <Arrow /></a>
			</div>
		</nav>
		<!-- The plan's daily email, as a chapter's plan day offers it. -->
		<div class="mt-8">
			{#key `${plan.slug}:${planDay}`}
				<PlanDayRemind slug={plan.slug} day={planDay} dayCount={plan.day_count} />
			{/key}
		</div>
	{:else}
		<nav class="mt-10 border-t border-border pt-6" aria-label={t('daily.chooseDate')}>
			<div class="flex flex-wrap items-center justify-between gap-3">
				<a href={dayHref(r.prev)} class="btn btn-ghost btn-sm" rel="prev">
					<Arrow back />
					{t('daily.prevDay')}
				</a>
				{#if !isToday}
					<a href={dayHref()} class="btn btn-primary btn-sm">{t('daily.backToToday')}</a>
				{/if}
				<a href={dayHref(r.next)} class="btn btn-ghost btn-sm" rel="next">
					{t('daily.nextDay')}
					<Arrow />
				</a>
			</div>
			<div class="mt-5 flex flex-wrap items-center justify-between gap-3 text-small">
				<a href={inBook} class="font-semibold text-accent">{t('daily.inContext')} <Arrow /></a>
				<label class="flex items-center gap-2 text-muted">
					{t('daily.chooseDate')}
					<input
						type="date"
						class="rounded-md border border-border bg-surface px-2 py-1 text-text"
						value={inputValue(r.requested, new Date())}
						onchange={pickDate}
					/>
				</label>
			</div>
		</nav>
	{/if}
</div>

<style>
	/* A reading column, not a page of cards: the measure the reader keeps. */
	.daily-day {
		max-width: 46rem;
	}
</style>
