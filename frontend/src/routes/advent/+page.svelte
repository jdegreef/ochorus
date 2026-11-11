<script lang="ts">
	import { onMount } from 'svelte';
	import { SITE_URL } from '$lib/config';
	import { absUrl, breadcrumbLd, collectionPage, hreflangFor } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { planDayPath } from '$lib/editionHref';
	import { planMinutesPerDay } from '$lib/reading';
	import type { BookSummary, PlanDetail, SermonSummary } from '$lib/library-public';
	import { adventFor, dayMonth, longDate, planWeeks, shortDate, statusLine } from '$lib/advent';
	import BookCard from '$lib/components/BookCard.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';

	// English literals, as on /quotes and /scripture: this hub is not localized
	// because what it lists is not (the plan reads English-only books). Chrome
	// strings still go through t().
	let { data } = $props();
	const t = i18n.t;
	const plan = $derived<PlanDetail | null>(data.plan);
	const books = $derived<BookSummary[]>(data.books);
	const sermons = $derived<SermonSummary[]>(data.sermons);

	// The prerender bakes the build day's Advent; the reader's own day takes
	// over on mount. `{#key now}` redraws the dated parts then, so a page built
	// before Christmas and opened after it shows next year's dates, not stale
	// text hydration left alone. The countdown is the reader's alone, so it
	// waits for mount.
	let now = $state<Date | null>(null);
	onMount(() => (now = new Date()));
	const at = $derived(now ?? new Date());
	const advent = $derived(adventFor(at));
	const weeks = $derived(plan ? planWeeks(plan.days) : []);
	const perDay = $derived(plan ? planMinutesPerDay(plan) : 0);
	// The fan features its middle cover (CoverStrip): lead with the waiting,
	// flanked by the incarnation (Gregory) and the story (Hurlbut), rather
	// than the plan's second book, the First Apology.
	const heroCovers = $derived.by(() => {
		if (!plan) return [];
		const lead = ['the-great-catechism', 'waiting-on-god', 'hurlbuts-life-of-christ'];
		const first = lead.flatMap((s) => plan.covers.filter((c) => c.slug === s));
		return [...first, ...plan.covers.filter((c) => !lead.includes(c.slug))];
	});
	/** The date plan day `n` falls on, begun on Advent Sunday. */
	const dayOf = (n: number) => advent.start + n - 1;

	const path = '/advent/';
	const canonical = `${SITE_URL}${path}`;
	const hreflang = hreflangFor(path, ['en']);
	const title = 'Advent readings: a daily plan from the Christian classics — Ochorus';
	const description =
		'Read through Advent with the classics: a free four-week plan, one short reading a ' +
		'day — Andrew Murray on waiting, Justin Martyr on the prophets, Athanasius on the ' +
		'incarnation and the Christmas story — with books and sermons for the season.';

	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: 'Advent', href: path }
	]);
	const listLd = $derived(
		collectionPage({
			name: 'Advent with the Christian classics',
			description,
			url: path,
			items: [
				...(plan ? [{ name: plan.title, url: `/plans/${plan.slug}/` }] : []),
				...books.map((b) => ({ name: b.title, url: `/books/${b.slug}/` })),
				...sermons.map((s) => ({ name: s.title, url: `/sermons/${s.slug}/` }))
			]
		})
	);
</script>

<Seo
	{title}
	{description}
	{canonical}
	{hreflang}
	ogImage={absUrl('/og/plans.png')}
	structuredData={[breadcrumbLd(crumbs), listLd]}
/>

<div class="page-col px-5 py-10">
	<!-- No visible breadcrumb: a top-level hub's trail is Home > Advent, which
	     the logo and the H1 already say (the /quotes note). The JSON-LD keeps it. -->

	<!-- The hero, the plan page's shape: the plan's books fanned beside the
	     title, then the season in one sentence and the read card. -->
	<section class="advent-hero" class:no-art={!plan?.covers.length}>
		{#if plan?.covers.length}
			<div class="advent-hero-art">
				<CoverStrip covers={heroCovers} size="fan" priority />
			</div>
		{/if}
		{#key now}
			<div class="advent-hero-head min-w-0">
				<p class="eyebrow mb-1 text-muted">
					<span class="whitespace-nowrap">Advent {advent.year}</span>{' · '}<span
						>{dayMonth(advent.start)} to {dayMonth(advent.end)}</span
					>
				</p>
				<h1 class="text-h1">Advent</h1>
			</div>
			<div class="advent-hero-about min-w-0">
				<p class="max-w-xl text-body text-muted">
					The four weeks before Christmas, when the Church remembers the long wait for the
					Saviour and looks for his coming again. Keep them with the writers who kept them
					before us: one short reading a day, free to read.
				</p>
				{#if now}<p class="mt-3 text-small font-medium text-text">{statusLine(now, advent)}</p>{/if}
			</div>
			{#if plan}
				<div class="advent-hero-start min-w-0">
					<div class="read-card">
						<div class="read-card-body">
							<p class="read-card-title">{plan.title}</p>
							<p class="text-small text-muted">
								<span class="whitespace-nowrap">{plan.day_count} {t('plans.days')}</span
								>{#if perDay}{' · '}<span class="whitespace-nowrap">~{perDay} {t('plans.minPerDay')}</span>{/if}{' · '}<span
									>Begin on {longDate(advent.start)}, finish on {dayMonth(dayOf(plan.day_count))}</span
								>
							</p>
						</div>
						<div class="read-card-cta">
							<a href="/plans/{plan.slug}/" class="btn btn-primary btn-solid">Start the Advent plan</a>
						</div>
					</div>
					<div class="mt-3 flex flex-wrap items-center gap-2">
						<FavoriteButton kind="plan" slug={plan.slug} showLabel />
						<ShareButton url={canonical} title="Advent with the Classics" showLabel />
					</div>
				</div>
			{/if}
		{/key}
	</section>

	{#if data.loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{/if}

	<!-- The plan's days as an Advent calendar: its four weeks, each day dated
	     as it falls when the plan is begun on Advent Sunday. -->
	{#if plan && weeks.length}
		{#key now}
			<section class="mb-10" aria-labelledby="advent-days">
				<h2 id="advent-days" class="section-heading no-rule">Day by day</h2>
				<div class="advent-weeks">
					{#each weeks as week, w (w)}
						<section class="advent-week" aria-labelledby="advent-week-{w}">
							<h3 id="advent-week-{w}" class="text-h3">
								<span class="eyebrow block text-muted">Week {w + 1}</span>{week.label}
							</h3>
							<ol class="mt-2">
								{#each week.days as d (d.day)}
									<li class="advent-day">
										<span class="advent-date text-small text-muted">{shortDate(dayOf(d.day))}</span>
										<span class="min-w-0">
											<a href={planDayPath(plan.slug, d)} class="text-body text-text hover:text-accent">{d.chapter_title}</a>
											<span class="block truncate text-small text-muted">{d.book_title}</span>
										</span>
									</li>
								{/each}
							</ol>
						</section>
					{/each}
				</div>
			</section>
		{/key}
	{/if}

	{#if books.length}
		<section class="mb-10" aria-labelledby="advent-books">
			<h2 id="advent-books" class="section-heading no-rule">Books for Advent</h2>
			<div class="book-grid">
				{#each books as book (book.slug)}
					<BookCard {book} showAuthor />
				{/each}
			</div>
		</section>
	{/if}

	{#if sermons.length}
		<section class="mb-10" aria-labelledby="advent-sermons">
			<h2 id="advent-sermons" class="section-heading no-rule">Sermons for Advent and Christmas</h2>
			<div class="sermon-list">
				{#each sermons as sermon (sermon.slug)}
					<SermonCard {sermon} showAuthor />
				{/each}
			</div>
		</section>
	{/if}
</div>

<style>
	/* The plan page's hero (routes/plans/[slug]): the picture beside the title,
	   the about lines and the read card full width beneath it on a phone; from
	   640px the picture spans the rows and the rest stacks beside it. */
	.advent-hero {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		column-gap: 1rem;
		align-items: start;
		padding-block: 0.5rem 2rem;
	}
	.advent-hero-art {
		width: 9.5rem;
	}
	.advent-hero-about,
	.advent-hero-start {
		grid-column: 1 / -1;
		margin-top: 1rem;
	}
	.advent-hero-start {
		max-width: 36rem;
	}
	.advent-hero.no-art {
		grid-template-columns: minmax(0, 1fr);
	}
	@media (min-width: 640px) {
		.advent-hero {
			grid-template-rows: auto auto 1fr;
			column-gap: 2rem;
		}
		.advent-hero-art {
			grid-row: 1 / -1;
			width: 16rem;
		}
		.advent-hero-about,
		.advent-hero-start {
			grid-column: 2;
		}
		.advent-hero.no-art > * {
			grid-column: 1;
		}
	}
	@media (min-width: 1024px) {
		.advent-hero-art {
			width: 19rem;
		}
	}
	/* Four weeks side by side where they fit, one column on a phone. */
	.advent-weeks {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 15rem), 1fr));
		gap: 1.75rem 2rem;
	}
	.advent-day {
		display: grid;
		grid-template-columns: 5.5rem minmax(0, 1fr);
		gap: 0.75rem;
		align-items: baseline;
		padding-block: 0.45rem;
		border-top: 1px solid var(--border);
	}
	.advent-date {
		font-variant-numeric: tabular-nums;
	}
</style>
