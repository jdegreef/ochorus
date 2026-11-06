<script lang="ts">
	import { assetSrcset, assetUrl } from '$lib/assetUrl';
	import ForPromo from '$lib/components/ForPromo.svelte';
	import { searchFor } from '$lib/forPromos';
	import Arrow from '$lib/components/Arrow.svelte';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import Icon from '$lib/components/Icon.svelte';
	import { coverSrcset } from '$lib/coverArt';
	import BookCover from '$lib/components/BookCover.svelte';
	import SermonMonogram from '$lib/components/SermonMonogram.svelte';
	import { onMount } from 'svelte';
	import {
		search,
		searchPage,
		listTopics,
		getPopularSearches,
		recordSearchClick,
		type CoverFace,
		type SearchHit,
		type SearchScope,
		type SearchSort,
		type SearchType,
		type TopicSummary
	} from '$lib/library-public';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { apiFetch } from '$lib/api';
	import { readJSON, writeJSON } from '$lib/persisted';
	import { readSearchState, searchStateKey, writeSearchState } from '$lib/searchState';
	import {
		GROUP_ORDER,
		grandTotal as grandTotalOf,
		groupRows,
		leadWithPinned,
		navList,
		toRow,
		topResult,
		totalFor as totalForOf,
		type ResultGroup,
		type ResultRow
	} from '$lib/searchResults';
	import type { ScriptureResult } from '$lib/scripture.svelte';
	import { snippetParts } from '$lib/highlight';
	import { tabStrip } from '$lib/actions/tabStrip';
	import { jumpToSection } from '$lib/scrollSpy.svelte';
	import { localizeHref } from '$lib/href';
	import { SITE_URL } from '$lib/config';
	import { hreflangAll } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import { page } from '$app/stores';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';

	const t = i18n.t;

	// "Search inside this author / topic / book", carried as `kind:slug`. The
	// label comes back with the results (`scopeInfo`) so the chip can name the
	// shelf without a second request; null means the server found no such shelf
	// in this language, and the page says so instead of showing an empty list.
	let scope = $state('');
	let scopeInfo = $state<SearchScope | null>(null);

	let q = $state('');
	let hits = $state<SearchHit[]>([]);
	let loading = $state(false);
	/** Measured height of the pinned search box and its tabs — the group
	    anchors below clear it via `--pinned-offset`. */
	let searchBarH = $state(0);
	let searchError = $state(false);
	let ran = $state('');
	const forGroup = $derived(ran ? searchFor(ran) : null);
	let suggestion = $state('');
	// The word actually searched when an admin's synonym replaced the reader's.
	let searchedFor = $state('');
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


	// The type chip's wording and the query ride in, so the shaping itself stays
	// a pure function of the hit — see $lib/searchResults.
	// Spelled out rather than derived from the type name: a key built by string
	// surgery type-checks against nothing and would fail silently the first time
	// a type's chip doesn't follow the pattern.
	const TYPE_LABELS: Record<SearchHit['type'], () => string> = {
		author: () => t('search.typeAuthor'),
		book: () => t('search.typeBook'),
		topic: () => t('search.typeTopic'),
		plan: () => t('search.typePlan'),
		article: () => t('search.typeArticle'),
		scripture: () => t('search.typeScripture'),
		sermon: () => t('search.typeSermon'),
		chapter: () => t('search.typeChapter')
	};
	const rowCtx = $derived({
		label: (type: SearchHit['type']) => TYPE_LABELS[type](),
		query: ran || q.trim()
	});
	const rows = $derived<ResultRow[]>(
		hits.map((h) => ({ ...toRow(h, rowCtx), type: h.type, pinned: h.pinned }))
	);
	const groups = $derived<ResultGroup[]>(leadWithPinned(groupRows(rows)));

	// Sort is the SERVER's job, and only offered once a type is selected. It used
	// to reorder the fetched rows in the browser, which meant "newest" showed the
	// newest of the thirty most relevant — a different question than the one the
	// control asks. Ordering the full match set is the only way it can be true,
	// and that needs the per-type endpoint.
	let sortMode = $state<SearchSort>('relevance');
	const SORTS: SearchSort[] = ['relevance', 'title', 'newest'];

	// Type facet: narrow the result set to one kind. Tabs are built from the
	// groups actually present, labelled with the REAL total rather than how many
	// rows the merged list happened to carry. Reset to "all" on each new query.
	let typeFilter = $state('all');

	/** Rows for the selected type, from the server once its page has landed. */
	const typeGroupRows = $derived<ResultRow[]>(
		typeRows ? typeRows.map((h) => ({ ...toRow(h, rowCtx), type: h.type })) : []
	);

	/**
	 * The one book or writer the query names exactly, drawn as a larger card
	 * above the list (design review #25) — and taken out of its section below, so
	 * it is not listed twice. Only in the mixed list: under a tab the reader has
	 * already said which kind they want, and the server's order is the answer.
	 */
	const top = $derived(typeFilter === 'all' ? topResult(rows, rowCtx.query) : null);

	const shownGroups = $derived.by(() => {
		if (typeFilter === 'all') {
			if (!top) return groups;
			// The section still counts it as loaded — see `loaded` in the markup.
			return groups
				.map((g) => ({ ...g, rows: g.rows.filter((r) => r.key !== top.key) }))
				.filter((g) => g.rows.length);
		}
		const g = GROUP_ORDER.find((x) => x.type === typeFilter);
		if (!g) return groups;
		// Fall back to the merged subset until the type's own page arrives, so
		// selecting a chip never blanks the list mid-flight.
		const merged = groups.find((x) => x.type === typeFilter)?.rows ?? [];
		return [{ type: g.type, labelKey: g.labelKey, rows: typeRows ? typeGroupRows : merged }];
	});
	const shownCount = $derived(
		shownGroups.reduce((n, g) => n + g.rows.length, 0) + (top ? 1 : 0)
	);

	/** Whether there is more than one kind to choose between — see the tabs. */
	const hasFacets = $derived(groups.length > 1);
	/** Sorting is only meaningful once one type owns the list, and only above one row. */
	const showsSort = $derived(typeFilter !== 'all' && shownCount > 1);

	/** How many matches of `type` exist — the server's count, else what we hold. */
	function totalFor(type: SearchType, loaded: number): number {
		return totalForOf(totals, type, loaded);
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
	const grandTotal = $derived(grandTotalOf(groups, totals));
	const anyCapped = $derived(groups.some((g) => isCapped(g.type)));

	/** The kind tabs: All, then each kind present, each with its real total. */
	const tabs = $derived([
		{ type: 'all', label: t('search.filterAll'), count: grandTotal, capped: anyCapped },
		...groups.map((g) => ({
			type: g.type as string,
			label: t(g.labelKey),
			count: totalFor(g.type, g.rows.length),
			capped: isCapped(g.type)
		}))
	]);

	/** Matches of the selected type not yet loaded. */
	const remaining = $derived(
		typeFilter === 'all' || !typeRows
			? 0
			: Math.max(0, (totals[typeFilter as SearchType] ?? 0) - typeRows.length)
	);

	// --- Keyboard navigation ---------------------------------------------------
	// Flatten the *visible* results (the top card, then every row in display
	// order) so ↑/↓ walk them and Enter opens the active one.
	let activeIndex = $state(-1);
	const nav = $derived(
		navList(top ? [{ type: top.type, labelKey: '', rows: [top] }, ...shownGroups] : shownGroups)
	);
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
		searchedFor = '';
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
		jumpToSection(`group-${type}`);
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
			searchedFor = res.searched_for ?? '';
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
			searchedFor = '';
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
				<Icon name="close" size={14} />
			</button>
		{/if}
	</span>
{/snippet}

<!-- A cover, a portrait or a sermon's monogram: the visual anchor that makes
     a list of titles scannable. The box is reserved and colour-filled whether or not an image
     arrives, so the list never reflows under the reader's cursor — and rows
     with neither (topics, plans) draw nothing rather than a placeholder.
     `large` is the top result's size; the rows below are short on purpose. -->
{#snippet thumb(
	row: {
		image: string;
		color: string;
		face?: CoverFace;
		round: boolean;
		focus?: string;
		monogram?: { scriptureRef: string; title: string };
	},
	large = false
)}
	{#if row.monogram}
		<!-- A sermon wears its passage monogram, the mark it has on every shelf,
		     at the portrait's size. Decorative: the row names the sermon. -->
		<SermonMonogram
			class={large ? 'search-monogram-lg' : 'search-monogram'}
			scriptureRef={row.monogram.scriptureRef}
			title={row.monogram.title}
			hue={row.color}
		/>
	{:else if row.face}
		<!-- A book's cover DRAWN, as everywhere else it appears: a plate is a
		     wordless ground, so the bare image read as a blank block. -->
		<!-- aria-hidden: the row's own title already names the book, and the
		     cover's "Cover of …" label would read it twice (the old thumb was
		     alt=""). -->
		<div class="flex-none {large ? 'w-16' : 'w-9'}" aria-hidden="true">
			<BookCover book={row.face} rounded="rounded-sm" />
		</div>
	{:else if row.image}
		{@const source = { src: assetUrl(row.image), srcset: assetSrcset(coverSrcset(row.image)) || undefined }}
		{@const boxStyle = [
			row.color ? `background-color:${row.color}` : '',
			row.focus ? `object-position:${row.focus}` : ''
		].filter(Boolean).join(';')}
		<img
			src={source.src}
			srcset={source.srcset}
			use:hydrateSrc={source}
			alt=""
			loading="lazy"
			decoding="async"
			class="flex-none bg-surface-2 object-cover {row.round
				? large
					? 'h-16 w-16 rounded-full'
					: 'h-9 w-9 rounded-full'
				: large
					? 'h-24 w-16 rounded-sm'
					: 'h-12 w-9 rounded-sm'}"
			style={boxStyle || undefined}
		/>
	{/if}
{/snippet}

<!-- A snippet with the words that matched marked. Rendered as text runs, never
     an HTML string: the server's markers say what matched (`snippetParts`), and with
     none it marks the query's own words — either way nothing in the snippet
     can become markup. -->
{#snippet marked(text: string)}
	{#each snippetParts(text, rowCtx.query) as part, i (i)}{#if part.mark}<mark>{part.text}</mark
			>{:else}{part.text}{/if}{/each}
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
						class="tag"
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

<svelte:head>
	<!-- Crawlable but never indexed: the empty state is a doorway, not a page,
	     and results (`?q=`) are disallowed in robots.txt. `follow`, so its ways
	     in still pass links. NOT a robots.txt Disallow of /search itself — that
	     hides the directive and leaves the URL "Indexed, though blocked". -->
	<meta name="robots" content="noindex,follow" />
</svelte:head>

<!-- `--pinned-offset`: the sticky app nav plus this page's own pinned search
     box (and its tabs) — the first pixel below everything that floats. The
     per-type anchors scroll to it. -->
<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {searchBarH}px)">
	<!-- The field is the header (design review #25): the h1 stays for screen
	     readers and the outline, but the title, divider and tagline no longer
	     push the one control this page exists for down the screen. -->
	<PageHeader title={t('search.title')} srOnly />

	<!-- Sticky: a long result list used to scroll the query out of sight, so
	     refining meant scrolling back up to find the box. The bleed padding and
	     background keep results from showing through as they pass under it.
	     The kind tabs ride in it, so switching kind never means scrolling up. -->
	<div
		bind:clientHeight={searchBarH}
		class="sticky z-(--z-pinned) -mx-5 -mt-4 bg-bg px-5 pb-2 pt-2" style="top: var(--appnav-h, 0px)"
	>
		<div role="search">
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
				class="field search-field w-full lg:max-w-3xl"
			/>
		</div>

		<!-- The type facet, as tabs by kind with the REAL total on each (not the
		     rows the merged list happened to carry). Shown only when there is more
		     than one kind to choose between, and only over a live answer — over the
		     skeleton or an error its counts would belong to the previous query. -->
		{#if hasFacets && !loading && !searchError && q.trim().length >= 2}
			<div class="search-tabs mt-3 lg:max-w-3xl" role="group" aria-label={t('search.filterByType')}>
				<div class="tab-strip flex gap-1" use:tabStrip={undefined}>
					{#each tabs as tab (tab.type)}
						<button
							type="button"
							class="subnav-link subnav-link-tight"
							class:is-active={typeFilter === tab.type}
							onclick={() => selectType(tab.type)}
							aria-pressed={typeFilter === tab.type}
						>
							{tab.label}
							<span class="count">{tab.count}{tab.capped ? '+' : ''}</span>
						</button>
					{/each}
				</div>
			</div>
		{/if}
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

	<!-- A search that names a group ("homeschool", "bible study"): their page
	     answers it better than any one book. -->
	{#if forGroup}
		<ForPromo place="search" slugs={[forGroup]} class="mb-4" />
	{/if}

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

	<div class="mt-4" id="search-results" aria-busy={loading}>
		{#if loading}
			<div class="space-y-6" aria-hidden="true">
				{#each Array(4) as _, i (i)}
					<div class="space-y-2">
						<div class="skeleton h-3 w-1/4 rounded-sm"></div>
						<div class="skeleton h-4 w-2/3 rounded-sm"></div>
						<div class="skeleton h-3 w-full rounded-sm"></div>
					</div>
				{/each}
			</div>
		{:else if searchError}
			<!-- One line under the field, not a boxed panel that became the only
			     thing on screen. The query is still in the box above it. -->
			<p class="text-small text-muted" role="alert">
				{t('search.loadError')}
				<button
					type="button"
					class="ms-1 font-semibold text-accent hover:underline"
					onclick={retrySearch}
				>
					{t('error.tryAgain')}
				</button>
			</p>
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
			{#if searchedFor}
				<!-- An admin's synonym ran the search on another word; say which, so
				     the reader isn't left wondering why theirs is in none of the results. -->
				<p class="mb-4 text-small text-muted">
					{t('search.showingFor')} “<span class="font-semibold text-text">{searchedFor}</span>”
				</p>
			{/if}
			<!-- The running count and, once a tab owns the list, the sort. One quiet
			     line under the tabs; rendered only when it holds something. -->
			{#if hasFacets || showsSort}
				<div class="mb-5 flex flex-wrap items-center gap-x-4 gap-y-2 lg:max-w-3xl">
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
					<!-- Sorting needs the whole match set, which only the per-type
					     endpoint returns — so it appears once a type is chosen. In the
					     mixed list the order is relevance, the only one that means
					     anything across books, people and passages. -->
					{#if showsSort}
						<div class="flex items-center gap-1.5 sm:ms-auto" role="group" aria-label={t('search.sortBy')}>
							<div class="seg">
								{#each SORTS as s (s)}
									<button
										type="button"
										class:active={sortMode === s}
										onclick={() => setSort(s)}
										aria-pressed={sortMode === s}
									>
										{t(`search.sort_${s}`)}
									</button>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/if}

			<!-- The top result: the book or writer the query names exactly, larger,
			     with its cover or portrait — most searches for a title end here. -->
			{#if top}
				<a
					href={localizeHref(top.href)}
					id="res-{top.key}"
					class="top-result mb-8 flex items-center gap-4 rounded-card p-4 hover:no-underline lg:max-w-3xl"
					class:is-active={top.key === activeKey}
					onclick={() => recordClick(top.key)}
				>
					{@render thumb(top, true)}
					<div class="min-w-0 flex-1">
						<p class="eyebrow text-muted">
							{top.label}{#if top.pinned}<span class="text-accent"> · {t('search.bestMatch')}</span>{/if}
						</p>
						<p class="top-result-title mt-0.5 text-text">{top.title}</p>
						{#if top.meta}
							<p class="mt-0.5 text-small text-muted">{top.meta}</p>
						{/if}
						{#if top.snippet}
							<p class="snippet-measure mt-1.5 line-clamp-2 text-small text-muted">
								{@render marked(top.snippet)}
							</p>
						{/if}
					</div>
				</a>
			{/if}

			<div class="space-y-8 lg:max-w-3xl">
				{#each shownGroups as g (g.type)}
					{@const loaded = g.rows.length + (top?.type === g.type ? 1 : 0)}
					{@const total = totalFor(g.type, loaded)}
					{@const more = total - loaded}
					<section
						id="group-{g.type}"
						style="scroll-margin-top: calc(var(--pinned-offset, 5rem) + 0.5rem)"
					>
						<GroupHeading name={t(g.labelKey)}>
							{#snippet detail()}
								<!-- The per-group number distinguishes one section from the next.
								     With a single section AND the running total already on
								     screen there is nothing to distinguish and it repeats that
								     total verbatim. With no tabs it is the only count there is,
								     so it stays.

								     Dropped, not hidden: sr-only would leave it in the heading's
								     accessible name, so a screen reader would still hear the
								     duplicate this exists to remove. -->
								{#if !(hasFacets && shownGroups.length === 1)}
									<span class="text-small font-normal count">
										{#if more > 0}{loaded} {t('search.of')} {total}{isCapped(g.type)
												? '+'
												: ''}{:else}{total}{/if}
									</span>
								{/if}
							{/snippet}
						</GroupHeading>
						<ul class="divide-y divide-border">
							{#each g.rows as row (row.key)}
								<li>
									{#if row.location}
										<!-- A passage: where it is, then the words that matched.
										     The snippet is the result — it is why the row is here. -->
										<a
											href={localizeHref(row.href)}
											id="res-{row.key}"
											class="-mx-2 block rounded-sm px-2 py-3 hover:no-underline"
											class:bg-surface-2={row.key === activeKey}
											onclick={() => recordClick(row.key)}
										>
											<div class="truncate text-small font-medium text-text">{row.location}</div>
											{#if row.snippet}
												<p class="snippet-measure mt-0.5 line-clamp-2 text-small text-muted">
													{@render marked(row.snippet)}
												</p>
											{/if}
										</a>
									{:else}
										<!-- A short row: title, and one line of context — the
										     byline when there is one, else the matching words. -->
										<a
											href={localizeHref(row.href)}
											id="res-{row.key}"
											class="-mx-2 flex items-center gap-3 rounded-sm px-2 py-2.5 hover:no-underline"
											class:bg-surface-2={row.key === activeKey}
											onclick={() => recordClick(row.key)}
										>
											{@render thumb(row)}
											<div class="min-w-0 flex-1">
												<div class="truncate text-body font-semibold text-text">
													{row.title}{#if row.pinned}<span
															class="ms-2 inline-block rounded-full bg-accent-soft px-2 py-0.5 align-middle text-micro font-semibold text-accent"
															>{t('search.bestMatch')}</span
														>{/if}
												</div>
												{#if row.meta}
													<div class="truncate text-small text-muted">{row.meta}</div>
												{:else if row.snippet}
													<div class="truncate text-small text-muted">{@render marked(row.snippet)}</div>
												{/if}
											</div>
										</a>
									{/if}
								</li>
							{/each}
						</ul>

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
										{total}{isCapped(g.type) ? '+' : ''} <Arrow />
									</button>
								{:else}
									<!-- Same affordance as the Biographies shelf's Show more: a
									     load-more is a button you press, and a bare accent link
									     read as navigation to somewhere else. -->
									<button
										type="button"
										class="btn btn-ghost btn-sm"
										disabled={typeLoading}
										aria-busy={typeLoading ? 'true' : undefined}
										onclick={() => loadType(g.type, { append: true })}
									>
										<!-- Keep the label; never swap it for "…", which leaves the
										     button announcing as "…, dimmed, button" (STYLE_GUIDE §6).
										     Spinner + aria-busy, the login/reset pattern. -->
										{#if typeLoading}<span class="btn-spinner" aria-hidden="true"></span>{/if}
										{t('search.showMore')}
									</button>
								{/if}
							</div>
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
	/* A sermon's monogram, sized like the round author portrait beside it
	   (h-11 w-11). :global because the chip is a child component's root. */
	:global(.search-monogram) {
		--chip-size: 2.25rem;
	}
	:global(.search-monogram-lg) {
		--chip-size: 4rem;
	}
	/* The field is the header, so it is drawn at a header's size. One class more
	   specific than app.css's `input[type='search'].field` (the magnifier and its
	   pad), so the larger icon and its pad stay in step. */
	input[type='search'].field.search-field {
		font-size: var(--fs-h3);
		padding-block: 0.65rem;
		padding-inline-start: 2.75rem;
		background-position: left 0.9rem center;
		background-size: 1.25rem;
	}
	:global([dir='rtl']) input[type='search'].field.search-field {
		background-position: right 0.9rem center;
	}
	.search-tabs {
		border-bottom: 1px solid var(--border);
	}
	/* The top result: one soft ground, no border (boxless, like the shelves). */
	.top-result {
		background: var(--surface-2);
	}
	.top-result:hover,
	.top-result.is-active {
		background: color-mix(in srgb, var(--accent) 8%, var(--surface-2));
	}
	.top-result-title {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		line-height: 1.25;
	}
</style>
