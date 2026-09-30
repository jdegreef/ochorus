<script lang="ts">
	import { pagedSnapshot } from '$lib/paging.svelte';
	import type { ArticleSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, hreflangExact } from '$lib/seo';
	import { ARTICLE_LOCALES } from '$lib/live-locales.generated';
	import { localizeHref } from '$lib/href';
	import { lang } from '$lib/lang.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import ArticleShelf, { articleFilters } from '$lib/components/ArticleShelf.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import AccountCta from '$lib/components/AccountCta.svelte';
	import { articleHasTopic, articleCollectionLd } from '$lib/articleTopics';
	import { featuredArticles, isGuide, topicGroups } from '$lib/articleIndex';
	import { readingTime } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { tick } from 'svelte';

	// Each locale's hub lists that language's own articles (+page.ts). The
	// English hub keeps its tuned, English-literal title and description; the
	// others take the catalogue's. Topic shelves (`/articles/<topic>/`) are
	// English-only — their SEO copy is curated English — so a translated hub
	// shows its topics without linking them.
	let { data } = $props();
	const isEn = $derived(lang.current === 'en');
	const articles = $derived<ArticleSummary[]>(data.articles);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	// The topic filter is a real path — the chips in <ArticleShelf> link to
	// `/articles/<slug>/`. Old shared links carrying the retired `?topic=<slug>`
	// query are forwarded to the clean URL so they don't silently show "All".
	// An $effect only runs in the browser, so this never touches the query string
	// during prerender (which SvelteKit forbids, and which the bare /articles must
	// not depend on anyway).
	$effect(() => {
		const wanted = $page.url.searchParams.get('topic');
		if (!wanted) return;
		// Topic shelves are English-only: a translated hub just drops the query.
		if (!isEn) {
			goto(localizeHref(path), { replaceState: true });
			return;
		}
		const known = articles.some((a) => articleHasTopic(a, wanted));
		goto(known ? `/articles/${wanted}/` : '/articles/', { replaceState: true });
	});

	// What narrows the shelf — shareable, reloadable, Back-able — lives in the
	// URL (the same helper Books, Sermons and Biographies use). Owned here rather
	// than in <ArticleShelf> so the page can step its secondary sections aside
	// while the reader is filtering (page-design, browse-shelf step 4).
	const filters = articleFilters(() => $page.url);

	const guides = $derived(articles.filter(isGuide));
	const featured = $derived(featuredArticles(articles));
	const groups = $derived(topicGroups(articles));
	/** The guides rail: the first few, in curated order, that have a cover. */
	const guideRail = $derived(
		guides.flatMap((g) => (g.lead_book ? [{ slug: g.slug, book: g.lead_book }] : [])).slice(0, 10)
	);

	const path = '/articles/';
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const hreflang = hreflangExact(path, [...ARTICLE_LOCALES]);

	const title = $derived(
		isEn
			? 'Articles on prayer, faith & the Christian life — Ochorus'
			: `${t('nav.articles')} — Ochorus`
	);
	const description = $derived(
		isEn
			? 'Short, plain-spoken readings on prayer, faith, grace and the life with God — ' +
					'each one pointing you to a classic Christian book, sermon or life worth reading in full, ' +
					'free.'
			: t('articles.tagline')
	);

	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.articles'), href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
	// A CollectionPage listing each article, so the set reads as one entity to a
	// crawler rather than a handful of unrelated URLs.
	const listLd = $derived(
		articleCollectionLd(t('nav.articles'), description, canonical, articles, (s) =>
			localizeHref(`/articles/${s}/`)
		)
	);

	async function showGuides() {
		filters.values.kind = 'guides';
		// Filtering removes the sections above the list; scroll once they're gone,
		// or the target is measured against the old layout.
		await tick();
		document.getElementById('all-articles')?.scrollIntoView({ block: 'start' });
	}

	let shelf = $state<ArticleShelf>();
	export const snapshot = pagedSnapshot(() => shelf?.pages);
</script>

<Seo {title} {description} {canonical} {hreflang} structuredData={[crumbsLd, listLd]} />

<svelte:head>
	<!-- No articles in this language (no English fallback): nothing to index. -->
	{#if !loadError && !articles.length}<meta name="robots" content="noindex" />{/if}
</svelte:head>

<div class="page-col px-5 py-10">
	<!-- No visible breadcrumb: a top-level hub's only trail is Home > <this>
	     — Home is already the logo, <this> restates the H1 below, so it
	     carries nothing. The BreadcrumbList JSON-LD stays in the head; the
	     page's position is true even when we don't draw it. -->
	<PageHeader
		title={t('nav.articles')}
		tagline={t('articles.tagline')}
		meta={articles.length ? counts : undefined}
	/>
	<!-- "130 articles · 73 book guides" — the shelf's size, and how much of it is
	     guides (the switch below splits them). -->
	{#snippet counts()}
		{articles.length}
		{articles.length === 1 ? t('common.articleOne') : t('common.articleMany')}
		{#if guides.length}
			<span class="opacity-50">·</span>
			{guides.length}
			{guides.length === 1 ? t('articles.guideOne') : t('articles.guideMany')}
		{/if}
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if articles.length}
		<!-- The secondary sections step aside while the reader filters: they
		     answer "where do I begin?", and a reader who has typed has begun. -->
		{#if !filters.active}
			{#if featured.length}
				<section class="mb-10" aria-labelledby="start-here">
					<h2 id="start-here" class="section-label">{t('articles.startHere')}</h2>
					<div class="grid gap-4 md:grid-cols-3">
						{#each featured as a (a.slug)}
							<a
								href={localizeHref(`/articles/${a.slug}/`)}
								class="card-lift flex gap-4 rounded-card border border-border bg-surface p-5 text-inherit hover:no-underline"
							>
								{#if a.lead_book}
									<div class="w-16 shrink-0" aria-hidden="true">
										<BookCover book={a.lead_book} />
									</div>
								{/if}
								<div class="flex min-w-0 flex-col gap-1.5">
									<p class="eyebrow text-accent">
										{#if a.topics?.[0]}{a.topics[0].title}<span class="opacity-50">{' · '}</span>{/if}{readingTime(a.word_count)}
									</p>
									<h3 class="text-h3 text-text">{a.h1}</h3>
									{#if a.lead_book}
										<p class="mt-auto text-small text-muted">
											{t('articles.leadsTo').replace('%title%', a.lead_book.title)}
										</p>
									{/if}
								</div>
							</a>
						{/each}
					</div>
				</section>
			{/if}

			{#if groups.length > 1}
				<section class="mb-10" aria-labelledby="by-topic">
					<h2 id="by-topic" class="section-label">{t('home.browseTopic')}</h2>
					<div class="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3">
						{#each groups as g (g.slug)}
							<div class="flex flex-col gap-2 rounded-card border border-border bg-surface p-4 sm:p-5">
								<h3 class="flex flex-col gap-1 text-h3 sm:flex-row sm:items-baseline sm:justify-between sm:gap-3">
									{#if isEn}
										<a href="/articles/{g.slug}/" class="text-text hover:text-accent">{g.title}</a>
									{:else}
										<span class="text-text">{g.title}</span>
									{/if}
									<span class="count text-small font-normal">{g.count}</span>
								</h3>
								<!-- The previews need a column's width; on a phone the card is the
								     topic's name and size, a door rather than a list. -->
								<ul class="hidden flex-col gap-1.5 sm:flex">
									{#each g.items as a (a.slug)}
										<li><a href={localizeHref(`/articles/${a.slug}/`)} class="text-body">{a.h1}</a></li>
									{/each}
								</ul>
								{#if isEn}
									<a
										href="/articles/{g.slug}/"
										class="mt-auto hidden pt-1 text-small font-semibold text-muted hover:text-accent sm:block"
										>{t('articles.seeAll').replace('%n%', String(g.count))}</a
									>
								{/if}
							</div>
						{/each}
					</div>
				</section>
			{/if}

			{#if guideRail.length > 2}
				<section class="mb-10" aria-labelledby="guides-rail">
					<div class="flex items-baseline justify-between gap-4">
						<h2 id="guides-rail" class="section-label">{t('articles.kindGuides')}</h2>
						<button class="btn btn-ghost btn-sm" onclick={showGuides}>
							{t('articles.allGuides').replace('%n%', String(guides.length))}
						</button>
					</div>
					<div class="cover-rail flex gap-4 pb-1">
						{#each guideRail as g (g.slug)}
							<a href={localizeHref(`/articles/${g.slug}/`)} class="w-20 shrink-0 hover:no-underline sm:w-24">
								<BookCover book={g.book} />
								<div class="mt-1.5 line-clamp-2 text-eyebrow font-medium text-text">
									{g.book.title}
								</div>
								<div class="truncate text-eyebrow text-muted">{g.book.author.name}</div>
							</a>
						{/each}
					</div>
				</section>
			{/if}
		{/if}
		<h2 id="all-articles" class="section-label">{t('home.allArticles')}</h2>
		<!-- A translated hub is unpaged: it is the crawl's one guaranteed link to
		     each of its articles (see +page.ts), and the largest is ~120 rows. -->
		<ArticleShelf
			bind:this={shelf}
			{articles}
			activeTopic=""
			{filters}
			heading="h3"
			topicLinks={isEn}
			pageSize={isEn ? 24 : Infinity}
		/>
	{:else}
		<EmptyState message={t('articles.emptyIndex')} />
	{/if}

	<AccountCta />
</div>

<style>
	#all-articles {
		scroll-margin-top: calc(var(--appnav-h, 0px) + 1rem);
	}
</style>
