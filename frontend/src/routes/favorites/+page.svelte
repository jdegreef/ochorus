<script lang="ts">
	import { onMount } from 'svelte';
	import {
		listAuthors,
		listBooks,
		listPlans,
		listSermons,
		listTopics,
		listArticles,
		resolveQuotes,
		citeLine,
		type AuthorBio,
		type BookSummary,
		type PlanSummary,
		type SermonSummary,
		type TopicSummary,
		type ArticleSummary,
		type SavedQuote
	} from '$lib/library-public';
	import { favorites, type FavoriteEntry } from '$lib/favorites.svelte';
	import { planProgress } from '$lib/planProgress.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { unslug } from '$lib/strings';
	import { topicMeta } from '$lib/emblemNames';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import LibraryBookCard from '$lib/components/LibraryBookCard.svelte';
	import AuthorTile from '$lib/components/AuthorTile.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import ShelfCard from '$lib/components/ShelfCard.svelte';
	import ArticleCard from '$lib/components/ArticleCard.svelte';
	import QuoteCard from '$lib/components/QuoteCard.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	/**
	 * "My Library" — the reader's followed authors and saved works, drawn as
	 * covers with reading progress, not the bare text pills the old homepage
	 * shelf showed. Client-only and personal (favorites are device-local first,
	 * synced when signed in), so it works signed-out too and never prerenders.
	 *
	 * Order is people before their works: Authors, then Books, Sermons, Topics,
	 * Plans, Articles, and saved Quotes.
	 *
	 * Titles/covers resolve from the public catalogs in the current language; a
	 * favorite whose work has no row in that language can't be drawn as a cover,
	 * so it falls back to a slug-derived pill (the old shelf's behaviour) rather
	 * than vanishing. Quotes are the exception — a quote has no slug-addressable
	 * page to fall back to, so an unresolved one (pulled or un-approved) simply
	 * drops off the shelf.
	 */
	const t = i18n.t;

	// Resolved catalogs, keyed by slug. Populated on mount; empty until then.
	let books = $state<Record<string, BookSummary>>({});
	let authors = $state<Record<string, AuthorBio>>({});
	let plans = $state<Record<string, PlanSummary>>({});
	let sermons = $state<Record<string, SermonSummary>>({});
	let topics = $state<Record<string, TopicSummary>>({});
	let articles = $state<Record<string, ArticleSummary>>({});
	// Quotes aren't a full catalog — there's no "list all quotes" — so these are
	// resolved from exactly the saved slugs (see resolveQuotes).
	let quotes = $state<Record<string, SavedQuote>>({});
	let loaded = $state(false);

	onMount(async () => {
		const lang = getLang();
		const [a, b, p, s, tp, ar] = await Promise.all([
			listAuthors(lang).catch(() => [] as AuthorBio[]),
			listBooks(lang).catch(() => [] as BookSummary[]),
			listPlans(lang).catch(() => [] as PlanSummary[]),
			listSermons(lang).catch(() => [] as SermonSummary[]),
			listTopics(lang).catch(() => [] as TopicSummary[]),
			listArticles(lang).catch(() => [] as ArticleSummary[])
		]);
		authors = Object.fromEntries(a.map((x) => [x.slug, x]));
		books = Object.fromEntries(b.map((x) => [x.slug, x]));
		plans = Object.fromEntries(p.map((x) => [x.slug, x]));
		sermons = Object.fromEntries(s.map((x) => [x.slug, x]));
		topics = Object.fromEntries(tp.map((x) => [x.slug, x]));
		articles = Object.fromEntries(ar.map((x) => [x.slug, x]));
		loaded = true;
	});

	// favorites.all() is reactive (favorites.ticks) but re-reads and re-sorts
	// localStorage on each call, so read it once per tick and filter that rather
	// than once per section. Un-hearting a work on its own page and coming back
	// still reflects immediately.
	const allFavs = $derived(favorites.all());
	const entriesOf = (kind: FavoriteEntry['kind']) => allFavs.filter((e) => e.kind === kind);

	const authorFavs = $derived(entriesOf('author'));
	const bookFavs = $derived(entriesOf('book'));
	const sermonFavs = $derived(entriesOf('sermon'));
	const topicFavs = $derived(entriesOf('topic'));
	const planFavs = $derived(entriesOf('plan'));
	const articleFavs = $derived(entriesOf('article'));
	const quoteFavs = $derived(entriesOf('quote'));
	const isEmpty = $derived(allFavs.length === 0);

	// Quotes have no catalog to load up front (there's no "list all quotes"), so
	// the shelf resolves them itself: whenever quoteFavs gains a slug we haven't
	// fetched yet — first paint, or a quote hearted on another device arriving
	// through the account sync (which bumps favorites.ticks) — fetch just the new
	// ones and merge them in. Without this, a synced-in quote would show neither
	// a card nor a fallback pill (quotes have no pill) until a reload.
	// `requestedQuotes` is a plain, non-reactive Set so a dropped/unreviewed slug
	// isn't re-fetched every time the list changes; a failed batch is cleared so
	// it can retry.
	const requestedQuotes = new Set<string>();
	$effect(() => {
		const missing = quoteFavs.map((e) => e.slug).filter((s) => !requestedQuotes.has(s));
		if (!missing.length) return;
		for (const s of missing) requestedQuotes.add(s);
		resolveQuotes(missing)
			.then((qs) => {
				quotes = { ...quotes, ...Object.fromEntries(qs.map((x) => [x.slug, x])) };
			})
			.catch(() => {
				for (const s of missing) requestedQuotes.delete(s);
			});
	});

	// Fallback link for a favorite whose catalog row is missing in this language.
	// Quotes are absent on purpose — they have no slug-addressable page.
	const HREF: Record<Exclude<FavoriteEntry['kind'], 'quote'>, (slug: string) => string> = {
		author: (s) => `/authors/${s}`,
		book: (s) => `/books/${s}`,
		plan: (s) => `/plans/${s}`,
		sermon: (s) => `/sermons/${s}`,
		topic: (s) => `/topics/${s}`,
		article: (s) => `/articles/${s}`
	};

	const planPercent = (plan: PlanSummary) =>
		plan.day_count > 0
			? Math.min(100, Math.round((planProgress.doneDays(plan.slug).length / plan.day_count) * 100))
			: 0;
</script>

<svelte:head>
	<title>{t('fav.yourFavorites')} — Ochorus</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="page-col px-5 py-10">
	<PageHeader title={t('fav.yourFavorites')} />

	{#if loaded && isEmpty}
		<EmptyState message={t('fav.empty')}>
			{#snippet action()}
				<a href={localizeHref('/books')} class="btn btn-primary hover:no-underline"
					>{t('home.browseLibrary')}</a
				>
			{/snippet}
		</EmptyState>
	{/if}

	<!-- A saved favorite whose work has no row in the current language can't draw
	     a cover; it falls back to this pill so it is never silently lost. Quotes
	     have no slug-addressable page, so they are never rendered as pills. -->
	{#snippet fallbackPills(
		entries: FavoriteEntry[],
		resolved: Record<string, unknown>,
		kind: Exclude<FavoriteEntry['kind'], 'quote'>
	)}
		{@const missing = entries.filter((e) => !resolved[e.slug])}
		<!-- Only once the catalogs are in: before that every entry is "unresolved",
		     which would flash the whole shelf as pills and then swap to covers. -->
		{#if loaded && missing.length}
			<div class="mt-3 flex flex-wrap gap-2">
				{#each missing as e (e.slug)}
					<a href={localizeHref(HREF[kind](e.slug))} class="tag">
						♥ {unslug(e.slug)}
					</a>
				{/each}
			</div>
		{/if}
	{/snippet}

	<!-- Following: hearted authors — the people first -->
	{#if authorFavs.length}
		<section class="pt-8">
			<SectionHeader title={t('fav.groupAuthors')} />
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
				{#each authorFavs as e (e.slug)}
					{#if authors[e.slug]}
						<AuthorTile author={authors[e.slug]} />
					{/if}
				{/each}
			</div>
			{@render fallbackPills(authorFavs, authors, 'author')}
		</section>
	{/if}

	<!-- Books — covers with the reader's own progress -->
	{#if bookFavs.length}
		<section class="pt-10">
			<SectionHeader title={t('fav.groupBooks')} />
			<div class="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 lg:grid-cols-5">
				{#each bookFavs as e (e.slug)}
					{#if books[e.slug]}
						<LibraryBookCard book={books[e.slug]} />
					{/if}
				{/each}
			</div>
			{@render fallbackPills(bookFavs, books, 'book')}
		</section>
	{/if}

	<!-- Saved sermons -->
	{#if sermonFavs.length}
		<section class="pt-10">
			<SectionHeader title={t('fav.groupSermons')} />
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
				{#each sermonFavs as e (e.slug)}
					{#if sermons[e.slug]}
						<SermonCard sermon={sermons[e.slug]} showAuthor />
					{/if}
				{/each}
			</div>
			{@render fallbackPills(sermonFavs, sermons, 'sermon')}
		</section>
	{/if}

	<!-- Followed topics: the shelves the reader wants to keep an eye on -->
	{#if topicFavs.length}
		<section class="pt-10">
			<SectionHeader title={t('fav.groupTopics')} />
			<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
				{#each topicFavs as e (e.slug)}
					{#if topics[e.slug]}
						{@const topic = topics[e.slug]}
						{@const meta = topicMeta(topic.slug)}
						<ShelfCard
							href={localizeHref(`/topics/${topic.slug}`)}
							hue={meta.accent}
							emblem={meta.emblem}
							covers={topic.covers}
							title={topic.title}
						>
							{#snippet aside()}
								{#if topic.book_count}
									{topic.book_count}
									{topic.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
								{/if}
								{#if topic.sermon_count}
									{#if topic.book_count}· {/if}{topic.sermon_count}
									{topic.sermon_count === 1 ? t('common.sermonOne') : t('common.sermonMany')}
								{/if}
							{/snippet}
							<p class="shelf-card-desc mt-1.5 text-small text-muted">{topic.description}</p>
						</ShelfCard>
					{/if}
				{/each}
			</div>
			{@render fallbackPills(topicFavs, topics, 'topic')}
		</section>
	{/if}

	<!-- Saved reading plans -->
	{#if planFavs.length}
		<section class="pt-10">
			<SectionHeader title={t('fav.groupPlans')} />
			<div class="grid gap-4 sm:grid-cols-2">
				{#each planFavs as e (e.slug)}
					{#if plans[e.slug]}
						{@const plan = plans[e.slug]}
						{@const pct = planPercent(plan)}
						<a
							href={localizeHref(`/plans/${plan.slug}`)}
							class="flex flex-col gap-3 rounded-card border border-border p-4 hover:bg-surface-2 hover:no-underline"
						>
							<div class="flex items-start justify-between gap-3">
								<span class="min-w-0">
									<span class="block text-body font-semibold text-text">{plan.title}</span>
									<span class="block text-small text-muted">
										{plan.day_count}
										{t('plans.days')}
									</span>
								</span>
								<CoverStrip covers={plan.covers} max={3} />
							</div>
							{#if pct > 0}
								<div>
									<ProgressBar percent={pct} label="{plan.title}: {t('plans.complete')}" />
									<div class="mt-1 text-eyebrow text-muted">{pct}% {t('plans.complete')}</div>
								</div>
							{/if}
						</a>
					{/if}
				{/each}
			</div>
			{@render fallbackPills(planFavs, plans, 'plan')}
		</section>
	{/if}

	<!-- Saved articles -->
	{#if articleFavs.length}
		<section class="pt-10">
			<SectionHeader title={t('fav.groupArticles')} />
			<div class="grid gap-4 sm:grid-cols-2">
				{#each articleFavs as e (e.slug)}
					{#if articles[e.slug]}
						<ArticleCard article={articles[e.slug]} />
					{/if}
				{/each}
			</div>
			{@render fallbackPills(articleFavs, articles, 'article')}
		</section>
	{/if}

	<!-- Saved quotes — each still sourced, and still un-savable by its heart -->
	{#if quoteFavs.length}
		<section class="pt-10 pb-4">
			<SectionHeader title={t('fav.groupQuotes')} />
			<ul class="grid list-none gap-4 p-0 sm:grid-cols-2">
				{#each quoteFavs as e (e.slug)}
					{#if quotes[e.slug]}
						{@const q = quotes[e.slug]}
						<QuoteCard quote={q} authorName={q.author.name} cite={citeLine(q)} />
					{/if}
				{/each}
			</ul>
		</section>
	{/if}
</div>
