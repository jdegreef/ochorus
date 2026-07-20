<script lang="ts">
	import { search, type SearchHit, type ChapterHit } from '$lib/library';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
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
					snippet: hit.snippet
				};
			case 'book':
				return {
					key: 'book:' + hit.book_slug,
					label: t('search.typeBook'),
					href: `/books/${hit.book_slug}`,
					title: hit.book_title,
					meta: hit.author_name,
					snippet: hit.snippet
				};
			case 'topic':
				return {
					key: 'topic:' + hit.topic_slug,
					label: t('search.typeTopic'),
					href: `/topics/${hit.topic_slug}`,
					title: hit.topic_title,
					meta: '',
					snippet: hit.snippet
				};
			case 'plan':
				return {
					key: 'plan:' + hit.plan_slug,
					label: t('search.typePlan'),
					href: `/plans/${hit.plan_slug}`,
					title: hit.plan_title,
					meta: '',
					snippet: hit.snippet
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
					snippet: hit.snippet
				};
			default:
				return {
					key: `chapter:${hit.book_slug}:${hit.chapter_order}`,
					label: t('search.typeChapter'),
					href: `/books/${hit.book_slug}/${hit.chapter_order}`,
					title: hit.chapter_title || hit.book_title,
					meta: `${hit.book_title} · ${hit.author_name}`,
					snippet: hit.snippet
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
			rows: by.get(g.type)!
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
		chapters: { key: string; order: number; title: string; snippet: string }[];
	};
	const passageBooks = $derived.by<PassageBook[]>(() => {
		const by = new Map<string, PassageBook>();
		for (const h of hits) {
			if (h.type !== 'chapter') continue;
			const c = h as ChapterHit;
			let g = by.get(c.book_slug);
			if (!g) {
				g = { slug: c.book_slug, title: c.book_title, author: c.author_name, chapters: [] };
				by.set(c.book_slug, g);
			}
			g.chapters.push({
				key: `${c.book_slug}:${c.chapter_order}`,
				order: c.chapter_order,
				title: c.chapter_title || c.book_title,
				snippet: c.snippet
			});
		}
		return [...by.values()];
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
	}

	async function runSearch(term: string) {
		// Responses can land out of order (a cold body-text scan overtaken by a
		// cached one), so only the newest request may write the list — otherwise
		// an older reply repaints stale hits over the term the reader can see.
		const token = ++searchSeq;
		loading = true;
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
		if (to && to.url.pathname !== $page.url.pathname) clearTimeout(timer);
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
</script>

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
			<p class="text-small text-muted">{t('search.prompt')}</p>
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
				<p class="text-small text-muted sm:ml-auto" aria-live="polite">
					{shownCount}
					{shownCount === 1 ? t('search.resultsOne') : t('search.resultsMany')}
				</p>
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
</style>
