<script lang="ts">
	import { scrollEdges } from '$lib/actions/scrollEdges';
	import FilterSheet from '$lib/components/FilterSheet.svelte';
	import SheetChoices from '$lib/components/SheetChoices.svelte';
	import { resumeOrderOf } from '$lib/reading-schema';
	import { chapterPath } from '$lib/editionHref';
	import { onMount } from 'svelte';
	import { type BookSummary, type SeriesSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { readJSON, writeJSON } from '$lib/persisted';
	import { allProgress } from '$lib/progress';
	import { page } from '$app/stores';
	import { urlFilters } from '$lib/urlFilters.svelte';
	import BookCard from './BookCard.svelte';
	import BookListRow from './BookListRow.svelte';
	import BookCover from './BookCover.svelte';
	import SeriesCard from './SeriesCard.svelte';
	import PageHeader from './PageHeader.svelte';
	import LibraryTabs from './LibraryTabs.svelte';
	import GroupHeading from './GroupHeading.svelte';
	import EmptyState from './EmptyState.svelte';
	import FilterSummary from './FilterSummary.svelte';
	import FilterBar from './FilterBar.svelte';
	import AuthorJumpStrip from './AuthorJumpStrip.svelte';
	import ViewToggle from './ViewToggle.svelte';
	import ContinueShelf from './ContinueShelf.svelte';
	import ContinueRow from './ContinueRow.svelte';
	import ProgressBar from './ProgressBar.svelte';
	import { queryChip, topicChip, type FilterChip } from '$lib/filterChips';
	import {
		BOOK_LENGTHS,
		BOOK_LENGTH_LABEL,
		BOOK_SORTS,
		BOOK_SORT_LABEL,
		bookLength,
		matchesBookQuery,
		sortBooks,
		type BookLength,
		type BookSort
	} from '$lib/bookSort';
	import { readingMinutes } from '$lib/reading';
	import { pager } from '$lib/paging.svelte';
	import ShowMore from '$lib/components/ShowMore.svelte';
	import { groupBySeries, seriesAmong } from '$lib/series';
	import { browseRows } from '$lib/browseRows';
	import { collapseEditions, editionFamilies } from '$lib/edition';

	let {
		books,
		series = [],
		loadError = false
	}: {
		books: BookSummary[];
		/** This language's book series — the Book Series rail and the count link. */
		series?: SeriesSummary[];
		loadError?: boolean;
	} = $props();
	const t = i18n.t;

	// --- View preferences (persisted per device) -------------------------------
	type View = 'grid' | 'list';
	type Sort = BookSort;
	type Group = 'author' | 'series' | 'all';
	const PREFS_KEY = 'ochorus:books-view2';

	let view = $state<View>('grid');
	let sort = $state<Sort>('shelf');
	// Default to the flat view — the shelf opens as one ungrouped roster of
	// books. Grouping by author stays available via the control, but is no
	// longer the default (reverting B4).
	let group = $state<Group>('all');
	// --- Filters (in the URL) --------------------------------------------------
	// A filtered shelf is a place: it survives a reload, comes back with Back,
	// and can be sent to someone. View preferences above deliberately stay in
	// localStorage — they describe the reader, not the shelf.
	//
	// `shelf` is which view is showing: '' the curated Browse rows the shelf
	// opens on (design review #11), 'all' the full grid with these filters. It
	// rides with them so a "See all" link can land on a pre-filtered grid, and
	// clearing the filters keeps the reader on the grid they were using.
	// `len` is a reading-time bucket ($lib/bookSort); off the list it reads as
	// "any length".
	const filters = urlFilters({
		defaults: { q: '', topic: '', len: '', shelf: '' },
		allowed: { shelf: ['all'], len: BOOK_LENGTHS },
		url: () => $page.url
	});
	const clearFilters = () => filters.reset({ shelf: 'all' });

	function save() {
		writeJSON(PREFS_KEY, { view, sort, group });
	}
	const setView = (v: View) => ((view = v), save());
	const setGroup = (g: Group) => ((group = g), save());
	const setSort = (v: Sort) => ((sort = v), save());

	// --- Continue reading (device-local; hydrated after mount) ------------------
	let continueBooks = $state<{ book: BookSummary; order: number }[]>([]);
	onMount(() => {
		const p = readJSON<{ view?: View; sort?: Sort; group?: Group }>(PREFS_KEY, {});
		if (p.view) view = p.view;
		if (p.sort) sort = p.sort;
		if (p.group) group = p.group;

		const bySlug = new Map(books.map((b) => [b.slug, b]));
		continueBooks = allProgress()
			// Books only — a sermon sharing a slug with a book must not render
			// as a phantom "Chapter 1" tile (or duplicate an each-block key).
			.filter((r) => r.kind === 'book')
			.map((r) => {
				const book = bySlug.get(r.slug);
				return book ? { book, order: resumeOrderOf(r) } : null;
			})
			.filter((x): x is { book: BookSummary; order: number } => x !== null)
			.slice(0, 3);
	});

	// --- Derived --------------------------------------------------------------
	// "By series" is offered only when some book on the shelf is in a named
	// series (never in a language with none, nor behind an API without the
	// field); a stored preference for it then falls back to the flat view.
	const hasSeries = $derived(books.some((b) => b.series));
	const activeGroup = $derived<Group>(group === 'series' && !hasSeries ? 'all' : group);

	// One slot per work (design review #26). A work's full text and its
	// young-reader editions (`<base>-teens` / `<base>-children`, $lib/edition)
	// take ONE card: the full edition's, with a stacked edge and an "N
	// editions" marker (N = its editions on this shelf); its book page is where
	// the reader picks one. The fold runs on whatever the filters left, so a
	// search or filter matching only the teens edition still finds it, as
	// itself. Not under "By series": there each edition sits in its own series
	// (the teens editions are Straight Talk), so every edition shows. Every count
	// on the page counts these slots, the cards a reader can see.
	const family = $derived(editionFamilies(books));
	const fold = <T extends { slug: string }>(list: readonly T[]): readonly T[] =>
		activeGroup === 'series' ? list : collapseEditions(list);
	const editionsOf = (b: BookSummary) => (activeGroup === 'series' ? 1 : (family.get(b.slug) ?? 1));
	/** The works on the shelf — what "N books" counts. */
	const works = $derived(collapseEditions(books));
	/** The unfiltered shelf in the current arrangement's slots — "of y". */
	const shelfSize = $derived(activeGroup === 'series' ? books.length : works.length);
	// The query, the topic and the length narrow the shelf; `shelf` picks the view.
	const searching = $derived(
		!!(filters.values.q.trim() || filters.values.topic || filters.values.len)
	);
	// The Browse rows — from the books already loaded, no request of their own.
	const rows = $derived(browseRows(books)); // folds editions itself
	// Any filter or search in the URL lands on the grid, never on the rows; so
	// does a shelf too small to make a single row (a young language).
	const hasBrowse = $derived(rows.length > 0);
	const showAll = $derived(searching || filters.values.shelf === 'all' || !hasBrowse);

	const seeAllHref = (topic: string) =>
		localizeHref(`/books?shelf=all&topic=${encodeURIComponent(topic)}`);

	// Distinct topics present on the shelf, alphabetical, with how many books
	// each holds — the Filters panel's topic choices. A count is the cards the
	// choice shows, so editions folded into one slot count once.
	const allTopics = $derived.by(() => {
		const m = new Map<string, { slug: string; title: string; books: BookSummary[] }>();
		for (const b of books)
			for (const tc of b.topics ?? []) {
				const e = m.get(tc.slug) ?? { slug: tc.slug, title: tc.title, books: [] };
				e.books.push(b);
				m.set(tc.slug, e);
			}
		return [...m.values()]
			.map(({ slug, title, books: list }) => ({ slug, title, count: fold(list).length }))
			.sort((a, b) => a.title.localeCompare(b.title));
	});
	const isEnglish = $derived(getLang() === 'en');

	/** The length bucket a book falls in — at THIS reader's pace, so it agrees
	 *  with the reading time its card prints — or null for a book with no word
	 *  count, which prints no time and so is in no bucket. */
	const lengthOf = (b: BookSummary): BookLength | null =>
		b.word_count ? bookLength(readingMinutes(b.word_count)) : null;
	/** Cards per length bucket (editions folded, as above), for the panel's choices. */
	const lengthFacets = $derived.by(() => {
		const c: Record<BookLength, number> = { short: 0, mid: 0, long: 0 };
		for (const l of BOOK_LENGTHS) c[l] = fold(books.filter((b) => lengthOf(b) === l)).length;
		return c;
	});
	// An empty bucket is dropped — unless a link selected it, so the panel
	// still shows (and can lift) what is filtering the grid to nothing.
	const lengthChoices = $derived(
		BOOK_LENGTHS.filter((b) => lengthFacets[b] || b === filters.values.len)
	);
	/** A SheetChoices toggle: tapping the active choice lifts it, as the topic
	 *  chip row did. */
	const toggle = (cur: string, v: string) => (v === cur ? '' : v);

	// The filters currently narrowing the shelf, each liftable on its own
	// (query and topic, shared with every shelf, via filterChips; length is
	// this shelf's own). Lifting one keeps the reader on the grid: a filtered
	// link without `shelf=all` (an older shared one) would otherwise drop to
	// the Browse rows with its last chip.
	const activeChips = $derived.by(() => {
		const len = filters.values.len as BookLength | '';
		const lenChip: FilterChip | null = len
			? { kind: 'len', label: t(BOOK_LENGTH_LABEL[len]), onRemove: () => (filters.values.len = '') }
			: null;
		return [queryChip(filters), topicChip(filters, allTopics), lenChip]
			.filter((c): c is FilterChip => c !== null)
			.map((c) => ({ ...c, onRemove: () => (c.onRemove(), (filters.values.shelf = 'all')) }));
	});
	/** What the Filters panel is narrowing by — the count on its button. The
	 *  query shows in its own field; grouping and sort arrange, not narrow. */
	const sheetCount = $derived((filters.values.topic ? 1 : 0) + (filters.values.len ? 1 : 0));

	const filtered = $derived.by(() => {
		const q = filters.values.q.trim().toLowerCase();
		const len = filters.values.len;
		return books.filter((b) => {
			const topic = filters.values.topic;
			if (topic && !(b.topics ?? []).some((tc) => tc.slug === topic)) return false;
			if (len && lengthOf(b) !== len) return false;
			// Topic is a shelf-only facet; the title/subtitle/author query
			// is the shared primitive (also used by the topic shelf). q is already
			// normalised, and matchesBookQuery treats '' as "no filter".
			return matchesBookQuery(b, q);
		});
	});

	// What the filters left, one slot per work, in the chosen order (shelf order
	// preserves the API's sort_order).
	const sorted = $derived(sortBooks(fold(filtered), sort));

	// A page at a time, like Articles and Biographies: the whole library in one
	// grid ran 40 phone screens. Only the flat view pages — by author and by
	// series keep every book, since their quick-nav jumps to a book further down.
	// Larger pages than the other shelves, since a wide desktop shows seven
	// across (.book-grid--library). The first page is 56 so it ends on a full
	// row at 2, 4 and 7 columns (phone, tablet, wide desktop); each "Show 48
	// more" adds a multiple of 2 and 4, so phone and tablet rows stay full.
	const FIRST_PAGE = 56;
	const MORE_PAGE = 48;
	const flat = pager(
		() => sorted,
		() => `${filters.values.q}|${filters.values.topic}|${filters.values.len}|${sort}`,
		MORE_PAGE,
		FIRST_PAGE
	);
	export const pages = flat; // for the route's snapshot ($lib/paging)

	const groups = $derived.by(() => {
		if (activeGroup !== 'author') return null;
		const map = new Map<string, { slug: string; name: string; photo_url: string; books: BookSummary[] }>();
		for (const b of sorted) {
			const g = map.get(b.author.slug) ?? {
				slug: b.author.slug,
				name: b.author.name,
				photo_url: b.author.photo_url ?? '',
				books: []
			};
			g.books.push(b);
			map.set(b.author.slug, g);
		}
		return [...map.values()];
	});

	// The by-author shelf renders as ONE flat grid, not a <section> per author:
	// `authorFlat` is those groups concatenated, so an author's books stay
	// together while a one-book author is a single card in the row rather than a
	// heading over an otherwise empty one. `authorAnchor` maps each author's
	// first book to the `#author-<slug>` id the quick-nav jumps to.
	const authorFlat = $derived(groups ? groups.flatMap((g) => g.books) : []);

	// By series: a section per series (see groupBySeries). Unlike authors, a
	// series is several books by definition, so a section each never leaves a
	// heading over a lone card.
	// The Book Series rail: every series on the open shelf; under any filter,
	// the series among the books it leaves — so For Young Readers leads with its
	// four series, and a search for "rooted" with Rooted.
	const railSeries = $derived(searching ? seriesAmong(series, filtered) : series);

	const seriesGroups = $derived(
		activeGroup === 'series' ? groupBySeries(sorted, series.map((s) => s.slug)) : null
	);
	const authorAnchor = $derived(new Map((groups ?? []).map((g) => [g.books[0].slug, g.slug])));

	// How much the pinned controls bar covers (0 where it doesn't pin) — what the
	// author anchors and group headings clear, via --pinned-offset.
	let pinnedH = $state(0);

	// --- SEO: ItemList structured data ------------------------------------------
	// Item URLs are LOCALIZED. This shelf prerenders once per locale, and a bare
	// /books/<slug> here pointed the Swahili page's structured data at the
	// English book — telling a crawler that the /sw shelf lists /en works, and
	// contradicting the hreflang set the same page emits.
	const jsonLd = $derived(
		JSON.stringify({
			'@context': 'https://schema.org',
			'@type': 'ItemList',
			name: 'Ochorus Library',
			numberOfItems: books.length,
			itemListElement: books.slice(0, 60).map((b, i) => ({
				'@type': 'ListItem',
				position: i + 1,
				url: `${SITE_URL}${localizeHref(`/books/${b.slug}`)}`,
				item: {
					'@type': 'Book',
					name: b.title,
					author: { '@type': 'Person', name: b.author.name }
				}
			}))
		}).replace(/</g, '\\u003c')
	);
</script>

<svelte:head>
	{#if books.length}
		<!-- eslint-disable-next-line svelte/no-at-html-tags, no-useless-escape -->
		{@html `<script type="application/ld+json">${jsonLd}<\/script>`}
	{/if}
</svelte:head>

<!-- The way out of an empty localized shelf: the English library, which always
     has something in it. -->
{#snippet readEnglish()}
	<a href="/books" class="btn btn-primary inline-block">{t('books.readEnglish')}</a>
{/snippet}

<!-- A run of books in the chosen view — the flat shelf, or one by-series
     group. `eager` marks a run whose first row is the shelf's first row: its
     covers load at once, not from the lazy queue — but not at high priority,
     because the controls above put that row a screen down on a phone (the
     page's LCP there is the tagline, not a cover);
     `showSeries` is off under a series heading, which already names it. -->
{#snippet shelfBooks(list: BookSummary[], eager: boolean, showSeries: boolean)}
	{#if view === 'grid'}
		<div class="book-grid book-grid--library">
			{#each list as book, i (book.slug)}
				<BookCard {book} showAuthor {showSeries} eager={eager && i < 7} editions={editionsOf(book)} />
			{/each}
		</div>
	{:else}
		<div class="flex flex-col gap-1">
			{#each list as book (book.slug)}
				<BookListRow {book} {showSeries} editions={editionsOf(book)} />
			{/each}
		</div>
	{/if}
{/snippet}

<!-- Book Series — books written to be read together. A rail of the index's
     own cards (without their descriptions), so the reader meets on /series
     the card they tapped here. Under the Browse rows, and above the grid. -->
{#snippet seriesRail()}
	{#if railSeries.length}
		<section class="mb-8">
			<div class="flex items-baseline justify-between gap-3">
				<h2 class="section-label">{t('nav.series')}</h2>
				<a href={localizeHref('/series/')} class="shrink-0 text-small font-medium">
					{t('series.seeAll')}
				</a>
			</div>
			<!-- pt/pb leave room for the cards' hover lift and shadow, which the
			     rail's overflow would otherwise clip. -->
			<div class="cover-rail flex gap-4 pt-1 pb-2" use:scrollEdges>
				{#each railSeries as s (s.slug)}
					<div class="grid w-64 shrink-0">
						<SeriesCard series={s} compact />
					</div>
				{/each}
			</div>
		</section>
	{/if}
{/snippet}

<!-- Filtered the shelf down to nothing: clear the filters (Biographies' model). -->
{#snippet clearFiltersAction()}
	<button class="btn btn-ghost" onclick={clearFilters}>{t('common.clearFilters')}</button>
{/snippet}

<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {pinnedH}px)">
	<PageHeader title={t('nav.books')} tagline={t('books.tagline')} meta={books.length ? bookCounts : undefined} />
	{#snippet bookCounts()}
		<!-- Works, as the grid shows them; and, where young-reader editions fold
		     into their full texts, every edition too, so neither number hides. -->
		{works.length}
		{works.length === 1 ? t('common.bookOne') : t('common.bookMany')}
		{#if works.length < books.length}
			<span class="sep" aria-hidden="true">·</span>
			{t('books.editionsCount').replace('%n%', String(books.length))}
		{/if}
		<!-- No author count: its own (book writers, the imprint among them) ran
		     beside the library's on the home page and the A–Z as a second,
		     smaller number. The library has one, `countWriters`. No series link
		     either: the Book Series tab right below already is one. -->
	{/snippet}
	<!-- Under the title, not above it: the page's first words are its name,
	     not navigation (design review #4). -->
	<LibraryTabs
		current="books"
		series={series.length > 0}
		browse={hasBrowse ? { count: works.length, all: showAll } : undefined}
	/>

	{#if loadError}
		<!-- The API couldn't be reached. -->
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if books.length === 0}
		<!-- The library is empty in this language. The way out only exists when
		     there IS one: on /books itself, "read the English library" is where
		     the reader already is. -->
		<EmptyState art="language" message={t('books.noneInLanguage')} action={isEnglish ? undefined : readEnglish} />
	{:else}
		<!-- Continue reading — the shared resume rows (Plans and Series use them
		     too), most recently read first. -->
		{#if continueBooks.length && !searching}
			<ContinueShelf heading={t('books.continue')}>
				{#each continueBooks as c (c.book.slug)}
					{@const of = c.book.chapter_count}
					{@const caption = of
						? `${t('continue.chapter')} ${c.order} ${t('plans.of')} ${of}`
						: `${t('continue.chapter')} ${c.order}`}
					<ContinueRow
						href={localizeHref(chapterPath(c.book.slug, c.order, c.book.has_modern_edition))}
						title={c.book.title}
						{caption}
						verb={t('plans.continue')}
					>
						{#snippet visual()}
							<span class="w-10 shrink-0"><BookCover book={c.book} /></span>
						{/snippet}
						{#snippet progress()}
							{#if of}
								<ProgressBar percent={((c.order - 1) / of) * 100} label={`${c.book.title}: ${caption}`} />
							{/if}
						{/snippet}
					</ContinueRow>
				{/each}
			</ContinueShelf>
		{/if}

		{#if !showAll}
			<!-- Browse: a few named rows a reader can choose between, each with
			     "See all" into the grid (pre-filtered to its topic). The full grid
			     is the "All N books" tab above. -->
			<div class="browse-rows">
				<!-- Start here has no "See all": the whole library is the tab above. -->
				{#each rows as row, ri (row.topic?.slug ?? '')}
					{@const id = `row-${row.topic?.slug ?? 'start'}`}
					<section class="mb-8" aria-labelledby={id}>
						<div class="flex items-baseline justify-between gap-3">
							<h2 {id} class="section-label">{row.topic?.title ?? t('books.startHere')}</h2>
							{#if row.topic}
								<a href={seeAllHref(row.topic.slug)} class="shrink-0 text-small font-medium">
									{t('books.seeAll').replace('%n%', String(row.count))}
								</a>
							{/if}
						</div>
						<div class="cover-rail browse-row" use:scrollEdges>
							{#each row.books as book, i (book.slug)}
								<BookCard {book} showAuthor eager={ri === 0 && i < 6} editions={family.get(book.slug)} />
							{/each}
						</div>
					</section>
				{/each}
			</div>
			{@render seriesRail()}
		{:else}
			{@render seriesRail()}

			<!-- Controls: search · sort · ONE Filters button · view (design
			     review #15), pinned under the app nav (FilterBar) so a reader deep
			     in the shelf can refine without scrolling back up. One line at
			     every width, so it pins at every width. Topic, length and grouping
			     live in the Filters panel — a bottom sheet on a phone, a side sheet
			     from sm — and the topic chip row that pushed the grid down is gone;
			     on a phone sort and view move into the panel too. -->
			<FilterBar bind:pinned={pinnedH} class="mb-6">
				<div class="filter-row">
					<input
						bind:value={filters.values.q}
						type="search"
						class="filter-field grow"
						placeholder={t('books.filterPlaceholder')}
						aria-label={t('books.filterPlaceholder')}
					/>

					<select
						bind:value={sort}
						onchange={save}
						class="filter-field hidden sm:block"
						aria-label={t('common.sort')}
					>
						{#each BOOK_SORTS as v (v)}
							<option value={v}>{t(BOOK_SORT_LABEL[v])}</option>
						{/each}
					</select>

					<FilterSheet
						everywhere
						count={sheetCount}
						shown={sorted.length}
						showLabel={t('books.showResults')}
						filtered={searching}
						onClear={clearFilters}
					>
						{#if allTopics.length > 1}
							<SheetChoices
								label={t('common.topics')}
								options={[
									{ v: '', label: t('books.topicAll') },
									...allTopics.map((tc) => ({ v: tc.slug, label: tc.title, count: tc.count }))
								]}
								value={filters.values.topic}
								onselect={(v) => (filters.values.topic = toggle(filters.values.topic, v))}
							/>
						{/if}
						{#if lengthChoices.length > 1 || filters.values.len}
							<SheetChoices
								label={t('common.length')}
								options={[
									{ v: '', label: t('common.allLengths') },
									...lengthChoices.map((b) => ({
										v: b,
										label: t(BOOK_LENGTH_LABEL[b]),
										count: lengthFacets[b]
									}))
								]}
								value={filters.values.len}
								onselect={(v) => (filters.values.len = toggle(filters.values.len, v))}
							/>
						{/if}
						<SheetChoices
							label={t('books.groupLabel')}
							options={[
								{ v: 'all' as Group, label: t('books.groupAll') },
								{ v: 'author' as Group, label: t('books.groupAuthor') },
								...(hasSeries ? [{ v: 'series' as Group, label: t('books.groupSeries') }] : [])
							]}
							value={activeGroup}
							onselect={setGroup}
						/>
						<!-- Phone only: the bar has no room for these there. -->
						<div class="contents sm:hidden">
							<SheetChoices
								label={t('common.sort')}
								options={BOOK_SORTS.map((v) => ({ v, label: t(BOOK_SORT_LABEL[v]) }))}
								value={sort}
								onselect={setSort}
							/>
							<ViewToggle {view} onchange={setView} cls="w-full" btnCls="flex-1" />
						</div>
					</FilterSheet>

					<div class="hidden sm:contents">
						<ViewToggle {view} onchange={setView} />
					</div>
				</div>
			</FilterBar>

			<!-- What the filters have left, each one a removable chip, with "Clear
			     filters" — the only place a closed panel's choices show. The shelf
			     once showed nothing here at all, so a query matching nine of
			     fifty-nine books looked exactly like a library of nine. -->
			{#if searching}
				<FilterSummary
					shown={sorted.length}
					total={shelfSize}
					template={t('books.showing')}
					onClear={clearFilters}
					chips={activeChips}
					class="mb-6"
				/>
			{/if}

			<!-- Author quick-nav: the shared faces strip (Sermons uses it too). -->
			{#if groups && groups.length > 1}
				<AuthorJumpStrip
					class="mb-8"
					label={t('books.jumpAuthor')}
					href={(slug) => `#author-${slug}`}
					writers={groups.map((g) => ({ slug: g.slug, name: g.name, photo_url: g.photo_url, count: g.books.length }))}
				/>
			{/if}

			<!-- Results — in a size container, so the library grid steps to seven
			     across by the shelf's own width (.book-shelf-room in app.css). -->
			<div class="book-shelf-room">
				{#if sorted.length === 0}
					<!-- Books exist in this language but the filters removed them all — a
					     filtered-to-nothing state, so offer to clear (not the bare <p> that
					     made Books the odd shelf out; C2). -->
					<EmptyState art="search" message={t('books.noResults')} action={clearFiltersAction} />
				{:else if seriesGroups}
					<!-- By series: one section per series (group-heading recipe, the name
					     linking to the series page), then the books in no series. The
					     cards drop their series line — the heading already says it. -->
					{#each seriesGroups.named as g, gi (g.slug)}
						<section class="mb-10">
							<GroupHeading
								name={g.title}
								href={localizeHref(`/series/${g.slug}/`)}
								count={g.books.length}
							/>
							{@render shelfBooks(g.books, gi === 0, false)}
						</section>
					{/each}
					{#if seriesGroups.standalone.length}
						<section>
							<GroupHeading name={t('books.standalone')} count={seriesGroups.standalone.length} />
							{@render shelfBooks(seriesGroups.standalone, !seriesGroups.named.length, false)}
						</section>
					{/if}
				{:else if groups}
					<!-- By author: one flat shelf, books ordered so each author's works sit
					     together and the author rides every card. A <section> per author
					     turned a library of mostly one-book authors into a tall column of
					     near-empty rows; a single grid fills left-to-right, and the
					     quick-nav above still lands on each author's first book. -->
					{#if view === 'grid'}
						<div class="book-grid book-grid--library">
							{#each authorFlat as book, i (book.slug)}
								<BookCard
									{book}
									showAuthor
									eager={i < 7}
									anchor={authorAnchor.get(book.slug)}
									editions={editionsOf(book)}
								/>
							{/each}
						</div>
					{:else}
						<div class="flex flex-col gap-1">
							{#each authorFlat as book (book.slug)}
								<BookListRow {book} anchor={authorAnchor.get(book.slug)} editions={editionsOf(book)} />
							{/each}
						</div>
					{/if}
				{:else}
					{@render shelfBooks(flat.visible, true, true)}
					<ShowMore pager={flat} />
				{/if}
			</div>
		{/if}
	{/if}
</div>

<style>
	/* Sized off the rows' own width, like .book-grid--library in its
	   .book-shelf-room, so a card is the same width on both tabs. */
	.browse-rows {
		container: browse-rows / inline-size;
	}
	/* A Browse row: one line of the shelf's own cards that scrolls sideways
	   (the shared .cover-rail carries overflow, hidden phone scrollbar and edge
	   fades), snapping card by card. Columns are sized off the row's width the
	   way .book-grid steps — a little over two on a phone, so the next cover
	   peeks in and says "swipe", then four, five and six across (by the rows'
	   container, below). Gaps match .book-grid's 1rem. Block padding
	   keeps a card's hover lift and focus ring inside the scroller's clip. */
	.browse-row {
		--across: 2.3;
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: calc((100% - (var(--across) - 1) * 1rem) / var(--across));
		column-gap: 1rem;
		padding-block: 0.375rem 0.5rem;
		scroll-snap-type: x proximity;
	}
	.browse-row > :global(*) {
		scroll-snap-align: start;
	}
	@container browse-rows (min-width: 36rem) {
		.browse-row {
			--across: 4;
		}
	}
	@container browse-rows (min-width: 56rem) {
		.browse-row {
			--across: 5;
		}
	}
	@container browse-rows (min-width: 68rem) {
		.browse-row {
			--across: 6;
		}
	}
</style>
