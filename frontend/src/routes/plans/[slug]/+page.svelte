<script lang="ts">
	import type { PlanDetail } from '$lib/library';
	import { planProgress } from '$lib/planProgress.svelte';
	import { readingMinutes, readingTime } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumb } from '$lib/seo';
	import { localizeHref, locales } from '$lib/paraglide/runtime';
	import CoverStrip from '$lib/components/CoverStrip.svelte';

	let { data } = $props();
	const plan = $derived<PlanDetail>(data.plan);
	const t = i18n.t;

	// Self-referential canonical + hreflang per locale (mirrors topics/[slug]) —
	// an English canonical here would deindex the translated plan pages.
	const path = $derived(`/plans/${plan.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const alternates = $derived(
		locales.map((loc) => ({ loc, href: `${SITE_URL}${localizeHref(path, { locale: loc })}` }))
	);
	// The distinct books the plan reads through (first appearance), for an ItemList.
	const planBooks = $derived.by(() => {
		const seen = new Set<string>();
		const out: { slug: string; title: string }[] = [];
		for (const d of plan.days) {
			if (!seen.has(d.book_slug)) {
				seen.add(d.book_slug);
				out.push({ slug: d.book_slug, title: d.book_title });
			}
		}
		return out;
	});
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
				url: `${SITE_URL}/books/${b.slug}`
			}))
		})
	);
	const crumbsLd = $derived(
		jsonLd(
			breadcrumb([
				{ name: t('common.home'), url: '/' },
				{ name: t('plans.title'), url: '/plans' },
				{ name: plan.title, url: `/plans/${plan.slug}` }
			])
		)
	);

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

	const dayHref = (day: number) => {
		const d = plan.days.find((x) => x.day === day);
		return d ? localizeHref(`/books/${d.book_slug}/${d.chapter_order}?plan=${plan.slug}&day=${day}`) : '#';
	};
</script>

<svelte:head>
	<title>{plan.title} — Ochorus</title>
	<meta name="description" content={plan.description} />
	<link rel="canonical" href={canonical} />
	{#each alternates as a (a.loc)}
		<link rel="alternate" hreflang={a.loc} href={a.href} />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_URL}{localizeHref(path, { locale: 'en' })}" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="{plan.title} — Ochorus" />
	<meta property="og:description" content={plan.description} />
	<meta property="og:url" content={canonical} />
	{@html planLd}
	{@html crumbsLd}
</svelte:head>

<div class="mx-auto max-w-3xl px-5 py-10">
	<nav class="mb-5 text-small text-muted" aria-label={t('a11y.breadcrumb')}>
		<a href={localizeHref('/plans')} class="hover:text-text">{t('plans.title')}</a>
		<span> › </span>
		<span class="text-text">{plan.title}</span>
	</nav>

	<div class="flex items-start justify-between gap-4">
		<div class="min-w-0 flex-1">
			<h1 class="text-h1 mb-2">{plan.title}</h1>
			<p class="mb-3 max-w-xl text-body text-muted">{plan.description}</p>
			<p class="mb-6 text-small text-muted">
				{plan.day_count} {t('plans.days')}{#if plan.total_words}
					<span class="opacity-60"> · </span>{readingTime(plan.total_words)}{/if}
			</p>
		</div>
		{#if plan.covers.length}
			<div class="hidden shrink-0 pt-1 sm:block">
				<CoverStrip covers={plan.covers} max={5} />
			</div>
		{/if}
	</div>

	{#if next !== null}
		<a href={dayHref(next)} class="btn btn-primary" onclick={() => planProgress.start(plan.slug)}>
			{started ? t('plans.continue') : t('plans.start')} — {t('plans.day')}
			{next} {t('plans.of')} {plan.day_count}
		</a>
	{:else}
		<p class="btn btn-ghost pointer-events-none inline-block">✓ {t('plans.finished')}</p>
	{/if}

	{#if started && next !== null}
		<div class="mt-6 max-w-md">
			<div class="mb-2 flex items-baseline justify-between gap-3 text-small">
				<span class="font-semibold text-text">{pct}% {t('plans.complete')}</span>
				<span class="text-muted">
					{t('plans.daysLeft').replace('%n%', String(daysLeft))}{#if wordsLeft}
						<span class="opacity-60"> · </span>{t('plans.minLeft').replace(
							'%n%',
							String(readingMinutes(wordsLeft))
						)}{/if}
				</span>
			</div>
			<div class="h-2 overflow-hidden rounded-full bg-surface-2">
				<div
					class="h-full rounded-full bg-accent transition-[width] duration-500"
					style="width: {pct}%"
				></div>
			</div>
		</div>
	{/if}

	<ol class="mt-8 divide-y divide-border">
		{#each plan.days as d (d.day)}
			{@const done = doneSet.has(d.day)}
			{@const isNext = d.day === next}
			<li
				class="flex items-center gap-4 py-3.5 transition-opacity hover:opacity-100"
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
