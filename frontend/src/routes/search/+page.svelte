<script lang="ts">
	import { onMount } from 'svelte';
	import {
		search,
		searchPage,
		listTopics,
		getPopularSearches,
		recordSearchClick,
		type SearchHit,
		type ChapterHit,
		type SearchScope,
		type SearchSort,
		type SearchType,
		type TopicSummary
	} from '$lib/library';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { apiFetch } from '$lib/api';
	import { readJSON, writeJSON } from '$lib/persisted';
	import { readSearchState, searchStateKey, writeSearchState } from '$lib/searchState';
	import { portraitPosition } from '$lib/portraits';
	import type { ScriptureResult } from '$lib/scripture.svelte';
	import { markSnippet } from '$lib/highlight';
	import { localizeHref } from '$lib/href';
	import { SITE_URL } from '$lib/config';
	import { hreflangAll } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import { page } from '$app/stores';
	import PageHeader from '$lib/components/PageHeader.svelte';

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
		/** Cover or portrait. "" for rows that have neither — topics and plans. */
		image: string;
		/** Backing colour for the reserved box, so the list never reflows. */
		color: string;
		/** Portraits are round and small; covers keep a book's proportions. */
		round: boolean;
		/** Where the face sits in a portrait; unset for covers, which crop nothing. */
		focus?: string;
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
					date: hit.date,
					image: hit.photo_url,
					color: '',
					round: true,
					focus: portraitPosition(hit.author_slug)
				};
			case 'book':
				return {
					key: 'book:' + hit.book_slug,
					label: t('search.typeBook'),
					href: `/books/${hit.book_slug}`,
					title: hit.book_title,
					meta: hit.author_name,
					snippet: hit.snippet,
					date: hit.date,
					image: hit.cover_url,
					color: hit.cover_color,
					round: false
				};
			case 'topic':
				return {
					key: 'topic:' + hit.topic_slug,
					label: t('search.typeTopic'),
					href: `/topics/${hit.topic_slug}`,
					title: hit.topic_title,
					meta: '',
					snippet: hit.snippet,
					date: hit.date,
					image: '',
					color: '',
					round: false
				};
			case 'plan':
				return {
					key: 'plan:' + hit.plan_slug,
					label: t('search.typePlan'),
					href: `/plans/${hit.plan_slug}`,
					title: hit.plan_title,
					meta: '',
					snippet: hit.snippet,
					date: hit.date,
					image: '',
					color: '',
					round: false
				};
			case 'sermon':
				return {
					key: 'sermon:' + hit.sermon_slug,
					label: t('search.typeSermon'),
					href: `/sermons/${hit.sermon_slug}?q=${encodeURIComponent(ran || q.trim())}`,
					title: hit.sermon_title,
					meta: hit.scripture_ref
						? `${hit.author_name} · ${hit.scripture_ref}`
						: hit.author_name,
					snippet: hit.snippet,
					date: hit.date,
					image: '',
					color: '',
					round: false
				};
			default:
				return {
					key: `chapter:${hit.book_slug}:${hit.chapter_order}`,
					label: t('search.typeChapter'),
					// The query rides along so the reader lands on the match rather than
					// at the top of the chapter.
					href: `/books/${hit.book_slug}/${hit.chapter_order}?q=${encodeURIComponent(ran || q.trim())}`,
					title: hit.chapter_title || hit.book_title,
					meta: `${hit.book_title} · ${hit.author_name}`,
					snippet: hit.snippet,
					date: hit.date,
					image: hit.cover_url,
					color: hit.cover_color,
					round: false
				};
		}
	}
	// "Search inside this author / topic / book", carried as `kind:slug`. The
	// label comes back with the results (`scopeInfo`) so the chip can name the
	// shelf without a second request; null means the server found no such shelf
	// in this language, and the page says so instead of showing an empty list.
	let scope = $state('');
	let scopeInfo = $state<SearchScope | null>(null);

	let q = $state('');
	let hits = $state<SearchHit[]>([]);
	let loading = $state(false);
	/** Measured height of the pinned search box — the rail and the group
	    anchors below both clear it via `--pinned-offset`. */
	let searchBarH = $state(0);
	let searchError = $state(false);
	let ran = $state('');
	let suggestion = $state('');
	let timer: ReturnType<typeof setTimeout> | undefined;
	// The view currently reflected in the URL — query, type facet and sort, as one
	// string. Plain (non-reactive): it exists only to tell "the reader navigated"
	// apart from "we just wrote the URL". Set before the goto, which is safe
	// because SvelteKit cancels a superseded navigation, so an earlier goto can
	// never land after a later one.
	//
	// The facet is in the URL because a filtered view is a real view: worth
	// sharing, worth surviving a reload, and worth coming back to when the reader
	// opens a passage and presses Back.
	let urlState = '';
	// Monotonic token: only the newest in-flight search may write the results.
	let searchSeq = 0;

	// How many matches EXIST per type. The merged list above is capped per type
	// (so no one kind crowds out the others), which used to be invisible: the
	// page reported the number of rows it had been handed, and a search matching
	// four hundred passages rendered "30 results". These are what let it say
	// "20 of 400" instead.
	let totals = $state<Partial<Record<SearchType, number>>>({});
	let totalsCapped = $state<Partial<Record<SearchType, boolean>>>({});
	let pageSize = $state(20);

	// Selecting a type hands that section over to the server: it returns matches
	// ordered across ALL of them, and "show more" pages through. `typeRows` is
	// null while showing the merged list.
	let typeRows = $state<SearchHit[] | null>(null);
	let typeLoading = $state(false);
	let typeSeq = 0;


	type ResultRow = Row & { type: SearchHit['type'] };
	const rows = $derived<ResultRow[]>(hits.map((h) => ({ ...toRow(h), type: h.type })));

	// Sort is the SERVER's job, and only offered once a type is selected. It used
	// to reorder the fetched rows in the browser, which meant "newest" showed the
	// newest of the thirty most relevant — a different question than the one the
	// control asks. Ordering the full match set is the only way it can be true,
	// and that needs the per-type endpoint.
	let sortMode = $state<SearchSort>('relevance');
	const SORTS: SearchSort[] = ['relevance', 'title', 'newest'];

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
	// groups actually present, labelled with the REAL total rather than how many
	// rows the merged list happened to carry. Reset to "all" on each new query.
	let typeFilter = $state('all');

	/** Rows for the selected type, from the server once its page has landed. */
	const typeGroupRows = $derived<ResultRow[]>(
		typeRows ? typeRows.map((h) => ({ ...toRow(h), type: h.type })) : []
	);

	const shownGroups = $derived.by(() => {
		if (typeFilter === 'all') return groups;
		const g = GROUP_ORDER.find((x) => x.type === typeFilter);
		if (!g) return groups;
		// Fall back to the merged subset until the type's own page arrives, so
		// selecting a chip never blanks the list mid-flight.
		const merged = groups.find((x) => x.type === typeFilter)?.rows ?? [];
		return [{ type: g.type, labelKey: g.labelKey, rows: typeRows ? typeGroupRows : merged }];
	});
	const shownCount = $derived(shownGroups.reduce((n, g) => n + g.rows.length, 0));

	/** Whether there is more than one kind to choose between — see the rail. */
	const hasFacets = $derived(groups.length > 1);
	/** Sorting is only meaningful once one type owns the list, and only above one row. */
	const showsSort = $derived(typeFilter !== 'all' && shownCount > 1);

	// The rail's geometry, in one place each, because it is a set: the grid, the
	// column that sits in it, and the input's matching indent all have to agree
	// or the layout comes apart in a way no single class reveals.
	const RAIL_GRID = 'lg:grid lg:grid-cols-[12rem_1fr] lg:items-start lg:gap-8';
	// `lg:top-[var(--pinned-offset,6rem)]` rather than a fixed `lg:top-24`: the
	// search box above is itself pinned under the sticky app nav, and its height
	// changes with the locale and the viewport, so a constant put the rail's
	// first chips underneath it.
	const RAIL_COL =
		'mb-5 flex flex-wrap items-center gap-2 lg:sticky lg:top-[var(--pinned-offset,6rem)] lg:mb-0 lg:flex-col lg:items-stretch lg:self-start';

	/** How many matches of `type` exist — the server's count, else what we hold. */
	function totalFor(type: SearchType, loaded: number): number {
		return totals[type] ?? loaded;
	}
	/** True when the count stopped at the server's ceiling ("200+"). */
	function isCapped(type: SearchType): boolean {
		return totalsCapped[type] === true;
	}
	/**
	 * Every match across every type. The mixed list is capped per type, so this is
	 * usually far larger than what is on screen — and saying "30 results" when it
	 * is 251 was the whole problem.
	 */
	const grandTotal = $derived(
		groups.reduce((n, g) => n + totalFor(g.type, g.rows.length), 0)
	);
	const anyCapped = $derived(groups.some((g) => isCapped(g.type)));

	/** Matches of the selected type not yet loaded. */
	const remaining = $derived(
		typeFilter === 'all' || !typeRows
			? 0
			: Math.max(0, (totals[typeFilter as SearchType] ?? 0) - typeRows.length)
	);

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
		cover: string;
		color: string;
		chapters: { key: string; order: number; title: string; snippet: string }[];
	};
	const passageBooks = $derived.by<PassageBook[]>(() => {
		// The selected type's own page when there is one, else the merged list —
		// otherwise "show more" would load passages the map never rendered.
		const source = typeFilter === 'chapter' && typeRows ? typeRows : hits;
		const by = new Map<string, PassageBook>();
		for (const h of source) {
			if (h.type !== 'chapter') continue;
			const c = h as ChapterHit;
			let g = by.get(c.book_slug);
			if (!g) {
				g = {
					slug: c.book_slug,
					title: c.book_title,
					author: c.author_name,
					date: c.date,
					cover: c.cover_url,
					color: c.cover_color,
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
		// Server order throughout: books in first-match order, chapters in book order.
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
		const labels = new Map<string, string>();
		// Which type each key is. Built here rather than parsed off the key
		// because this is the one place that already knows, and it doubles as the
		// reading order the click log records a position against.
		const types = new Map<string, SearchType>();
		for (const g of shownGroups) {
			if (g.type === 'chapter') {
				for (const pb of passageBooks) {
					const shown = expandedBooks.has(pb.slug)
						? pb.chapters
						: pb.chapters.slice(0, PASSAGE_PREVIEW);
					for (const ch of shown) {
						keys.push(ch.key);
						map.set(ch.key, `/books/${pb.slug}/${ch.order}`);
						labels.set(ch.key, `${ch.title} — ${pb.title}`);
						types.set(ch.key, 'chapter');
					}
				}
			} else {
				for (const row of g.rows) {
					keys.push(row.key);
					map.set(row.key, row.href);
					labels.set(row.key, row.meta ? `${row.title} — ${row.meta}` : row.title);
					types.set(row.key, g.type as SearchType);
				}
			}
		}
		return { keys, map, labels, types };
	});

	/**
	 * Tell the server a result was opened — anonymously, and never in the way.
	 *
	 * This is the only signal that separates "the search found forty things" from
	 * "the search found the thing"; without it a query answered by near-misses
	 * looks like a success in every report. Fire-and-forget on purpose: it must
	 * not delay the navigation the reader just asked for, and if it fails,
	 * nothing about their click changes.
	 *
	 * **Not recorded inside a scope**, for the same reason a scoped search isn't
	 * logged as a query. The report joins the two logs on query text, so a scoped
	 * click would land against a denominator its own search never entered — one
	 * reader opening a chapter from "search inside this book" would delete a real
	 * library-wide gap from the unopened list. Same population in both logs, or
	 * the join lies.
	 */
	function recordClick(key: string) {
		if (scope) return;
		const type = nav.types.get(key);
		const position = nav.keys.indexOf(key) + 1;
		const query = ran || q.trim();
		if (!type || position < 1 || query.length < 2) return;
		void recordSearchClick(query, type, position, getLang()).catch(() => {});
	}
	const activeKey = $derived(
		activeIndex >= 0 && activeIndex < nav.keys.length ? nav.keys[activeIndex] : ''
	);

	// Keep the highlighted result in view as it moves.
	$effect(() => {
		if (activeKey) document.getElementById(`res-${activeKey}`)?.scrollIntoView({ block: 'nearest' });
	});

	/**
	 * What ↑/↓ just landed on, for screen readers.
	 *
	 * The highlight was purely visual: a keyboard user who can't see it got no
	 * signal at all that anything had moved. Announcing it politely is the honest
	 * fix here — the alternative, `aria-activedescendant`, needs the results to be
	 * a listbox, and they are a document with headings, nested lists and buttons,
	 * none of which is legal inside one.
	 */
	const activeAnnouncement = $derived.by(() => {
		if (activeIndex < 0 || !activeKey) return '';
		const el = nav.map.get(activeKey);
		if (!el) return '';
		const label = nav.labels.get(activeKey) ?? '';
		return `${activeIndex + 1} ${t('search.of')} ${nav.keys.length}: ${label}`;
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
			// Recorded on the keyboard path too — measuring only mouse clicks
			// would read as "keyboard users never find anything".
			if (href) {
				recordClick(key);
				goto(localizeHref(href));
			}
		} else if (e.key === 'Escape') {
			activeIndex = -1;
		}
	}

	function clearResults() {
		hits = [];
		ran = '';
		suggestion = '';
		scriptureAnswer = null;
		totals = {};
		totalsCapped = {};
		typeRows = null;
		searchError = false;
	}

	// --- Instant scripture answer ----------------------------------------------
	// When the query looks like a Bible reference ("John 3:16", "1 Cor 13",
	// "Psalm 23"), fetch the passage and show it above the results — the answer,
	// not just links to sermons about it. The backend is the real judge: a
	// non-reference simply returns nothing and the card stays hidden.
	let scriptureAnswer = $state<ScriptureResult | null>(null);
	/** Verses shown before the card clamps — about four lines at the card's measure. */
	const SCRIPTURE_PREVIEW = 4;
	let scriptureOpen = $state(false);
	const REF_RE = /^\s*(?:[123]\s*|I{1,3}\s+)?[A-Za-z][A-Za-z.]{1,}\s+\d{1,3}(?::\d{1,3}(?:[-–]\d{1,3})?)?\s*$/;

	/**
	 * What on this page engages the passage the card is showing.
	 *
	 * Counted from the hits actually rendered, NOT from `totals`. For a reference
	 * query the two are different populations: the merged list leads with sermons
	 * preached on an overlapping text and chapters that CITE it (matched by verse
	 * id), while `totals` counts a plain text search for the reference string.
	 * They can coincide and generally won't, so a link built on `totals` would
	 * promise a number and then show a different set.
	 */
	const engagedCounts = $derived(
		scriptureAnswer
			? GROUP_ORDER.filter((g) => g.type === 'sermon' || g.type === 'chapter')
					.map((g) => ({
						type: g.type,
						labelKey: g.labelKey,
						count: rows.filter((r) => r.type === g.type).length
					}))
					.filter((e) => e.count > 0)
			: []
	);

	/** Resolve a scope's display name with an empty query — see `applyTerm`. */
	async function nameScope(forScope: string) {
		scopeInfo = null;
		try {
			const res = await search('', getLang(), forScope);
			if (forScope === scope) scopeInfo = res.scope ?? null;
		} catch {
			// A chip that can't name itself is not worth blocking the page for.
		}
	}

	/** Jump to a section — not a facet switch, for the reason above. */
	function jumpTo(type: string) {
		document.getElementById(`group-${type}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}

	async function maybeScripture(term: string, token: number) {
		// A new passage arrives collapsed: expanding Romans 12 must not leave the
		// next query's chapter already unfurled.
		scriptureOpen = false;
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

	/**
	 * Load one type from the server: the whole match set, in the chosen order.
	 * `append` continues from what we have ("show more"); otherwise it replaces
	 * (a chip click, or a sort change).
	 */
	async function loadType(
		type: SearchType,
		{ append = false, term = '' }: { append?: boolean; term?: string } = {}
	) {
		// `term` is explicit for the arriving-from-a-URL path, where the merged
		// search hasn't answered yet so `ran` is still empty.
		const forQuery = term || ran || q.trim();
		const token = ++typeSeq;
		typeLoading = true;
		try {
			const res = await searchPage(forQuery, getLang(), type, {
				offset: append && typeRows ? typeRows.length : 0,
				sort: sortMode,
				scope
			});
			if (token !== typeSeq) return; // superseded
			typeRows = append && typeRows ? [...typeRows, ...res.results] : res.results;
		} catch {
			// Leave what's on screen; the merged rows are still a usable answer.
			if (token === typeSeq && !append) typeRows = null;
		} finally {
			if (token === typeSeq) typeLoading = false;
		}
	}

	/** Select a type (or return to the merged list). */
	function selectType(type: string) {
		typeFilter = type;
		activeIndex = -1;
		typeSeq++; // cancel anything in flight for the previous type
		typeRows = null;
		if (type === 'all') sortMode = 'relevance';
		syncUrl(ran || q.trim(), type, type === 'all' ? 'relevance' : sortMode);
		if (type !== 'all') void loadType(type as SearchType);
	}

	function setSort(next: SearchSort) {
		if (next === sortMode) return;
		sortMode = next;
		syncUrl(ran || q.trim(), typeFilter, next);
		if (typeFilter !== 'all') void loadType(typeFilter as SearchType);
	}

	async function runSearch(term: string) {
		// Responses can land out of order (a cold body-text scan overtaken by a
		// cached one), so only the newest request may write the list — otherwise
		// an older reply repaints stale hits over the term the reader can see.
		const token = ++searchSeq;
		loading = true;
		searchError = false;
		void maybeScripture(term, token); // in parallel; independent of the list
		try {
			const res = await search(term, getLang(), scope);
			if (token !== searchSeq) return;
			hits = res.results;
			ran = res.query;
			suggestion = res.suggestion ?? '';
			totals = res.totals ?? {};
			totalsCapped = res.totals_capped ?? {};
			pageSize = res.page_size ?? pageSize;
			scopeInfo = res.scope ?? null;
		} catch {
			// Never leave the previous query's hits on screen under the new term —
			// that reads as a (wrong) answer. Clear and surface a retry instead.
			if (token !== searchSeq) return;
			hits = [];
			ran = '';
			suggestion = '';
			totals = {};
			totalsCapped = {};
			searchError = true;
		} finally {
			if (token === searchSeq) loading = false;
		}
	}

	/** Re-run the current query after an error (the retry button). */
	function retrySearch() {
		const term = q.trim();
		if (term.length >= 2) runSearch(term);
	}

	/**
	 * Mirror the query into ?q= so a search is linkable, survives a reload, and
	 * comes back intact when the reader returns with Back after opening a result.
	 * replaceState (not push) so typing doesn't bury their history; keepFocus so
	 * the caret stays in the box mid-word.
	 */
	function syncUrl(term: string, type = typeFilter, sort: SearchSort = sortMode) {
		const state = { q: term, type, sort, scope };
		const next = searchStateKey(state);
		if (next === urlState) return;
		urlState = next;
		goto(writeSearchState(new URL($page.url), state), {
			replaceState: true,
			keepFocus: true,
			noScroll: true
		});
	}

	/**
	 * Show `term` under `type`/`sort`: reset the list state, then search.
	 *
	 * The facet is a parameter rather than always reset, because this is also the
	 * path a shared `/search?q=…&type=chapter` link arrives on — resetting there
	 * would drop the very thing the link was sent to show.
	 */
	function applyTerm(
		term: string,
		type = 'all',
		sort: SearchSort = 'relevance',
		nextScope = ''
	) {
		clearTimeout(timer);
		activeIndex = -1;
		typeFilter = type;
		sortMode = sort;
		scope = nextScope;
		typeRows = null;
		typeSeq++;
		if (term.length < 2) {
			clearResults();
			// Arriving from "search inside this book" lands here with no query
			// yet. The search itself is what usually carries the shelf's name
			// back, so with nothing to search for, ask for the name alone.
			if (nextScope) void nameScope(nextScope);
			else scopeInfo = null;
			return;
		}
		runSearch(term);
		if (type !== 'all') void loadType(type as SearchType, { term });
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
		typeRows = null;
		typeSeq++;
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

	// The URL is the source of truth for which view is showing: this covers the
	// first load of a shared /search?q=…&type=… link and the Back/Forward buttons.
	// The urlState guard is what stops a loop — syncUrl sets it before writing the
	// URL, so the effect our own write triggers falls straight through.
	$effect(() => {
		const state = readSearchState($page.url.searchParams);
		const next = searchStateKey(state);
		if (next === urlState) return;
		urlState = next;
		q = state.q;
		applyTerm(state.q, state.type, state.sort, state.scope);
	});

	/**
	 * Leave the shelf and search the whole library, keeping the query.
	 *
	 * The way out has to be one click and always present: a scope arrived at from
	 * a book or an author page is easy to forget you're in, and "no results" then
	 * reads as "the library doesn't have this" when it only means "not here".
	 */
	function clearScope() {
		const term = ran || q.trim();
		// Same reset every other entry into a view performs — going through
		// applyTerm rather than repeating it is what keeps them from drifting.
		applyTerm(term);
		syncUrl(term, 'all', 'relevance');
	}

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

	/** The search box, so arriving on this page can put the caret in it. */
	let input = $state<HTMLInputElement | null>(null);

	onMount(() => {
		// Focus only on a pointer device with a real keyboard. On a phone,
		// autofocus throws up the on-screen keyboard over the results the reader
		// came to read — and if they arrived from a shared ?q= link, the answer is
		// already on screen and the box is the last thing they want.
		//
		// After a frame, not during mount: SvelteKit moves focus itself once
		// navigation settles, and a focus() call in the same tick is simply undone.
		if (window.matchMedia?.('(pointer: fine)').matches) {
			requestAnimationFrame(() => {
				if (!q.trim() && input && document.activeElement !== input) input.focus();
			});
		}

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

	/**
	 * Forget ONE remembered query.
	 *
	 * "Clear" was all-or-nothing, so a single query you would rather not see
	 * again — searched on a shared phone, or about something private — could only
	 * be removed by wiping the whole list. Local to the device: recent searches
	 * are localStorage and never leave it.
	 */
	function forgetRecent(term: string) {
		recent = recent.filter((r) => r !== term);
		writeJSON(RECENT_KEY, recent);
	}
</script>

<!-- A clickable query chip — shared by the "recent" and "popular" rows, which
     re-run the search via applySuggestion. Recent chips also carry a ✕; popular
     ones don't, since there is nothing personal to remove. The ✕ is a sibling
     button rather than nested (a button inside a button is invalid), with the
     two drawn as one chip. -->
{#snippet queryChip(term: string, onForget?: (t: string) => void)}
	<span
		class="inline-flex items-center overflow-hidden rounded-full border border-border text-small text-text focus-within:border-accent hover:border-accent"
	>
		<button
			type="button"
			class="px-3 py-1 hover:text-accent"
			onclick={() => applySuggestion(term)}
		>
			{term}
		</button>
		{#if onForget}
			<button
				type="button"
				class="self-stretch pe-2.5 ps-1 text-muted hover:text-accent"
				aria-label="{t('search.forget')}: {term}"
				title={t('search.forget')}
				onclick={() => onForget(term)}
			>
				✕
			</button>
		{/if}
	</span>
{/snippet}

<!-- A cover or a portrait: the visual anchor that makes a list of titles
     scannable. The box is reserved and colour-filled whether or not an image
     arrives, so the list never reflows under the reader's cursor — and rows
     with neither (topics, plans) draw nothing rather than a placeholder. -->
{#snippet thumb(row: {
	image: string;
	color: string;
	round: boolean;
	small?: boolean;
	focus?: string;
})}
	{#if row.image}
		{@const boxStyle = [
			row.color ? `background-color:${row.color}` : '',
			row.focus ? `object-position:${row.focus}` : ''
		].filter(Boolean).join(';')}
		<img
			src={row.image}
			alt=""
			loading="lazy"
			decoding="async"
			class="flex-none bg-surface-2 object-cover {row.round
				? 'h-11 w-11 rounded-full'
				: row.small
					? 'h-8 w-6 rounded-sm'
					: 'h-16 w-12 rounded-sm'}"
			style={boxStyle || undefined}
		/>
	{/if}
{/snippet}

<!-- Somewhere to go: what this reader searched before, what other readers search,
     and the shelves. Rendered both on a blank page and after a query that found
     nothing — the second is where it matters more. `showRecent` is false in the
     no-results case, where re-running an earlier query is a stranger offer than
     browsing. -->
{#snippet waysIn(showRecent: boolean)}
	{#if showRecent && recent.length}
		<section class="mb-8">
			<div class="mb-2 flex items-center justify-between">
				<h2 class="section-label">
					{t('search.recent')}
				</h2>
				<button type="button" class="text-small text-accent hover:underline" onclick={clearRecent}>
					{t('search.clearRecent')}
				</button>
			</div>
			<div class="flex flex-wrap gap-2">
				{#each recent as term (term)}{@render queryChip(term, forgetRecent)}{/each}
			</div>
		</section>
	{/if}
	{#if popular.length}
		<section class="mb-8">
			<h2 class="section-label">
				{t('search.popular')}
			</h2>
			<div class="flex flex-wrap gap-2">
				{#each popular as term (term)}{@render queryChip(term)}{/each}
			</div>
		</section>
	{/if}
	{#if topics.length}
		<section>
			<h2 class="section-label">
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
	{#if showRecent && !recent.length && !topics.length && !popular.length}
		<p class="text-small text-muted">{t('search.prompt')}</p>
	{/if}
{/snippet}

<Seo
	title="{t('search.title')} — Ochorus"
	description={t('search.metaDescription')}
	canonical="{SITE_URL}{localizeHref('/search')}"
	hreflang={hreflangAll('/search')}
/>

<!-- Above lg the page uses the width it has: the facet chips leave the top bar
     and become a rail, so results get the full column and the filters stop
     wrapping onto three lines. Below lg nothing changes — the single column is
     right on a phone, and this page is read on phones. -->
<!-- `--pinned-offset`: the sticky app nav plus this page's own pinned search
     box — the first pixel below everything that floats. The facet rail pins to
     it and the per-type anchors scroll to it. -->
<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {searchBarH}px)">
	<PageHeader title={t('search.title')} tagline={t('search.tagline')} />

	<!-- Sticky: a long result list used to scroll the query out of sight, so
	     refining meant scrolling back up to find the box. The bleed padding and
	     background keep results from showing through as they pass under it. -->
	<!-- The box lines up with the results, not with the page. It used to span the
	     full width while the results began 12rem in behind the rail, so the eye
	     had two left edges to track down a single column of content. -->
	<div
		bind:clientHeight={searchBarH}
		class="sticky z-20 -mx-5 bg-bg px-5 pb-3 pt-2" style="top: var(--appnav-h, 0px)"
		class:lg:ps-[15.25rem]={hasFacets}
		role="search"
	>
		<input
			bind:this={input}
			bind:value={q}
			oninput={onInput}
			onkeydown={onKeydown}
			type="search"
			autocomplete="off"
			placeholder={t('search.placeholder')}
			aria-label={t('search.title')}
			aria-describedby="search-help"
			class="field w-full lg:max-w-3xl"
		/>
	</div>

	<!-- The shelf being searched inside, and the one-click way out of it.
	     Directly under the input on purpose: a scope you can't see is a scope
	     that makes "no results" read as "the library doesn't have this" when it
	     only means "not in here". -->
	{#if scope}
		<div class="mt-2 flex flex-wrap items-center gap-2">
			{#if scopeInfo}
				<span
					class="inline-flex items-center gap-1.5 rounded-full border border-accent bg-accent-soft px-3 py-1 text-small text-text"
				>
					<span class="text-muted">{t('search.scopeIn')}</span>
					<span class="font-semibold">{scopeInfo.label}</span>
				</span>
			{:else}
				<span class="text-small text-muted">{t('search.scopeMissing')}</span>
			{/if}
			<button
				type="button"
				class="text-small font-semibold text-accent hover:underline"
				onclick={clearScope}
			>
				{t('search.scopeClear')}
			</button>
		</div>
	{/if}

	<!-- Two live regions, deliberately separate. The first is the running result
	     count; the second is what ↑/↓ landed on. Merged into one, each arrow key
	     would re-announce the count as well. -->
	<p id="search-help" class="sr-only" aria-live="polite">
		{ran ? `${shownCount} ${t('search.resultsMany')}` : ''}
	</p>
	<p class="sr-only" aria-live="polite">{activeAnnouncement}</p>

	{#if scriptureAnswer}
		<!-- Instant scripture answer: the passage text for a reference query. -->
		{@const verses = scriptureAnswer.verses}
		{@const clamped = !scriptureOpen && verses.length > SCRIPTURE_PREVIEW}
		<!-- The card is sized to its text. Left at full width it drew a tinted
		     panel two-thirds empty, because the verses inside are capped to a
		     readable measure and the panel was not. -->
		<div class="answer-measure mt-6 rounded-card border-s-4 border-accent bg-accent-soft p-4">
			<p class="eyebrow text-accent">
				{t('reader.scripture')}
			</p>
			<p class="scripture-answer-ref">{scriptureAnswer.reference}</p>
			<!-- Clamped by LENGTH, not always. "John 3:16" is answered in place, which
			     is the whole point of the card; a whole chapter printed in full pushed
			     every search result below the fold — the reader asked a question and
			     got a wall instead of an answer plus their results. -->
			<p class="scripture-answer-body mt-2">
				{#each clamped ? verses.slice(0, SCRIPTURE_PREVIEW) : verses as v (v.number)}<sup
						class="scripture-answer-num">{v.number}</sup
					>{v.text}{' '}{/each}{#if clamped}<span class="text-muted">…</span>{/if}
			</p>
			{#if verses.length > SCRIPTURE_PREVIEW}
				<button
					type="button"
					class="mt-1.5 text-small font-semibold text-accent hover:underline"
					onclick={() => (scriptureOpen = !scriptureOpen)}
					aria-expanded={scriptureOpen}
				>
					<!-- One message with a placeholder, not three fragments glued in
					     English word order: "Show all 21 verses" concatenated is
					     ungrammatical in Arabic, where the numeral has to bind to the
					     noun. Same %placeholder% convention as author.metaFallback. -->
					{#if scriptureOpen}{t('search.showLess')}{:else}{t(
							'search.showAllVerses'
						).replace('%count%', String(verses.length))}{/if}
				</button>
			{/if}
			<p class="eyebrow mt-2 text-muted">
				{scriptureAnswer.version}
			</p>

			<!-- The card used to state the passage and stop. What engages this text is
			     already on the page below — the backend matches sermons preached on an
			     overlapping reference and chapters that cite it — so these jump to it
			     rather than fetching anything new. (There is no Bible reader to link
			     "read the chapter" to; if one is ever added, it belongs here.) -->
			{#if engagedCounts.length}
				<div class="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-accent/20 pt-2.5">
					{#each engagedCounts as e (e.type)}
						<button
							type="button"
							class="text-small font-semibold text-accent hover:underline"
							onclick={() => jumpTo(e.type)}
						>
							{e.count}
							{t(e.labelKey)} ↓
						</button>
					{/each}
				</div>
			{/if}
		</div>
	{/if}

	<div class="mt-6" id="search-results" aria-busy={loading}>
		{#if loading}
			<div class="space-y-6" aria-hidden="true">
				{#each Array(4) as _, i (i)}
					<div class="animate-pulse space-y-2">
						<div class="h-3 w-1/4 rounded-sm bg-surface-2"></div>
						<div class="h-4 w-2/3 rounded-sm bg-surface-2"></div>
						<div class="h-3 w-full rounded-sm bg-surface-2"></div>
					</div>
				{/each}
			</div>
		{:else if searchError}
			<div class="rounded-card border border-border bg-surface p-8 text-center">
				<p class="text-body text-text">{t('search.loadError')}</p>
				<button type="button" class="btn btn-primary mt-4" onclick={retrySearch}>
					{t('error.tryAgain')}
				</button>
			</div>
		{:else if q.trim().length < 2}
			{@render waysIn(true)}
		{:else if ran && hits.length === 0}
			<!-- Nothing found. The old version stopped at one line and, if the fuzzy
			     matcher had something, a "did you mean" — a dead end for every other
			     query. The same routes out the blank page offers work here, and this
			     is where a reader actually needs them. -->
			<p class="text-body text-text">{t('search.noResults')} “{ran}”.</p>
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
			<div class="mt-8">
				{@render waysIn(false)}
			</div>
		{:else}
			<!-- The rail earns its 12rem only when there are chips to put in it. A
			     query that matched one kind (any scripture reference, for instance)
			     was still paying for the column, which then held nothing but the word
			     "Sort:" beside a wide, empty margin. -->
			<div class={hasFacets ? RAIL_GRID : ''}>
			<!-- Type facet + result count. Everything that positions this — the
			     grid column, the column direction, and CRUCIALLY the stickiness —
			     is one switch. Pinning survived the grid being dropped once, and a
			     sticky *block* is a very different thing from a sticky grid cell:
			     with no column to sit in it spans the full width above the results
			     and they scroll straight through it, unbacked.

			     Rendered only when it holds something. Collapsed and empty it was
			     still an element with a bottom margin — 20px of nothing above the
			     results on every single-type query. -->
			{#if hasFacets || showsSort}
			<div class={hasFacets ? RAIL_COL : 'mb-5 flex flex-wrap items-center gap-2'}>
				{#if hasFacets}
					<div
						class="flex flex-wrap gap-1.5 lg:flex-col"
						role="group"
						aria-label={t('search.filterByType')}
					>
						<button
							type="button"
							class="rounded-full border px-2.5 py-1 text-small"
							class:border-accent={typeFilter === 'all'}
							class:bg-accent={typeFilter === 'all'}
							class:text-accent-contrast={typeFilter === 'all'}
							class:border-border={typeFilter !== 'all'}
							class:text-muted={typeFilter !== 'all'}
							onclick={() => selectType('all')}
							aria-pressed={typeFilter === 'all'}
						>
							{t('search.filterAll')}
						</button>
						{#each groups as g (g.type)}
							<button
								type="button"
								class="rounded-full border px-2.5 py-1 text-small"
								class:border-accent={typeFilter === g.type}
								class:bg-accent={typeFilter === g.type}
								class:text-accent-contrast={typeFilter === g.type}
								class:border-border={typeFilter !== g.type}
								class:text-muted={typeFilter !== g.type}
								onclick={() => selectType(g.type)}
								aria-pressed={typeFilter === g.type}
							>
								{t(g.labelKey)}
								<!-- The real total, not the number of rows we were handed. -->
								<span class="tabular-nums opacity-70"
									>{totalFor(g.type, g.rows.length)}{isCapped(g.type) ? '+' : ''}</span
								>
							</button>
						{/each}
					</div>
				{/if}
				<div class="flex flex-wrap items-center gap-x-3 gap-y-2 sm:ms-auto lg:ms-0 lg:flex-col lg:items-start">
					<!-- Sorting needs the whole match set, which only the per-type
					     endpoint returns — so it appears once a type is chosen. In the
					     mixed list the order is relevance, the only one that means
					     anything across books, people and passages. -->
					{#if showsSort}
						<div class="flex items-center gap-1.5" role="group" aria-label={t('search.sortBy')}>
							<span class="text-small text-muted">{t('search.sortBy')}</span>
							<div class="flex overflow-hidden rounded-full border border-border">
								{#each SORTS as s, i (s)}
									<button
										type="button"
										class="whitespace-nowrap px-2.5 py-1 text-small"
										class:bg-accent={sortMode === s}
										class:text-accent-contrast={sortMode === s}
										class:text-muted={sortMode !== s}
										class:border-s={i > 0}
										class:border-border={i > 0}
										onclick={() => setSort(s)}
										aria-pressed={sortMode === s}
									>
										{t(`search.sort_${s}`)}
									</button>
								{/each}
							</div>
						</div>
					{/if}
				<!-- The running total belongs in the rail. With no rail there is
				     nothing to anchor it to, and it stacked above the section label as
				     a second lonely line ("15 results" over "PASSAGES") — so the
				     section heading carries its own count there instead.

				     Removed rather than sr-only'd: the accessible running count is
				     already its own live region up by the input, so hiding this one
				     would leave two polite regions announcing the same number on every
				     keystroke. Its aria-live goes with it for the same reason. -->
				{#if hasFacets}
					<p class="text-small text-muted">
						{#if typeFilter !== 'all' && remaining > 0}
							{shownCount}
							{t('search.of')}
							{totalFor(typeFilter as SearchType, shownCount)}{isCapped(
								typeFilter as SearchType
							)
								? '+'
								: ''}
							{t('search.resultsMany')}
						{:else if typeFilter === 'all' && grandTotal > shownCount}
							{shownCount}
							{t('search.of')}
							{grandTotal}{anyCapped ? '+' : ''}
							{t('search.resultsMany')}
						{:else}
							{shownCount}
							{shownCount === 1 ? t('search.resultsOne') : t('search.resultsMany')}
						{/if}
						</p>
					{/if}
				</div>
			</div>
			{/if}
			<div class="space-y-8 lg:min-w-0">
				{#each shownGroups as g (g.type)}
					{@const total = totalFor(g.type, g.rows.length)}
					{@const more = total - g.rows.length}
					<section
						id="group-{g.type}"
						style="scroll-margin-top: calc(var(--pinned-offset, 5rem) + 0.5rem)"
					>
						<h2
							class="mb-2 flex items-baseline gap-2 section-label"
						>
							{t(g.labelKey)}
							<!-- The per-group number distinguishes one section from the next.
							     With a single section AND the rail's running total already on
							     screen there is nothing to distinguish and it repeats that
							     total verbatim — which is what put "PASSAGES 20 OF 127" three
							     inches from "20 of 127 results". With no rail it is the only
							     count there is, so it stays.

							     Dropped, not hidden: sr-only would leave it in the heading's
							     accessible name, so a screen reader would still hear the
							     duplicate this exists to remove. -->
							{#if !(hasFacets && shownGroups.length === 1)}
								<span class="text-small font-normal tabular-nums text-muted/70">
									{#if more > 0}{g.rows.length} {t('search.of')} {total}{isCapped(g.type)
											? '+'
											: ''}{:else}{total}{/if}
								</span>
							{/if}
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
											class="flex items-center gap-2.5 text-small font-semibold text-text hover:text-accent hover:no-underline"
										>
											{@render thumb({
												image: pb.cover,
												color: pb.color,
												round: false,
												small: true
											})}
											<span>
												{pb.title} <span class="font-normal text-muted">· {pb.author}</span>
											</span>
										</a>
										<ul class="mt-1 divide-y divide-border border-s border-border ps-3">
											{#each shown as ch (ch.key)}
												<li class="py-2.5">
													<a
														href={localizeHref(
														`/books/${pb.slug}/${ch.order}?q=${encodeURIComponent(ran || q.trim())}`
													)}
														id="res-{ch.key}"
														class="-mx-2 block rounded-sm px-2 hover:no-underline"
														class:bg-surface-2={ch.key === activeKey}
														onclick={() => recordClick(ch.key)}
													>
														<div class="text-small font-medium text-text">{ch.title}</div>
														{#if ch.snippet}
															<p class="snippet-measure mt-0.5 text-small text-muted">
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
												class="mt-1.5 ps-3 text-small font-semibold text-accent"
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
											class="-mx-2 flex gap-3 rounded-sm px-2 hover:no-underline"
											class:bg-surface-2={row.key === activeKey}
											onclick={() => recordClick(row.key)}
										>
											{@render thumb(row)}
											<div class="min-w-0 flex-1">
												{#if row.meta}
													<div class="text-small text-muted">{row.meta}</div>
												{/if}
												<div class="text-body font-semibold text-text">{row.title}</div>
												{#if row.snippet}
													<p class="snippet-measure mt-1 text-small text-muted">
														<!-- eslint-disable-next-line svelte/no-at-html-tags -->
														{@html mark(row.snippet)}
													</p>
												{/if}
											</div>
										</a>
									</li>
								{/each}
							</ul>
						{/if}

						<!-- The way past the cap. In the mixed list this hands the section
						     over to the server (which can order and page it); once a type is
						     selected it appends the next page. Before this the reader had no
						     signal that anything had been left out at all. -->
						{#if more > 0}
							<div class="mt-3">
								{#if typeFilter === 'all'}
									<button
										type="button"
										class="text-small font-semibold text-accent hover:underline"
										onclick={() => selectType(g.type)}
									>
										{t('search.showAll')}
										{total}{isCapped(g.type) ? '+' : ''} →
									</button>
								{:else}
									<button
										type="button"
										class="text-small font-semibold text-accent hover:underline disabled:opacity-50"
										disabled={typeLoading}
										onclick={() => loadType(g.type, { append: true })}
									>
										{typeLoading ? '…' : t('search.showMore')}
									</button>
								{/if}
							</div>
						{/if}
					</section>
				{/each}
			</div>
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
	/* One measure per context, following the reader's Width control the way the
	   page shells do — a hardcoded ch cap would have been the one thing on the
	   page that ignored "Wide". */
	.snippet-measure {
		max-width: calc(68ch * var(--page-scale, 1));
	}
	.answer-measure {
		max-width: calc(72ch * var(--page-scale, 1));
	}
	.scripture-answer-num {
		font-size: 0.62em;
		font-weight: 600;
		color: var(--muted);
		margin-inline-end: 0.15em;
		vertical-align: super;
		font-style: normal;
	}
</style>
