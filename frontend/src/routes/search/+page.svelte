<script lang="ts">
	import { onMount } from 'svelte';
	import {
		search,
		listTopics,
		getPopularSearches,
		type SearchHit,
		type ChapterHit,
		type TopicSummary
	} from '$lib/library';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { apiFetch } from '$lib/api';
	import { readJSON, writeJSON } from '$lib/persisted';
	import type { ScriptureResult } from '$lib/scripture.svelte';
	import { markSnippet } from '$lib/highlight';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { beforeNavigate, goto } from '$app/navigation';
	import { page } from '$app/stores';

	const t = i18n.t;

	// One flat shape for every hit type, so the list renders uniformly (and so
	// grouping by type is a small step from here). `label` is the type chip;
	// `meta` is the muted line under the title; `snippet` may be empty for
	// entities with no prose.
	type Row = {
		key: string;
		label: string;
		href: string;
		title: string;
		meta: string;
		snippet: string;
		date: string;
	};

	function toRow(hit: SearchHit): Row {
		switch (hit.type) {
			case 'author':
				return {
					key: 'author:' + hit.author_slug,
					label: t('search.typeAuthor'),
					href: `/authors/${hit.author_slug}`,
					title: hit.author_name,
					meta: '',
					snippet: hit.snippet,
					date: hit.date
				};
			case 'book':
				return {
					key: 'book:' + hit.book_slug,
					label: t('search.typeBook'),
					href: `/books/${hit.book_slug}`,
					title: hit.book_title,
					meta: hit.author_name,
					snippet: hit.snippet,
					date: hit.date
				};
			case 'topic':
				return {
					key: 'topic:' + hit.topic_slug,
					label: t('search.typeTopic'),
					href: `/topics/${hit.topic_slug}`,
					title: hit.topic_title,
					meta: '',
					snippet: hit.snippet,
					date: hit.date
				};
			case 'plan':
				return {
					key: 'plan:' + hit.plan_slug,
					label: t('search.typePlan'),
					href: `/plans/${hit.plan_slug}`,
					title: hit.plan_title,
					meta: '',
					snippet: hit.snippet,
					date: hit.date
				};
			case 'sermon':
				return {
					key: 'sermon:' + hit.sermon_slug,
					label: t('search.typeSermon'),
					href: `/sermons/${hit.sermon_slug}`,
					title: hit.sermon_title,
					meta: hit.scripture_ref
						? `${hit.author_name} · ${hit.scripture_ref}`
						: hit.author_name,
					snippet: hit.snippet,
					date: hit.date
				};
			default:
				return {
					key: `chapter:${hit.book_slug}:${hit.chapter_order}`,
					label: t('search.typeChapter'),
					href: `/books/${hit.book_slug}/${hit.chapter_order}`,
					title: hit.chapter_title || hit.book_title,
					meta: `${hit.book_title} · ${hit.author_name}`,
					snippet: hit.snippet,
					date: hit.date
				};
		}
	}
	let q = $state('');
	let hits = $state<SearchHit[]>([]);
	let loading = $state(false);
	let ran = $state('');
	let suggestion = $state('');
	let timer: ReturnType<typeof setTimeout> | undefined;
	// The query currently reflected in the URL. Plain (non-reactive) — it exists
	// only to tell "the reader navigated" apart from "we just wrote the URL".
	// Set before the goto, which is safe because SvelteKit cancels a superseded
	// navigation, so an earlier goto can never land after a later one.
	let urlQuery = '';
	// Monotonic token: only the newest in-flight search may write the results.
	let searchSeq = 0;

	type ResultRow = Row & { type: SearchHit['type'] };
	const rows = $derived<ResultRow[]>(hits.map((h) => ({ ...toRow(h), type: h.type })));

	// Sort order applied *within* each type section (grouping stays by type).
	// 'relevance' keeps the server's ranking; the others reorder the fetched set
	// locally — no round-trip. Array.sort is stable, so ties keep relevance order.
	type SortMode = 'relevance' | 'title' | 'newest';
	let sortMode = $state<SortMode>('relevance');
	const SORTS: SortMode[] = ['relevance', 'title', 'newest'];
	function sorted<T extends { title: string; date: string }>(arr: T[]): T[] {
		if (sortMode === 'title') return [...arr].sort((a, b) => a.title.localeCompare(b.title));
		if (sortMode === 'newest') return [...arr].sort((a, b) => (b.date || '').localeCompare(a.date || ''));
		return arr;
	}

	// Cluster the flat result list into type sections in a fixed reading order —
	// navigational entities first, passages last — keeping only sections present.
	const GROUP_ORDER: { type: SearchHit['type']; labelKey: string }[] = [
		{ type: 'book', labelKey: 'search.groupBooks' },
		{ type: 'author', labelKey: 'search.groupAuthors' },
		{ type: 'topic', labelKey: 'search.groupTopics' },
		{ type: 'plan', labelKey: 'search.groupPlans' },
		{ type: 'chapter', labelKey: 'search.groupPassages' },
		{ type: 'sermon', labelKey: 'search.groupSermons' }
	];
	const groups = $derived.by(() => {
		const by = new Map<string, ResultRow[]>();
		for (const r of rows) {
			const arr = by.get(r.type);
			if (arr) arr.push(r);
			else by.set(r.type, [r]);
		}
		return GROUP_ORDER.filter((g) => by.has(g.type)).map((g) => ({
			type: g.type,
			labelKey: g.labelKey,
			rows: sorted(by.get(g.type)!)
		}));
	});

	// Type facet: narrow the result set to one kind. Chips are built from the
	// groups actually present (with counts); selecting one shows only that
	// section. Reset to "all" on each new query.
	let typeFilter = $state('all');
	const shownGroups = $derived(
		typeFilter === 'all' || !groups.some((g) => g.type === typeFilter)
			? groups
			: groups.filter((g) => g.type === typeFilter)
	);
	const shownCount = $derived(shownGroups.reduce((n, g) => n + g.rows.length, 0));

	// Within the Passages section, collapse a book's chapter matches under the
	// book so "where does this theme live across the work" reads as a map, not a
	// scatter of unrelated-looking lines. Books over the preview cap get a toggle.
	const PASSAGE_PREVIEW = 3;
	let expandedBooks = $state(new Set<string>());

	type PassageBook = {
		slug: string;
		title: string;
		author: string;
		date: string;
		chapters: { key: string; order: number; title: string; snippet: string }[];
	};
	const passageBooks = $derived.by<PassageBook[]>(() => {
		const by = new Map<string, PassageBook>();
		for (const h of hits) {
			if (h.type !== 'chapter') continue;
			const c = h as ChapterHit;
			let g = by.get(c.book_slug);
			if (!g) {
				g = {
					slug: c.book_slug,
					title: c.book_title,
					author: c.author_name,
					date: c.date,
					chapters: []
				};
				by.set(c.book_slug, g);
			}
			g.chapters.push({
				key: `${c.book_slug}:${c.chapter_order}`,
				order: c.chapter_order,
				title: c.chapter_title || c.book_title,
				snippet: c.snippet
			});
		}
		// The sort toggle reorders the books; chapters keep their in-book order.
		return sorted([...by.values()]);
	});

	function toggleBook(slug: string) {
		const next = new Set(expandedBooks);
		if (next.has(slug)) next.delete(slug);
		else next.add(slug);
		expandedBooks = next;
	}

	// --- Keyboard navigation ---------------------------------------------------
	// Flatten the *visible* leaf results (entity/sermon rows + the shown passage
	// chapters, in display order) so ↑/↓ walk them and Enter opens the active one.
	let activeIndex = $state(-1);
	const nav = $derived.by(() => {
		const keys: string[] = [];
		const map = new Map<string, string>();
		for (const g of shownGroups) {
			if (g.type === 'chapter') {
				for (const pb of passageBooks) {
					const shown = expandedBooks.has(pb.slug)
						? pb.chapters
						: pb.chapters.slice(0, PASSAGE_PREVIEW);
					for (const ch of shown) {
						keys.push(ch.key);
						map.set(ch.key, `/books/${pb.slug}/${ch.order}`);
					}
				}
			} else {
				for (const row of g.rows) {
					keys.push(row.key);
					map.set(row.key, row.href);
				}
			}
		}
		return { keys, map };
	});
	const activeKey = $derived(
		activeIndex >= 0 && activeIndex < nav.keys.length ? nav.keys[activeIndex] : ''
	);

	// Keep the highlighted result in view as it moves.
	$effect(() => {
		if (activeKey) document.getElementById(`res-${activeKey}`)?.scrollIntoView({ block: 'nearest' });
	});

	function onKeydown(e: KeyboardEvent) {
		const n = nav.keys.length;
		if (!n) return;
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			activeIndex = (activeIndex + 1) % n;
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			activeIndex = activeIndex <= 0 ? n - 1 : activeIndex - 1;
		} else if (e.key === 'Enter') {
			const key = activeIndex >= 0 ? nav.keys[activeIndex] : nav.keys[0];
			const href = nav.map.get(key);
			if (href) goto(localizeHref(href));
		} else if (e.key === 'Escape') {
			activeIndex = -1;
		}
	}

	function clearResults() {
		hits = [];
		ran = '';
		suggestion = '';
		scriptureAnswer = null;
	}

	// --- Instant scripture answer ----------------------------------------------
	// When the query looks like a Bible reference ("John 3:16", "1 Cor 13",
	// "Psalm 23"), fetch the passage and show it above the results — the answer,
	// not just links to sermons about it. The backend is the real judge: a
	// non-reference simply returns nothing and the card stays hidden.
	let scriptureAnswer = $state<ScriptureResult | null>(null);
	const REF_RE = /^\s*(?:[123]\s*|I{1,3}\s+)?[A-Za-z][A-Za-z.]{1,}\s+\d{1,3}(?::\d{1,3}(?:[-–]\d{1,3})?)?\s*$/;

	async function maybeScripture(term: string, token: number) {
		if (!REF_RE.test(term)) {
			scriptureAnswer = null;
			return;
		}
		try {
			const data = await apiFetch<ScriptureResult>(
				`/api/library/scripture/?ref=${encodeURIComponent(term)}`
			);
			if (token !== searchSeq) return;
			scriptureAnswer = data?.verses?.length ? data : null;
		} catch {
			if (token === searchSeq) scriptureAnswer = null;
		}
	}

	async function runSearch(term: string) {
		// Responses can land out of order (a cold body-text scan overtaken by a
		// cached one), so only the newest request may write the list — otherwise
		// an older reply repaints stale hits over the term the reader can see.
		const token = ++searchSeq;
		loading = true;
		void maybeScripture(term, token); // in parallel; independent of the list
		try {
			const res = await search(term, getLang());
			if (token !== searchSeq) return;
			hits = res.results;
			ran = res.query;
			suggestion = res.suggestion ?? '';
		} finally {
			if (token === searchSeq) loading = false;
		}
	}

	/**
	 * Mirror the query into ?q= so a search is linkable, survives a reload, and
	 * comes back intact when the reader returns with Back after opening a result.
	 * replaceState (not push) so typing doesn't bury their history; keepFocus so
	 * the caret stays in the box mid-word.
	 */
	function syncUrl(term: string) {
		if (term === urlQuery) return;
		urlQuery = term;
		const url = new URL($page.url);
		if (term) url.searchParams.set('q', term);
		else url.searchParams.delete('q');
		goto(url, { replaceState: true, keepFocus: true, noScroll: true });
	}

	/** Show `term`: reset the list state, then search it (or clear if too short). */
	function applyTerm(term: string) {
		clearTimeout(timer);
		activeIndex = -1;
		typeFilter = 'all';
		sortMode = 'relevance';
		if (term.length < 2) clearResults();
		else runSearch(term);
	}

	function onInput() {
		const term = q.trim();
		if (term.length < 2) {
			applyTerm(term); // drops any pending search and clears the list
			syncUrl('');
			return;
		}
		// Reset the facet/selection on the keystroke, not 250ms later: the list
		// stops looking filtered the moment the query changes, and a chip the
		// reader clicks while waiting for results isn't yanked out from under
		// them when the debounce fires.
		clearTimeout(timer);
		activeIndex = -1;
		typeFilter = 'all';
		sortMode = 'relevance';
		timer = setTimeout(() => {
			syncUrl(term);
			runSearch(term);
		}, 250);
	}

	// A pending debounce must not survive the reader leaving. Its callback
	// navigates (syncUrl -> goto), and that goto would *cancel* the navigation
	// they just started — clicking a result while a keystroke is still debouncing
	// would pull them straight back to /search. Clear it as the departure begins;
	// a destroy-time cleanup is too late, since the timer fires first.
	// Our own ?q= writes keep the same path, so they must not cancel the search.
	beforeNavigate(({ to }) => {
		if (to && to.url.pathname !== $page.url.pathname) {
			clearTimeout(timer);
			// Opening a result (or any departure to a real page) means this search
			// was useful — remember it for the empty-state shortcuts.
			recordRecent(ran || q);
		}
	});

	// The URL is the source of truth for which search is showing: this covers the
	// first load of a shared /search?q=… link and the Back/Forward buttons. The
	// urlQuery guard is what stops a loop — syncUrl sets it before writing the
	// URL, so the effect our own write triggers falls straight through.
	$effect(() => {
		const term = ($page.url.searchParams.get('q') ?? '').trim();
		if (term === urlQuery) return;
		urlQuery = term;
		q = term;
		applyTerm(term);
	});

	// Accept a "did you mean" suggestion: swap it in and search immediately.
	function applySuggestion(term: string) {
		q = term;
		onInput();
	}

	// Server snippets arrive with matches wrapped in full-text markers; markSnippet
	// escapes them and swaps the markers for <mark> (shared with the in-book search).
	const mark = markSnippet;

	// --- Empty-state suggestions -----------------------------------------------
	// A blank search page is dead space; fill it with the reader's recent
	// searches (device-local) and a few topics to browse into.
	const RECENT_KEY = 'ochorus:recent-searches';
	let recent = $state<string[]>([]);
	let topics = $state<TopicSummary[]>([]);

	// What other readers search most (aggregate, server-side). Empty when the
	// log is too sparse — the section simply doesn't render.
	let popular = $state<string[]>([]);

	onMount(() => {
		recent = readJSON<string[]>(RECENT_KEY, []).filter((s) => typeof s === 'string');
		listTopics(getLang())
			.then((all) => (topics = all.slice(0, 10)))
			.catch(() => (topics = []));
		getPopularSearches(getLang())
			.then((r) => (popular = r.queries ?? []))
			.catch(() => (popular = []));
	});

	/** Remember a query that led somewhere (most-recent-first, deduped, capped). */
	function recordRecent(term: string) {
		const t2 = term.trim();
		if (t2.length < 2) return;
		recent = [t2, ...recent.filter((r) => r.toLowerCase() !== t2.toLowerCase())].slice(0, 6);
		writeJSON(RECENT_KEY, recent);
	}
	function clearRecent() {
		recent = [];
		writeJSON(RECENT_KEY, []);
	}
</script>

<!-- A clickable query chip — shared by the "recent" and "popular" rows, which
     render identically (both re-run the search via applySuggestion). -->
{#snippet queryChip(term: string)}
	<button
		type="button"
		class="rounded-full border border-border px-3 py-1 text-small text-text hover:border-accent hover:text-accent"
		onclick={() => applySuggestion(term)}
	>
		{term}
	</button>
{/snippet}

<svelte:head><title>{t('search.title')} — Ochorus</title></svelte:head>

<div class="mx-auto max-w-2xl px-5 py-10">
	<h1 class="text-h1 mb-8">{t('search.title')}</h1>

	<input
		bind:value={q}
		oninput={onInput}
		onkeydown={onKeydown}
		type="search"
		autocomplete="off"
		role="combobox"
		aria-expanded={hits.length > 0}
		aria-controls="search-results"
		placeholder={t('search.placeholder')}
		aria-label={t('search.title')}
		class="w-full rounded-card border border-border bg-surface px-4 py-3 text-body text-text"
	/>

	{#if scriptureAnswer}
		<!-- Instant scripture answer: the passage text for a reference query. -->
		<div class="mt-6 rounded-card border-l-4 border-accent bg-accent-soft p-4">
			<p class="text-[0.66rem] font-bold uppercase tracking-[0.1em] text-accent">
				{t('reader.scripture')}
			</p>
			<p class="scripture-answer-ref">{scriptureAnswer.reference}</p>
			<p class="scripture-answer-body mt-2">
				{#each scriptureAnswer.verses as v (v.number)}<sup class="scripture-answer-num"
						>{v.number}</sup
					>{v.text}{' '}{/each}
			</p>
			<p class="mt-2 text-[0.66rem] uppercase tracking-[0.08em] text-muted">
				{scriptureAnswer.version}
			</p>
		</div>
	{/if}

	<div class="mt-6" id="search-results">
		{#if loading}
			<div class="space-y-6" aria-hidden="true">
				{#each Array(4) as _, i (i)}
					<div class="animate-pulse space-y-2">
						<div class="h-3 w-1/4 rounded bg-surface-2"></div>
						<div class="h-4 w-2/3 rounded bg-surface-2"></div>
						<div class="h-3 w-full rounded bg-surface-2"></div>
					</div>
				{/each}
			</div>
		{:else if q.trim().length < 2}
			{#if recent.length}
				<section class="mb-8">
					<div class="mb-2 flex items-center justify-between">
						<h2 class="text-small font-semibold uppercase tracking-wide text-muted">
							{t('search.recent')}
						</h2>
						<button type="button" class="text-small text-accent hover:underline" onclick={clearRecent}>
							{t('search.clearRecent')}
						</button>
					</div>
					<div class="flex flex-wrap gap-2">
						{#each recent as term (term)}{@render queryChip(term)}{/each}
					</div>
				</section>
			{/if}
			{#if popular.length}
				<section class="mb-8">
					<h2 class="mb-2 text-small font-semibold uppercase tracking-wide text-muted">
						{t('search.popular')}
					</h2>
					<div class="flex flex-wrap gap-2">
						{#each popular as term (term)}{@render queryChip(term)}{/each}
					</div>
				</section>
			{/if}
			{#if topics.length}
				<section>
					<h2 class="mb-2 text-small font-semibold uppercase tracking-wide text-muted">
						{t('search.browseTopics')}
					</h2>
					<div class="flex flex-wrap gap-2">
						{#each topics as tp (tp.slug)}
							<a
								href={localizeHref(`/topics/${tp.slug}`)}
								class="rounded-full border border-border px-3 py-1 text-small text-text hover:border-accent hover:text-accent hover:no-underline"
							>
								{tp.title}
							</a>
						{/each}
					</div>
				</section>
			{/if}
			{#if !recent.length && !topics.length && !popular.length}
				<p class="text-small text-muted">{t('search.prompt')}</p>
			{/if}
		{:else if ran && hits.length === 0}
			<p class="text-small text-muted">{t('search.noResults')} “{ran}”.</p>
			{#if suggestion}
				<p class="mt-2 text-small text-muted">
					{t('search.didYouMean')}
					<button
						type="button"
						class="font-semibold text-accent hover:underline"
						onclick={() => applySuggestion(suggestion)}
					>
						{suggestion}
					</button>?
				</p>
			{/if}
		{:else}
			<!-- Type facet + result count -->
			<div class="mb-5 flex flex-wrap items-center gap-2">
				{#if groups.length > 1}
					<div class="flex flex-wrap gap-1.5" role="group" aria-label={t('search.filterByType')}>
						<button
							type="button"
							class="rounded-full border px-2.5 py-1 text-[0.78rem]"
							class:border-accent={typeFilter === 'all'}
							class:bg-accent={typeFilter === 'all'}
							class:text-accent-contrast={typeFilter === 'all'}
							class:border-border={typeFilter !== 'all'}
							class:text-muted={typeFilter !== 'all'}
							onclick={() => (typeFilter = 'all')}
							aria-pressed={typeFilter === 'all'}
						>
							{t('search.filterAll')}
						</button>
						{#each groups as g (g.type)}
							<button
								type="button"
								class="rounded-full border px-2.5 py-1 text-[0.78rem]"
								class:border-accent={typeFilter === g.type}
								class:bg-accent={typeFilter === g.type}
								class:text-accent-contrast={typeFilter === g.type}
								class:border-border={typeFilter !== g.type}
								class:text-muted={typeFilter !== g.type}
								onclick={() => (typeFilter = g.type)}
								aria-pressed={typeFilter === g.type}
							>
								{t(g.labelKey)}
								<span class="tabular-nums opacity-70">{g.rows.length}</span>
							</button>
						{/each}
					</div>
				{/if}
				<div class="flex flex-wrap items-center gap-x-3 gap-y-2 sm:ml-auto">
					{#if shownCount > 1}
						<div class="flex items-center gap-1.5" role="group" aria-label={t('search.sortBy')}>
							<span class="text-small text-muted">{t('search.sortBy')}</span>
							<div class="flex overflow-hidden rounded-full border border-border">
								{#each SORTS as s, i (s)}
									<button
										type="button"
										class="px-2.5 py-1 text-[0.78rem]"
										class:bg-accent={sortMode === s}
										class:text-accent-contrast={sortMode === s}
										class:text-muted={sortMode !== s}
										class:border-l={i > 0}
										class:border-border={i > 0}
										onclick={() => (sortMode = s)}
										aria-pressed={sortMode === s}
									>
										{t(`search.sort_${s}`)}
									</button>
								{/each}
							</div>
						</div>
					{/if}
					<p class="text-small text-muted" aria-live="polite">
						{shownCount}
						{shownCount === 1 ? t('search.resultsOne') : t('search.resultsMany')}
					</p>
				</div>
			</div>
			<div class="space-y-8">
				{#each shownGroups as g (g.type)}
					<section>
						<h2
							class="mb-2 flex items-baseline gap-2 text-small font-semibold uppercase tracking-wide text-muted"
						>
							{t(g.labelKey)}
							<span class="text-[0.78rem] font-normal tabular-nums text-muted/70">{g.rows.length}</span>
						</h2>
						{#if g.type === 'chapter'}
							<!-- Passages: matches collapsed under their book. -->
							<div class="space-y-5">
								{#each passageBooks as pb (pb.slug)}
									{@const expanded = expandedBooks.has(pb.slug)}
									{@const shown = expanded ? pb.chapters : pb.chapters.slice(0, PASSAGE_PREVIEW)}
									<div>
										<a
											href={localizeHref(`/books/${pb.slug}`)}
											class="text-small font-semibold text-text hover:text-accent hover:no-underline"
										>
											{pb.title} <span class="font-normal text-muted">· {pb.author}</span>
										</a>
										<ul class="mt-1 divide-y divide-border border-l border-border pl-3">
											{#each shown as ch (ch.key)}
												<li class="py-2.5">
													<a
														href={localizeHref(`/books/${pb.slug}/${ch.order}`)}
														id="res-{ch.key}"
														class="-mx-2 block rounded px-2 hover:no-underline"
														class:bg-surface-2={ch.key === activeKey}
													>
														<div class="text-small font-medium text-text">{ch.title}</div>
														{#if ch.snippet}
															<p class="mt-0.5 text-small text-muted">
																<!-- eslint-disable-next-line svelte/no-at-html-tags -->
																{@html mark(ch.snippet)}
															</p>
														{/if}
													</a>
												</li>
											{/each}
										</ul>
										{#if pb.chapters.length > PASSAGE_PREVIEW}
											<button
												type="button"
												onclick={() => toggleBook(pb.slug)}
												class="mt-1.5 pl-3 text-small font-semibold text-accent"
											>
												{#if expanded}
													{t('search.showLess')}
												{:else}
													+{pb.chapters.length - PASSAGE_PREVIEW} {t('search.morePassages')}
												{/if}
											</button>
										{/if}
									</div>
								{/each}
							</div>
						{:else}
							<ul class="divide-y divide-border">
								{#each g.rows as row (row.key)}
									<li class="py-4">
										<a
											href={localizeHref(row.href)}
											id="res-{row.key}"
											class="-mx-2 block rounded px-2 hover:no-underline"
											class:bg-surface-2={row.key === activeKey}
										>
											{#if row.meta}
												<div class="text-small text-muted">{row.meta}</div>
											{/if}
											<div class="text-body font-semibold text-text">{row.title}</div>
											{#if row.snippet}
												<p class="mt-1 text-small text-muted">
													<!-- eslint-disable-next-line svelte/no-at-html-tags -->
													{@html mark(row.snippet)}
												</p>
											{/if}
										</a>
									</li>
								{/each}
							</ul>
						{/if}
					</section>
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	:global(.text-muted mark) {
		background: color-mix(in srgb, var(--gold) 30%, transparent);
		color: var(--text);
		border-radius: 3px;
		padding: 0 0.15em;
	}
	.scripture-answer-ref {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		color: var(--accent);
		margin-top: 0.1rem;
	}
	.scripture-answer-body {
		font-family: var(--font-display);
		font-style: italic;
		line-height: 1.6;
		color: var(--text);
	}
	.scripture-answer-num {
		font-size: 0.62em;
		font-weight: 600;
		color: var(--muted);
		margin-right: 0.15em;
		vertical-align: super;
		font-style: normal;
	}
</style>
