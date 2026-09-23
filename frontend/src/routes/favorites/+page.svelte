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
	import { allProgress } from '$lib/progress';
	import { buildShelves, shelfHref } from '$lib/bookshelf';
	import { readJSON, writeJSON } from '$lib/persisted';
	import Icon from '$lib/components/Icon.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import Bookshelf from '$lib/components/Bookshelf.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import AuthorTile from '$lib/components/AuthorTile.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import ShelfCard from '$lib/components/ShelfCard.svelte';
	import ArticleCard from '$lib/components/ArticleCard.svelte';
	import QuoteCard from '$lib/components/QuoteCard.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';

	/**
	 * "My Bookshelf" — the reader's books first, drawn as a bookcase with three
	 * shelves (Currently reading, To read, Finished; see $lib/bookshelf for which
	 * book goes where), then everything else they've saved. Client-only and
	 * personal (favorites and progress are device-local first, synced when signed
	 * in), so it works signed-out too and never prerenders.
	 *
	 * Below the books: Sermons, Plans, Authors, Topics, Articles, saved Quotes.
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
	// Reading progress is localStorage, not a rune: re-read it when a finish /
	// un-finish on this page, or an account sync, announces a change.
	let progressTicks = $state(0);

	onMount(() => {
		const bump = () => progressTicks++;
		window.addEventListener('ochorus:sync', bump);
		void loadCatalogs();
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	async function loadCatalogs() {
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
	}

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
	const shelves = $derived.by(() => {
		void progressTicks;
		return buildShelves(Object.values(books), bookFavs, allProgress());
	});
	const bookCount = $derived(
		shelves.reading.length + shelves.toRead.length + shelves.finished.length
	);
	// Covers or spines — a per-device preference, like the reader's own layout
	// settings, so it lives in localStorage and isn't synced.
	const VIEW_KEY = 'ochorus:shelf-view';
	let view = $state<'covers' | 'spines'>(
		readJSON<string>(VIEW_KEY, 'covers') === 'spines' ? 'spines' : 'covers'
	);
	function setView(v: 'covers' | 'spines') {
		view = v;
		writeJSON(VIEW_KEY, v);
	}

	// The book to pick up: the one most recently read.
	const current = $derived(shelves.reading[0]);
	const hasOthers = $derived(allFavs.some((e) => e.kind !== 'book'));
	const jumps = $derived(
		[
			{ id: 'reading', label: t('fav.shelfReading'), count: shelves.reading.length },
			{ id: 'to-read', label: t('fav.shelfToRead'), count: shelves.toRead.length },
			{ id: 'finished', label: t('fav.shelfFinished'), count: shelves.finished.length },
			{ id: 'sermons', label: t('fav.groupSermons'), count: sermonFavs.length },
			{ id: 'authors', label: t('fav.groupAuthors'), count: authorFavs.length },
			{ id: 'topics', label: t('fav.groupTopics'), count: topicFavs.length },
			{ id: 'plans', label: t('fav.groupPlans'), count: planFavs.length },
			{ id: 'articles', label: t('fav.groupArticles'), count: articleFavs.length },
			{ id: 'quotes', label: t('fav.groupQuotes'), count: quoteFavs.length }
		].filter((j, i) => i < 3 || j.count > 0)
	);

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
	<PageHeader title={t('fav.yourFavorites')} tagline={t('fav.tagline')} />

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

	<!-- Jump links: the three shelves, then whatever else is saved. Only worth
	     the row once the page runs past the books. -->
	{#if loaded && hasOthers}
		<nav class="-mt-2 mb-2 flex flex-wrap gap-2" aria-label={t('fav.yourFavorites')}>
			{#each jumps as j (j.id)}
				<a href="#{j.id}" class="tag hover:no-underline"
					>{j.label} <span class="text-muted">{j.count}</span></a
				>
			{/each}
		</nav>
	{/if}

	{#if loaded && current}
		{@const b = current.book}
		<!-- The one book to pick up now: the most recently read. -->
		<a
			href={localizeHref(shelfHref(current))}
			class="card-lift bg-surface mt-6 flex items-center gap-5 rounded-card border border-border p-4 hover:no-underline sm:p-5"
		>
			<div class="w-20 shrink-0 sm:w-24">
				<BookCover book={b} rounded="rounded-sm" />
			</div>
			<div class="min-w-0 flex-1">
				<p class="eyebrow mb-1 text-accent">{t('fav.pickUp')}</p>
				<div class="text-h3 line-clamp-2 font-display text-text">{b.title}</div>
				<div class="mt-0.5 truncate text-small text-muted">{b.author.name}</div>
				<div class="mt-3 max-w-sm">
					<ProgressBar percent={current.pct} label="{b.title}: {current.pct}%" size="md" />
					<div class="mt-1 text-micro text-muted">
						{t('continue.chapter')}
						{current.order} / {b.chapter_count} · {current.pct}%
					</div>
				</div>
				<div class="mt-3 text-small font-semibold text-accent">{t('reader.resume')} →</div>
			</div>
		</a>
	{/if}

	{#if loaded}
		{#if bookCount}
			<div class="-mb-6 mt-8 flex justify-end">
				<div class="view-toggle" role="group" aria-label={t('fav.shelfView')}>
					<button type="button" aria-pressed={view === 'covers'} onclick={() => setView('covers')}>
						<Icon name="grid" size={15} />
						{t('fav.viewCovers')}
					</button>
					<button type="button" aria-pressed={view === 'spines'} onclick={() => setView('spines')}>
						<Icon name="layers" size={15} />
						{t('fav.viewSpines')}
					</button>
				</div>
			</div>
		{/if}
		<Bookshelf
			{view}
			id="reading"
			title={t('fav.shelfReading')}
			items={shelves.reading}
			emptyHint={t('fav.shelfReadingEmpty')}
		/>
		<Bookshelf
			{view}
			id="to-read"
			title={t('fav.shelfToRead')}
			items={shelves.toRead}
			emptyHint={t('fav.shelfToReadEmpty')}
		/>
		{#if shelves.unresolved.length}
			<div class="mt-4 flex flex-wrap gap-2">
				{#each shelves.unresolved as slug (slug)}
					<a href={localizeHref(`/books/${slug}`)} class="tag">♥ {unslug(slug)}</a>
				{/each}
			</div>
		{/if}
		<Bookshelf
			{view}
			id="finished"
			title={t('fav.shelfFinished')}
			items={shelves.finished}
			emptyHint={t('fav.shelfFinishedEmpty')}
		/>
		{#if bookCount === 0 && !hasOthers}
			<div class="mt-8 text-center">
				<a href={localizeHref('/books')} class="btn btn-primary hover:no-underline"
					>{t('home.browseLibrary')}</a
				>
			</div>
		{/if}
	{/if}

	<!-- Everything else saved, below the books -->
	<!-- Saved sermons -->
	{#if sermonFavs.length}
		<section id="sermons" class="scroll-mt-24 pt-10">
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

	<!-- Following: hearted authors — the people first -->
	{#if authorFavs.length}
		<section id="authors" class="scroll-mt-24 pt-10">
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

	<!-- Followed topics: the shelves the reader wants to keep an eye on -->
	{#if topicFavs.length}
		<section id="topics" class="scroll-mt-24 pt-10">
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
		<section id="plans" class="scroll-mt-24 pt-10">
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
		<section id="articles" class="scroll-mt-24 pt-10">
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
		<section id="quotes" class="scroll-mt-24 pt-10 pb-4">
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

<style>
	.view-toggle {
		display: inline-flex;
		padding: 3px;
		gap: 2px;
		border: 1px solid var(--color-border);
		border-radius: 999px;
		background: var(--color-surface);
	}
	.view-toggle button {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.3rem 0.8rem;
		border: 0;
		border-radius: 999px;
		background: transparent;
		color: var(--color-muted);
		font-size: var(--fs-small);
		cursor: pointer;
	}
	.view-toggle button[aria-pressed='true'] {
		background: var(--color-accent-soft);
		color: var(--color-accent);
		font-weight: 600;
	}
</style>
