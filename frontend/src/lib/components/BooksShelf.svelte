<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import { onMount } from 'svelte';
	import { isTranslated, type BookSummary, type SeriesSummary } from '$lib/library-public';
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
	import GroupHeading from './GroupHeading.svelte';
	import EmptyState from './EmptyState.svelte';
	import FilterSummary from './FilterSummary.svelte';
	import TopicFilterRow from './TopicFilterRow.svelte';
	import { queryChip, topicChip, type FilterChip } from '$lib/filterChips';
	import { matchesBookQuery, sortBooks, type BookSort } from '$lib/bookSort';
	import { groupBySeries } from '$lib/series';

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
	type Source = 'all' | 'public_domain' | 'translated';
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
	const filters = urlFilters({
		defaults: { q: '', source: 'all' as Source, topic: '' },
		allowed: { source: ['all', 'public_domain', 'translated'] },
		url: () => $page.url
	});
	const clearFilters = () => filters.reset();

	function save() {
		writeJSON(PREFS_KEY, { view, sort, group });
	}
	const setView = (v: View) => ((view = v), save());
	const setGroup = (g: Group) => ((group = g), save());
	function onSort(e: Event) {
		sort = (e.currentTarget as HTMLSelectElement).value as Sort;
		save();
	}

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
				return book ? { book, order: r.order } : null;
			})
			.filter((x): x is { book: BookSummary; order: number } => x !== null)
			.slice(0, 6);
	});

	// --- Derived --------------------------------------------------------------
	const searching = $derived(filters.active);
	const sourceTypes = $derived(new Set(books.map((b) => b.source_type)));
	const showSourceFilter = $derived(sourceTypes.size > 1);

	// Distinct topics present on the shelf, alphabetical — the topic-filter chips.
	const allTopics = $derived.by(() => {
		const m = new Map<string, string>();
		for (const b of books) for (const tc of b.topics ?? []) m.set(tc.slug, tc.title);
		return [...m].map(([slug, title]) => ({ slug, title })).sort((a, b) => a.title.localeCompare(b.title));
	});
	const authorCount = $derived(new Set(books.map((b) => b.author.slug)).size);
	const isEnglish = $derived(getLang() === 'en');

	// The filters currently narrowing the shelf, each liftable on its own. The
	// query and topic (shared with every shelf) come from filterChips; the source
	// segment shows its own state but rides along here so one row has the whole set.
	const SOURCE_LABEL: Record<string, string> = {
		public_domain: 'books.sourcePublic',
		translated: 'books.sourceTranslated'
	};
	const activeChips = $derived.by(() => {
		const c: FilterChip[] = [];
		const q = queryChip(filters);
		if (q) c.push(q);
		if (filters.values.source !== 'all')
			c.push({
				kind: 'source',
				label: t(SOURCE_LABEL[filters.values.source]),
				onRemove: () => (filters.values.source = 'all')
			});
		const topic = topicChip(filters, allTopics);
		if (topic) c.push(topic);
		return c;
	});

	// Newest additions first — a "new to the library" discovery strip. Hidden
	// while searching/filtering, and only when there are enough books to bother.
	const recent = $derived(
		[...books].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 8)
	);

	const filtered = $derived.by(() => {
		const q = filters.values.q.trim().toLowerCase();
		return books.filter((b) => {
			if (filters.values.source === 'public_domain' && isTranslated(b.source_type)) return false;
			if (filters.values.source === 'translated' && !isTranslated(b.source_type)) return false;
			const topic = filters.values.topic;
			if (topic && !(b.topics ?? []).some((tc) => tc.slug === topic)) return false;
			// Source and topic are shelf-only facets; the title/subtitle/author query
			// is the shared primitive (also used by the topic shelf). q is already
			// normalised, and matchesBookQuery treats '' as "no filter".
			return matchesBookQuery(b, q);
		});
	});

	const sorted = $derived(sortBooks(filtered, sort)); // shelf order preserves the API's sort_order

	// "By series" is offered only when some book on the shelf is in a named
	// series (never in a language with none, nor behind an API without the
	// field); a stored preference for it then falls back to the flat view.
	const hasSeries = $derived(books.some((b) => b.series));
	const activeGroup = $derived<Group>(group === 'series' && !hasSeries ? 'all' : group);

	const groups = $derived.by(() => {
		if (activeGroup !== 'author') return null;
		const map = new Map<string, { slug: string; name: string; books: BookSummary[] }>();
		for (const b of sorted) {
			const g = map.get(b.author.slug) ?? { slug: b.author.slug, name: b.author.name, books: [] };
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
	const seriesGroups = $derived(
		activeGroup === 'series' ? groupBySeries(sorted, series.map((s) => s.slug)) : null
	);
	const authorAnchor = $derived(new Map((groups ?? []).map((g) => [g.books[0].slug, g.slug])));

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
     group. `eager` marks a run whose first covers are above the fold;
     `showSeries` is off under a series heading, which already names it. -->
{#snippet shelfBooks(list: BookSummary[], eager: boolean, showSeries: boolean)}
	{#if view === 'grid'}
		<div class="book-grid">
			{#each list as book, i (book.slug)}
				<BookCard {book} showAuthor {showSeries} priority={eager && i < 6} />
			{/each}
		</div>
	{:else}
		<div class="flex flex-col gap-1">
			{#each list as book (book.slug)}
				<BookListRow {book} {showSeries} />
			{/each}
		</div>
	{/if}
{/snippet}

<!-- Filtered the shelf down to nothing: clear the filters (Biographies' model). -->
{#snippet clearFiltersAction()}
	<button class="btn btn-ghost" onclick={clearFilters}>{t('common.clearFilters')}</button>
{/snippet}

<div class="page-col px-5 py-10">
	<PageHeader title={t('nav.books')} tagline={t('books.tagline')} meta={books.length ? bookCounts : undefined} />
	{#snippet bookCounts()}
		{books.length}
		{books.length === 1 ? t('common.bookOne') : t('common.bookMany')}
		<span class="opacity-50">·</span>
		{authorCount} {t('books.authorsWord')}
		{#if series.length}
			<span class="opacity-50">·</span>
			<a href={localizeHref('/series/')}>
				{series.length}
				{series.length === 1 ? t('common.seriesOne') : t('common.seriesMany')}
			</a>
		{/if}
	{/snippet}

	{#if loadError}
		<!-- The API couldn't be reached. -->
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if books.length === 0}
		<!-- The library is empty in this language. The way out only exists when
		     there IS one: on /books itself, "read the English library" is where
		     the reader already is. -->
		<EmptyState message={t('books.noneInLanguage')} action={isEnglish ? undefined : readEnglish} />
	{:else}
		<!-- Continue reading -->
		{#if continueBooks.length && !searching}
			<section class="mb-8">
				<h2 class="section-label">
					{t('books.continue')}
				</h2>
				{#if continueBooks.length === 1}
					<!-- One book reads as a broken row when rendered as a scroll strip:
					     a single 80px cover marooned in the full page width. On its own
					     it becomes a proper resume card instead. -->
					{@const c = continueBooks[0]}
					<a
						href={localizeHref(`/books/${c.book.slug}/${c.order}`)}
						class="book-card book-card--row card-lift group !p-4 sm:max-w-md"
					>
						<div class="w-16 shrink-0 sm:w-20"><BookCover book={c.book} /></div>
						<div class="min-w-0 flex-1">
							<div class="line-clamp-2 text-body font-medium text-text">{c.book.title}</div>
							<div class="text-small text-muted">{c.book.author.name}</div>
							<div class="mt-1 text-small font-semibold text-accent">
								{t('continue.chapter')}
								{c.order} →
							</div>
						</div>
					</a>
				{:else}
					<div class="cover-rail flex gap-4 pb-1">
						{#each continueBooks as c (c.book.slug)}
							<a
								href={localizeHref(`/books/${c.book.slug}/${c.order}`)}
								class="w-20 shrink-0 hover:no-underline sm:w-24"
							>
								<BookCover book={c.book} />
								<div class="mt-1.5 line-clamp-2 text-eyebrow font-medium text-text">
									{c.book.title}
								</div>
								<div class="text-eyebrow text-muted">{t('continue.chapter')} {c.order}</div>
							</a>
						{/each}
					</div>
				{/if}
			</section>
		{/if}

		<!-- Book Series — books written to be read together. A rail of the index's
		     own cards (without their descriptions), so the reader meets on /series
		     the card they tapped here. -->
		{#if series.length && !searching}
			<section class="mb-8">
				<div class="flex items-baseline justify-between gap-3">
					<h2 class="section-label">{t('nav.series')}</h2>
					<a href={localizeHref('/series/')} class="shrink-0 text-small font-medium">
						{t('series.seeAll')}
					</a>
				</div>
				<!-- pt/pb leave room for the cards' hover lift and shadow, which the
				     rail's overflow would otherwise clip. -->
				<div class="cover-rail flex gap-4 pt-1 pb-2">
					{#each series as s (s.slug)}
						<div class="grid w-64 shrink-0">
							<SeriesCard series={s} compact />
						</div>
					{/each}
				</div>
			</section>
		{/if}

		<!-- New to the library -->
		{#if books.length > 8 && !searching}
			<section class="mb-8">
				<h2 class="section-label">
					{t('books.newTitle')}
				</h2>
				<div class="cover-rail flex gap-4 pb-1">
					{#each recent as book (book.slug)}
						<a
							href={localizeHref(`/books/${book.slug}`)}
							class="w-20 shrink-0 hover:no-underline sm:w-24"
						>
							<BookCover {book} />
							<div class="mt-1.5 line-clamp-2 text-eyebrow font-medium text-text">
								{book.title}
							</div>
							<div class="truncate text-eyebrow text-muted">{book.author.name}</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Controls: search · source · sort · group · view -->
		<div class="filter-row mb-6">
			<input
				bind:value={filters.values.q}
				type="search"
				class="filter-field grow"
				placeholder={t('books.filterPlaceholder')}
				aria-label={t('books.filterPlaceholder')}
			/>

			{#if showSourceFilter}
				<div class="seg">
					{#each [['all', t('books.sourceAll')], ['public_domain', t('books.sourcePublic')], ['translated', t('books.sourceTranslated')]] as opt (opt[0])}
						<button
							class:active={filters.values.source === opt[0]}
							onclick={() => (filters.values.source = opt[0] as Source)}
							aria-pressed={filters.values.source === opt[0]}>{opt[1]}</button
						>
					{/each}
				</div>
			{/if}

			<select
				value={sort}
				onchange={onSort}
				class="filter-field"
				aria-label={t('common.sort')}
			>
				<option value="shelf">{t('common.sortShelf')}</option>
				<option value="title">{t('common.sortTitle')}</option>
				<option value="longest">{t('common.sortLongest')}</option>
				<option value="shortest">{t('common.sortShortest')}</option>
			</select>

			<div class="seg">
				<button
					class:active={activeGroup === 'author'}
					onclick={() => setGroup('author')}
					aria-pressed={activeGroup === 'author'}>{t('books.groupAuthor')}</button
				>
				{#if hasSeries}
					<button
						class:active={activeGroup === 'series'}
						onclick={() => setGroup('series')}
						aria-pressed={activeGroup === 'series'}>{t('books.groupSeries')}</button
					>
				{/if}
				<button
					class:active={activeGroup === 'all'}
					onclick={() => setGroup('all')}
					aria-pressed={activeGroup === 'all'}>{t('books.groupAll')}</button
				>
			</div>

			<div class="seg">
				<button
					class:active={view === 'grid'}
					onclick={() => setView('grid')}
					aria-label={t('books.viewGrid')}
					aria-pressed={view === 'grid'}><Icon name="grid" /></button
				>
				<button
					class:active={view === 'list'}
					onclick={() => setView('list')}
					aria-label={t('books.viewList')}
					aria-pressed={view === 'list'}><Icon name="list" /></button
				>
			</div>
		</div>

		<!-- Topic filter -->
		<TopicFilterRow
			topics={allTopics}
			selected={filters.values.topic}
			onSelect={(topic) => (filters.values.topic = topic)}
		/>

		<!-- What the filters have left. The shelf showed nothing here at all, so a
		     query matching nine of fifty-nine books looked exactly like a library
		     of nine. -->
		{#if searching}
			<FilterSummary
				shown={filtered.length}
				total={books.length}
				template={t('books.showing')}
				onClear={clearFilters}
				chips={activeChips}
				class="mb-6"
			/>
		{/if}

		<!-- Author quick-nav -->
		{#if groups && groups.length > 1}
			<nav class="mb-8 flex flex-wrap items-center gap-1.5" aria-label={t('books.jumpAuthor')}>
				<span class="eyebrow text-muted me-1">{t('books.jumpAuthor')}</span>
				{#each groups as g (g.slug)}
					<a href="#author-{g.slug}" class="tag">
						{g.name}
					</a>
				{/each}
			</nav>
		{/if}

		<!-- Results -->
		{#if sorted.length === 0}
			<!-- Books exist in this language but the filters removed them all — a
			     filtered-to-nothing state, so offer to clear (not the bare <p> that
			     made Books the odd shelf out; C2). -->
			<EmptyState message={t('books.noResults')} action={clearFiltersAction} />
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
				<div class="book-grid">
					{#each authorFlat as book, i (book.slug)}
						<BookCard {book} showAuthor priority={i < 6} anchor={authorAnchor.get(book.slug)} />
					{/each}
				</div>
			{:else}
				<div class="flex flex-col gap-1">
					{#each authorFlat as book (book.slug)}
						<BookListRow {book} anchor={authorAnchor.get(book.slug)} />
					{/each}
				</div>
			{/if}
		{:else}
			{@render shelfBooks(sorted, true, true)}
		{/if}
	{/if}
</div>
