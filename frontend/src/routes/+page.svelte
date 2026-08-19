<script lang="ts">
	import type { BookSummary, AuthorBio, TopicSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { jsonLd } from '$lib/seo';
	import { goto } from '$app/navigation';
	import { localizeHref } from '$lib/href';
	import { locales } from '$lib/paraglide/runtime';
	import { i18n } from '$lib/i18n.svelte';
	import { portraitPosition } from '$lib/portraits';
	import ContinueReading from '$lib/components/ContinueReading.svelte';
	import ReadingNudge from '$lib/components/ReadingNudge.svelte';
	import TodaysReading from '$lib/components/TodaysReading.svelte';
	import PlansProgress from '$lib/components/PlansProgress.svelte';
	import FavoritesShelf from '$lib/components/FavoritesShelf.svelte';
	import RecommendedNext from '$lib/components/RecommendedNext.svelte';
	import SermonOfTheWeek from '$lib/components/SermonOfTheWeek.svelte';
	import BookCard from '$lib/components/BookCard.svelte';

	let { data } = $props();
	const featured = $derived<BookSummary[]>(data.featured);
	const authors = $derived<AuthorBio[]>(data.authors);
	const topics = $derived<TopicSummary[]>(data.topics ?? []);

	const t = i18n.t;

	// Hero search → the full search page. Progressive enhancement: the form is a
	// real GET to /search (works with no JS); with JS we intercept and navigate
	// client-side so it stays in the SPA.
	let query = $state('');
	function submitSearch(e: Event) {
		e.preventDefault();
		const q = query.trim();
		goto(localizeHref('/search') + (q ? `?q=${encodeURIComponent(q)}` : ''));
	}

	const initials = (name: string) =>
		name
			.split(' ')
			.filter(Boolean)
			.map((w) => w[0])
			.slice(0, 2)
			.join('')
			.toUpperCase();

	// Site-level structured data: a WebSite with the sitelinks-searchbox action
	// (the hero search posts to /search) and the publishing Organization.
	const siteLd = jsonLd([
		{
			'@context': 'https://schema.org',
			'@type': 'WebSite',
			name: 'Ochorus',
			url: `${SITE_URL}/`,
			potentialAction: {
				'@type': 'SearchAction',
				target: {
					'@type': 'EntryPoint',
					urlTemplate: `${SITE_URL}/search?q={search_term_string}`
				},
				'query-input': 'required name=search_term_string'
			}
		},
		{
			'@context': 'https://schema.org',
			'@type': 'Organization',
			name: 'Ochorus',
			url: `${SITE_URL}/`,
			description: t('home.metaDescription')
		}
	]);
</script>

<svelte:head>
	<title>Ochorus — {t('home.heroTitle')}</title>
	<meta name="description" content={t('home.metaDescription')} />
	<link rel="canonical" href="{SITE_URL}{localizeHref('/')}" />
	{#each locales as loc (loc)}
		<link rel="alternate" hreflang={loc} href="{SITE_URL}{localizeHref('/', { locale: loc })}" />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_URL}/" />
	<meta property="og:type" content="website" />
	<meta property="og:site_name" content="Ochorus" />
	<meta property="og:title" content="Ochorus — {t('home.heroTitle')}" />
	<meta property="og:description" content={t('home.metaDescription')} />
	<meta property="og:url" content="{SITE_URL}{localizeHref('/')}" />
	<meta name="twitter:card" content="summary" />
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html siteLd}
</svelte:head>

<!-- Hero -->
<section class="border-b border-border bg-surface-2">
	<div class="mx-auto max-w-4xl px-5 py-20 text-center">
		<p class="eyebrow mb-4 text-accent">
			{t('home.heroEyebrow')}
		</p>
		<h1 class="text-display mx-auto mb-5 max-w-3xl">
			{t('home.heroTitle')}
		</h1>
		<p class="mx-auto mb-7 max-w-xl text-body text-muted">
			{t('home.heroTagline')}
		</p>
		<form
			onsubmit={submitSearch}
			method="GET"
			action={localizeHref('/search')}
			role="search"
			class="mx-auto mb-6 flex max-w-lg items-center gap-2 rounded-full border border-border bg-surface px-2 py-1.5 shadow-sm focus-within:border-accent"
		>
			<svg
				class="ms-2 h-5 w-5 shrink-0 text-muted"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
				aria-hidden="true"
			>
				<circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
			</svg>
			<input
				bind:value={query}
				name="q"
				type="search"
				enterkeyhint="search"
				placeholder={t('search.placeholder')}
				aria-label={t('nav.search')}
				class="min-w-0 flex-1 bg-transparent py-1 text-body text-text placeholder:text-muted focus-visible:-outline-offset-2"
			/>
			<button type="submit" class="btn btn-primary shrink-0 !rounded-full">{t('nav.search')}</button>
		</form>
		<div class="flex flex-wrap justify-center gap-3">
			<a href={localizeHref('/books')} class="btn btn-primary">{t('home.browseLibrary')}</a>
			<a href={localizeHref('/about')} class="btn btn-ghost">{t('home.aboutOchorus')}</a>
		</div>
	</div>
</section>

<!-- Continue reading (resume) stays first for returning readers; empty for
     new visitors, so browsing books leads for them. Client-side only. -->
<ContinueReading books={data.books} />

<!-- Streak + weekly-goal nudge for returning readers; renders nothing until
     there's reading activity. Client-side only. -->
<ReadingNudge />

<!-- Discover Your Next Book — above the plan/sermon blocks.
     Hidden when empty, like the topics row below it: if the shelf failed to
     load (see the note in +page.ts) a bare heading over an empty grid reads as
     "Ochorus has no books", where showing nothing simply reads as a shorter
     page around the personal blocks that still work. -->
{#if featured.length}
	<section class="page-col px-5 pt-14">
		<div class="mb-6 flex items-end justify-between">
			<h2 class="text-h1">{t('home.discoverNext')}</h2>
			<a href={localizeHref('/books')} class="text-small font-semibold text-accent">{t('home.allBooks')} →</a>
		</div>
		<div class="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-6">
			{#each featured as book (book.slug)}
				<BookCard {book} showAuthor />
			{/each}
		</div>
	</section>
{/if}

<!-- Personal plan / sermon blocks — client-side only (this page is prerendered) -->
<TodaysReading />
<PlansProgress />
<RecommendedNext />
<FavoritesShelf />
<SermonOfTheWeek />

<!-- Browse by topic -->
{#if topics.length}
	<section class="page-col px-5 pt-14">
		<div class="mb-6 flex items-end justify-between">
			<h2 class="text-h1">{t('home.browseTopic')}</h2>
			<a href={localizeHref('/topics')} class="text-small font-semibold text-accent"
				>{t('home.allTopics')} →</a
			>
		</div>
		<div class="flex flex-wrap gap-2.5">
			{#each topics as topic (topic.slug)}
				<a
					href={localizeHref(`/topics/${topic.slug}`)}
					class="inline-flex items-baseline gap-1.5 rounded-full border border-border bg-surface px-4 py-2 text-small font-medium text-text hover:border-accent hover:text-accent hover:no-underline"
				>
					{topic.title}
					<span class="text-eyebrow font-normal text-muted">{topic.book_count}</span>
				</a>
			{/each}
		</div>
	</section>
{/if}

<!-- Mission teaser -->
<section class="mt-14 border-y border-border bg-surface-2">
	<div class="mx-auto max-w-3xl px-5 py-16 text-center">
		<h2 class="text-h1 mb-3">{t('home.missionTitle')}</h2>
		<p class="mx-auto max-w-xl text-body text-muted">
			{t('home.missionText')}
		</p>
		<a href={localizeHref('/about')} class="btn btn-ghost mt-6">{t('home.ourStory')}</a>
	</div>
</section>

<!-- Christian Authors — hidden when the shelf is empty, same reason as
     "Discover your next book" above. -->
{#if authors.length}
	<section class="page-col px-5 pt-14 pb-20">
		<div class="mb-6 flex items-end justify-between">
			<h2 class="text-h1">{t('home.authorsTitle')}</h2>
			<a href={localizeHref('/biographies')} class="text-small font-semibold text-accent">{t('home.allBiographies')} →</a>
		</div>
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
			{#each authors as author (author.slug)}
				<a
					href={localizeHref(`/authors/${author.slug}`)}
					class="flex items-center gap-3 rounded-card border border-border p-4 hover:no-underline hover:bg-surface-2"
				>
					{#if author.photo_url}
						<img
							src={author.photo_url}
							alt="{t('a11y.portraitOf')} {author.name}"
							loading="lazy"
							class="h-11 w-11 shrink-0 rounded-full border border-border object-cover"
							style="filter: grayscale(1); object-position: {portraitPosition(author.slug)}"
						/>
					{:else}
						<span
							class="font-display flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent-soft text-small font-semibold text-accent"
						>
							{initials(author.name)}
						</span>
					{/if}
					<span>
						<span class="block text-small font-semibold text-text">{author.name}</span>
						<span class="block text-small text-muted">
							{author.book_count}
							{author.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
						</span>
					</span>
				</a>
			{/each}
		</div>
	</section>
{/if}
