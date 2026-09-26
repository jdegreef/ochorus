<script lang="ts">
	import type { PlanDetail } from '$lib/library-public';
	import { planProgress } from '$lib/planProgress.svelte';
	import { planTimeLeft, readingMinutes, readingTime } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { authorPath } from '$lib/originals';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumbLd } from '$lib/seo';
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

	let { data } = $props();
	const plan = $derived<PlanDetail>(data.plan);
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
	// The distinct books the plan reads through, in first-appearance order, with
	// the span of days each occupies. Powers both the ItemList JSON-LD and the
	// "In this plan" preview — a reader sees the shape of the journey (which
	// works, in what order, over how many days) before committing.
	const planBooks = $derived.by(() => {
		const map = new Map<string, { slug: string; title: string; first: number; last: number; days: number }>();
		for (const d of plan.days) {
			let e = map.get(d.book_slug);
			if (!e) {
				e = { slug: d.book_slug, title: d.book_title, first: d.day, last: d.day, days: 0 };
				map.set(d.book_slug, e);
			}
			e.last = d.day;
			e.days++;
		}
		return [...map.values()];
	});
	const dayRange = (b: { first: number; last: number }) =>
		b.first === b.last
			? `${t('plans.day')} ${b.first}`
			: `${t('plans.daysLabel')} ${b.first}–${b.last}`;
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

	const dayHref = (day: number) => {
		const d = plan.days.find((x) => x.day === day);
		return d ? localizeHref(`/books/${d.book_slug}/${d.chapter_order}?plan=${plan.slug}&day=${day}`) : '#';
	};
</script>

<Seo
	title="{plan.title} — Ochorus"
	description={plan.description}
	{canonical}
	{hreflang}
	ogImage={absUrl('/og/plans.png')}
	structuredData={[planLd, crumbsLd]}
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<LanguageFallbackNotice {fallback} alternates={hreflang.alternates} browsePath="/plans" />

	<div class="flex items-start justify-between gap-4">
		<div class="min-w-0 flex-1">
			<p class="eyebrow mb-1 text-muted">
				{t('search.typePlan')} · {plan.day_count} {t('plans.days')}{#if plan.total_words} ·
					{readingTime(plan.total_words)}{/if}
			</p>
			<h1 class="text-h1 mb-2">{plan.title}</h1>
			<p class="mb-6 max-w-xl text-body text-muted">{plan.description}</p>
		</div>
		{#if plan.covers.length}
			<div class="hidden shrink-0 pt-1 sm:block">
				<CoverStrip covers={plan.covers} max={5} />
			</div>
		{/if}
	</div>

	<!-- The read card, as on the book page: the reading that's next, named —
	     its book and length, and for a started plan how far through you are —
	     with the one read verb. A first visit (and the prerender, since plan
	     progress is client-only) gets Day 1 with the "Free to read · No account
	     needed" reassurance. Save and Share sit quietly beneath. -->
	{#if next !== null}
		<div class="read-card">
			<div class="min-w-0 flex-1">
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
						{nextDay.chapter_title || `${t('plans.day')} ${nextDay.day}`}
					</p>
					<p class="text-small text-muted" dir="auto">
						<!-- The separator as an expression: literal spaces at an {#if}
						     boundary are compiler-trimmed ("Prayer·9 min"). -->
						{nextDay.book_title}{#if nextDay.word_count}<span class="opacity-60">{' · '}</span
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

	<!-- Preview: the works this plan reads through, in order, with day spans —
	     so a reader sees the whole journey before starting. Multi-book plans
	     benefit most; a single-book plan is already summarised in the header. -->
	{#if planBooks.length > 1}
		<section class="mt-8">
			<h2 class="section-heading">
				{t('plans.inThisPlan')}
			</h2>
			<ol class="space-y-2.5">
				{#each planBooks as b (b.slug)}
					<li class="flex items-baseline justify-between gap-3">
						<a
							href={localizeHref(`/books/${b.slug}`)}
							class="min-w-0 text-body font-medium text-text hover:text-accent hover:underline"
						>
							{b.title}
						</a>
						<span class="shrink-0 text-small tabular-nums text-muted">{dayRange(b)}</span>
					</li>
				{/each}
			</ol>
		</section>
	{/if}

	<!-- The writers this plan reads through — a link to each author page, so a
	     plan is a way into their work, not only a sequence of chapters. Reuses the
	     shared "Authors" label, so it is already translated in every locale. -->
	{#if plan.authors?.length}
		<section class="mt-8">
			<h2 class="section-heading">{t('search.groupAuthors')}</h2>
			<p class="text-body">
				{#each plan.authors as a, i (a.slug)}<a
						href={localizeHref(authorPath(a.slug))}
						class="font-medium text-text hover:text-accent hover:underline">{a.name}</a
					>{i < plan.authors.length - 1 ? ' · ' : ''}{/each}
			</p>
		</section>
	{/if}

	<ol class="mt-8 divide-y divide-border">
		{#each plan.days as d (d.day)}
			{@const done = doneSet.has(d.day)}
			{@const isNext = d.day === next}
			<li
				class="flex items-center gap-4 py-4 transition-opacity hover:opacity-100"
				class:opacity-55={done && !isNext}
			>
				<button
					type="button"
					onclick={() => planProgress.toggleDone(plan.slug, d.day)}
					aria-pressed={done}
					aria-label={done ? t('plans.dayDone') : t('plans.markDone')}
					title={done ? t('plans.dayDone') : t('plans.markDone')}
					class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-small font-semibold transition-colors hover:border-accent"
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
						<span class="block truncate text-body text-text" class:font-semibold={isNext}>
							{d.chapter_title || `${t('plans.day')} ${d.day}`}
						</span>
						<span class="block text-small text-muted">
							{d.book_title}{#if d.word_count}
								<span class="opacity-60"> · </span>{readingMinutes(d.word_count)} {t('common.min')}{/if}
						</span>
					</span>
					{#if isNext}
						<span class="shrink-0 text-small font-semibold text-accent">{t('plans.today')}</span>
					{/if}
				</a>
			</li>
		{/each}
	</ol>
</div>
