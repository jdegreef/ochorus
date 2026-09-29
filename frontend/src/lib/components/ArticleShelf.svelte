<script lang="ts" module>
	import { ARTICLE_KINDS } from '$lib/articleIndex';
	import { urlFilters } from '$lib/urlFilters.svelte';

	/**
	 * The article shelf's URL-backed filters — the text query and the kind. One
	 * setup for the index and the topic shelves, called in the PAGE (not here)
	 * so the page can step its secondary sections aside while the reader
	 * filters. Like `urlFilters`, call it during component setup; `url` is read
	 * lazily (`() => $page.url`) for the reason `urlFilters` gives.
	 */
	export function articleFilters(url: () => URL) {
		return urlFilters({ defaults: { q: '', kind: '' }, allowed: { kind: ARTICLE_KINDS }, url });
	}
	export type ArticleFilters = ReturnType<typeof articleFilters>;
</script>

<script lang="ts">
	import { onMount } from 'svelte';
	import type { ArticleSummary } from '$lib/library-public';
	import ArticleCard from '$lib/components/ArticleCard.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FilterSheet from '$lib/components/FilterSheet.svelte';
	import SheetChoices from '$lib/components/SheetChoices.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';
	import {
		ARTICLE_SORTS,
		isGuide,
		matchesQuery,
		ofKind,
		sortArticles,
		topicCounts,
		type ArticleKind,
		type ArticleSort
	} from '$lib/articleIndex';
	import { articleHasTopic } from '$lib/articleTopics';
	import { queryChip, type FilterChip } from '$lib/filterChips';
	import { readJSON, writeJSON } from '$lib/persisted';
	import { readingTime } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	/**
	 * The article shelf shared by the /articles index and each /articles/<topic>/
	 * page: the controls (free text · sort · Questions / Book guides), the
	 * topic-filter row, the FilterSummary, and the list itself.
	 *
	 * The topic chips are real links, not a client-side filter: each topic view
	 * is its own crawlable URL (`/articles/<slug>/`) with its own H1 and
	 * canonical, which is the whole point of the clean path — a `?topic=` query
	 * gave one indexable page for the lot. "All" is the bare index. Articles are
	 * English-only, so the hrefs are plain (no locale prefix).
	 *
	 * The text query and the kind DO live in the query string, through the
	 * page's `articleFilters()` (above; passed in, so the page can hide its
	 * secondary sections while the reader filters). Sort is the reader's own preference
	 * and lives in localStorage, like the Books and Sermons shelves.
	 */
	let {
		articles,
		activeTopic = '',
		filters,
		heading = 'h2'
	}: {
		/** The full shelf — tabs and their counts are derived from it. */
		articles: ArticleSummary[];
		/** The topic slug this view is filtered to; '' is the unfiltered index. */
		activeTopic?: string;
		/** The page's `articleFilters()`. */
		filters: ArticleFilters;
		/** Card title level: h3 when the page heads the list with its own h2. */
		heading?: 'h2' | 'h3';
	} = $props();

	// Distinct topics present on the shelf, alphabetical, each with a count for
	// its chip badge.
	const topicTabs = $derived(
		topicCounts(articles).sort((x, y) => x.title.localeCompare(y.title))
	);

	/** The shelf this view starts from: the whole index, or one topic's set. */
	const base = $derived(
		activeTopic ? articles.filter((a) => articleHasTopic(a, activeTopic)) : articles
	);

	// The Questions / Book guides switch only earns its place when the view
	// holds both kinds — or when a kind is already set (a shared link), so the
	// reader can always see, and undo, what is narrowing the shelf.
	const guideCount = $derived(base.filter(isGuide).length);
	const showKinds = $derived(
		(guideCount > 0 && guideCount < base.length) || filters.values.kind !== ''
	);

	const KIND_LABEL: Record<ArticleKind, string> = {
		questions: 'articles.kindQuestions',
		guides: 'articles.kindGuides'
	};
	/** The switch's segments: value, label key, count. '' is All. */
	const kindTabs = $derived<[string, string, number][]>([
		['', 'search.filterAll', base.length],
		['questions', KIND_LABEL.questions, base.length - guideCount],
		['guides', KIND_LABEL.guides, guideCount]
	]);
	const SORT_LABEL: Record<ArticleSort, string> = {
		featured: 'common.sortShelf',
		newest: 'search.sortNewest',
		shortest: 'common.sortShortest',
		title: 'common.sortTitle'
	};

	// --- Arrangement (persisted per device, like the Books/Sermons shelves) ----
	const PREFS_KEY = 'ochorus:articles-view';
	let sort = $state<ArticleSort>('featured');
	// Hydrated after mount: the page is prerendered, so reading localStorage
	// while rendering would desync the static HTML from the client.
	onMount(() => {
		const p = readJSON<{ sort?: ArticleSort }>(PREFS_KEY, {});
		if (p.sort && (ARTICLE_SORTS as readonly string[]).includes(p.sort)) sort = p.sort;
	});
	const save = () => writeJSON(PREFS_KEY, { sort });

	const filtered = $derived(
		base.filter((a) => ofKind(a, filters.values.kind) && matchesQuery(a, filters.values.q))
	);
	const shown = $derived(sortArticles(filtered, sort));

	// The guides view is a shelf of covers — each guide is ABOUT one book, so
	// the book is the thing to recognise. Everything else is a list of rows.
	const asCovers = $derived(filters.values.kind === 'guides');

	const activeChips = $derived.by(() => {
		const c: FilterChip[] = [];
		const q = queryChip(filters);
		if (q) c.push(q);
		const k = filters.values.kind as ArticleKind;
		if (k)
			c.push({ kind: 'kind', label: t(KIND_LABEL[k]), onRemove: () => (filters.values.kind = '') });
		return c;
	});

	// --- Show more -----------------------------------------------------------
	// A page at a time, so the index is not 130 rows deep on arrival. The count
	// belongs to one filter state: change the filters and it starts over. Kept
	// as (key, count) rather than reset in an effect — an $effect that writes
	// state is a $derived in disguise (frontend/CLAUDE.md).
	const PAGE = 24;
	const viewKey = $derived(`${activeTopic}|${filters.values.kind}|${filters.values.q}|${sort}`);
	let expanded = $state({ key: '', count: PAGE });
	const limit = $derived(expanded.key === viewKey ? expanded.count : PAGE);
	const visible = $derived(shown.slice(0, limit));
	const remaining = $derived(shown.length - visible.length);
	const showMore = () => (expanded = { key: viewKey, count: limit + PAGE });
</script>

<!-- The Questions / Book guides switch — inline from sm, and in the phone
     sheet below it. -->
{#snippet kindSeg(cls: string, btnCls: string)}
	<div class="seg {cls}">
		{#each kindTabs as [k, label, n] (k)}
			<button
				class={btnCls}
				class:active={filters.values.kind === k}
				aria-pressed={filters.values.kind === k}
				onclick={() => (filters.values.kind = k)}>{t(label)} <span class="count">{n}</span></button
			>
		{/each}
	</div>
{/snippet}

<!-- Below sm: search + a Filters button whose sheet holds sort and kind (the
     three controls stacked ~170px above the topic chips). From sm, inline. -->
<div class="filter-row mb-4">
	<input
		bind:value={filters.values.q}
		type="search"
		autocomplete="off"
		placeholder={t('articles.filterPlaceholder')}
		aria-label={t('articles.filterPlaceholder')}
		class="filter-field grow"
	/>
	<FilterSheet
		count={filters.values.kind ? 1 : 0}
		shown={filtered.length}
		showLabel={t('articles.showResults')}
		filtered={filters.active}
		onClear={() => filters.reset()}
	>
		<SheetChoices
			label={t('common.sort')}
			options={ARTICLE_SORTS.map((v) => ({ v, label: t(SORT_LABEL[v]) }))}
			value={sort}
			onselect={(v) => ((sort = v), save())}
		/>
		{#if showKinds}
			{@render kindSeg('w-full', 'flex-1')}
		{/if}
	</FilterSheet>
	<div class="hidden sm:contents">
		<select bind:value={sort} onchange={save} class="filter-field" aria-label={t('common.sort')}>
			{#each ARTICLE_SORTS as s (s)}
				<option value={s}>{t(SORT_LABEL[s])}</option>
			{/each}
		</select>
		{#if showKinds}
			{@render kindSeg('', '')}
		{/if}
	</div>
</div>

{#if topicTabs.length > 1}
	<nav class="chip-scroller mb-6" aria-label={t('articles.filterByTopic')}>
		<a
			class="chip"
			class:active={activeTopic === ''}
			aria-current={activeTopic === '' ? 'page' : undefined}
			href="/articles/"
		>
			{t('search.filterAll')}<span class="count">{articles.length}</span>
		</a>
		{#each topicTabs as tab (tab.slug)}
			<a
				class="chip"
				class:active={activeTopic === tab.slug}
				aria-current={activeTopic === tab.slug ? 'page' : undefined}
				href="/articles/{tab.slug}/"
			>
				{tab.title}<span class="count">{tab.count}</span>
			</a>
		{/each}
	</nav>
{/if}

{#if filters.active}
	<FilterSummary
		shown={filtered.length}
		total={base.length}
		template={t('articles.showing')}
		onClear={() => filters.reset()}
		chips={activeChips}
		class="mb-6"
	/>
{/if}

{#if shown.length === 0}
	<!-- Filtered to nothing, or (only via a stale/hand-edited topic slug — a
	     live chip always has ≥1 article) an empty topic. -->
	<EmptyState message={filters.active ? t('articles.noMatches') : t('articles.emptyTopic')} />
{:else if asCovers}
	<div class="book-grid">
		{#each visible as a (a.slug)}
			<a href="/articles/{a.slug}/" class="book-card card-lift group">
				{#if a.lead_book}
					<BookCover book={a.lead_book} />
				{:else}
					<!-- No published book to show: hold the cover's 3:4 box so the
					     grid row stays aligned. -->
					<div class="rounded-card border border-dashed border-border" style="aspect-ratio: 3 / 4"></div>
				{/if}
				<div class="mt-2 flex flex-1 flex-col px-0.5">
					<svelte:element
						this={heading}
						class="line-clamp-2 text-small font-medium leading-snug text-text"
					>
						{a.lead_book?.title ?? a.h1}
					</svelte:element>
					{#if a.lead_book}
						<p class="truncate text-small text-muted">{a.lead_book.author.name}</p>
					{/if}
					<p class="mt-auto pt-0.5 text-eyebrow text-muted">
						{t('book.readersGuide')}<span class="opacity-50">{' · '}</span>{readingTime(a.word_count)}
					</p>
				</div>
			</a>
		{/each}
	</div>
{:else}
	<div class="flex flex-col gap-3">
		{#each visible as a (a.slug)}
			<ArticleCard article={a} {heading} />
		{/each}
	</div>
{/if}

{#if remaining > 0}
	<div class="mt-8 flex justify-center">
		<button class="btn btn-ghost" onclick={showMore}>
			{t('bios.showMore').replace('%n%', String(Math.min(PAGE, remaining)))}
		</button>
	</div>
{/if}
