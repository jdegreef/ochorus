<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { fullLifeDiscriminates, type AuthorBio, type BookSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumbLd, hreflangAll } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { ERAS, eraOf, type EraId } from '$lib/eras';
	import AuthorBioCard from '$lib/components/AuthorBioCard.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import { urlFilters } from '$lib/urlFilters.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';
	import { queryChip, type FilterChip } from '$lib/filterChips';
	import { jumpToSection } from '$lib/scrollSpy.svelte';

	const t = i18n.t;

	let { data } = $props();
	const authors = $derived<AuthorBio[]>(data.authors);
	const loadError = $derived<boolean>(data.loadError);
	const books = $derived<BookSummary[]>(data.books ?? []);

	// Group the library's books by author slug for the per-writer cover strip.
	const booksByAuthor = $derived.by(() => {
		const m = new Map<string, BookSummary[]>();
		for (const b of books) {
			const arr = m.get(b.author.slug);
			if (arr) arr.push(b);
			else m.set(b.author.slug, [b]);
		}
		return m;
	});

	// --- Search · filter · sort -------------------------------------------------
	// Value lists are the single source of truth: the Filter/Sort types derive
	// from them, and coerce() uses them to reject junk query-string values.
	const FILTER_VALUES = ['all', 'library', 'bio'] as const;
	const SORT_VALUES = ['name', 'era', 'books'] as const;
	type Filter = (typeof FILTER_VALUES)[number];
	type Sort = (typeof SORT_VALUES)[number];
	// The controls are URL-addressable (?q=&filter=&sort=&full=1) so a filtered
	// view is shareable, survives a reload, and comes back with the Back button.
	// Encoding, loop guard, debounce and prerender safety all live in
	// $lib/urlFilters — shared with the Books shelf, which had a hand-written
	// copy of every one of them.
	//
	// `full` is a string because the URL is: '1' or ''. Keeping the flag in that
	// shape rather than laundering a boolean in and out is one fewer conversion
	// to get backwards.
	const filters = urlFilters({
		defaults: { q: '', filter: 'all' as Filter, sort: 'name' as Sort, full: '' },
		allowed: { filter: FILTER_VALUES, sort: SORT_VALUES, full: ['1'] },
		url: () => $page.url
	});

	function clearFilters() {
		// Clears the search + filters but keeps the chosen sort order.
		filters.reset({ sort: filters.values.sort });
	}

	// "In the library" means "has something to read here" — including writers
	// represented only by sermons.
	const worksCount = (a: AuthorBio) => a.book_count + a.sermon_count;

	// The "Full life" badge/chip only carry information when they actually SPLIT
	// the roster — in English almost every writer now has a full bio, so they
	// would be noise. Self-tunes per locale; the rule lives in library-public.ts
	// so the index and the era pages agree.
	const showFullLife = $derived(fullLifeDiscriminates(authors));

	// A stale ?full=1 from a shared link must not linger once the chip that sets it
	// is hidden — it would otherwise drive the filter summary and the active-count
	// badge with no visible control to clear it.
	$effect(() => {
		if (!showFullLife && filters.values.full) filters.values.full = '';
	});

	const filtered = $derived.by(() => {
		const q = filters.values.q.trim().toLowerCase();
		return authors.filter((a) => {
			if (filters.values.filter === 'library' && worksCount(a) === 0) return false;
			if (filters.values.filter === 'bio' && worksCount(a) > 0) return false;
			if (showFullLife && filters.values.full === '1' && !a.has_long_bio) return false;
			if (!q) return true;
			return a.name.toLowerCase().includes(q) || (a.bio ?? '').toLowerCase().includes(q);
		});
	});

	// The pinned bar was 177px on a 375px screen — 22% of the viewport, kept
	// forever. On mobile the secondary controls now collapse behind a Filters
	// toggle, leaving search (the thing you actually reach for) plus the toggle.
	// `hidden` is conditional and `sm:` overrides it, so desktop is untouched
	// and there is no duplicated markup.
	/** Measured height of the pinned controls bar — the era headings pin below it. */
	let controlsH = $state(0);
	let filtersOpen = $state(false);
	const activeCount = $derived(
		(filters.values.q.trim() !== '' ? 1 : 0) +
		(filters.values.filter !== 'all' ? 1 : 0) +
		(showFullLife && filters.values.full ? 1 : 0)
	);

	// The filters currently narrowing the roster, each liftable on its own. The
	// query (shared with every shelf) comes from filterChips; the library/bio
	// segment and the Full-life toggle show their state in their own controls,
	// but ride along so one row carries the whole set and every part has a ×. The
	// `full` chip follows the same showFullLife guard as its control and the
	// badge — a stale ?full=1 with no visible toggle must not surface a chip.
	const activeChips = $derived.by(() => {
		const c: FilterChip[] = [];
		const q = queryChip(filters);
		if (q) c.push(q);
		if (filters.values.filter !== 'all') {
			const k = FILTERS.find((f) => f.v === filters.values.filter)?.k;
			if (k)
				c.push({ kind: 'filter', label: t(k), onRemove: () => (filters.values.filter = 'all') });
		}
		if (showFullLife && filters.values.full === '1')
			c.push({ kind: 'full', label: t('bios.fullLife'), onRemove: () => (filters.values.full = '') });
		return c;
	});

	// Count summary + whether any narrowing is active (sort doesn't count).
	const isFiltered = $derived(filters.active);

	/** Reveal the page holding `slug`, then scroll to it once it has painted. */
	function jumpTo(slug: string) {
		const i = sorted.findIndex((a) => a.slug === slug);
		if (i < 0) return;
		const needed = Math.ceil((i + 1) / PER_PAGE);
		if (needed > pageNum) pageNum = needed;
		// The row may not exist yet this frame; wait for the render it triggered.
		tick().then(() => jumpToSection(slug));
	}

	// A–Z jump targets for the name sort: first writer per initial letter. Each
	// card already carries id={slug} + scroll-mt, so the rail links to #<slug>.
	const AZ = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
	const firstByLetter = $derived.by(() => {
		const m = new Map<string, string>();
		if (filters.values.sort !== 'name') return m;
		for (const a of sorted) {
			const c = a.name.trim()[0]?.toUpperCase() ?? '';
			if (c >= 'A' && c <= 'Z' && !m.has(c)) m.set(c, a.slug);
		}
		return m;
	});

	const sorted = $derived.by(() => {
		const arr = [...filtered];
		switch (filters.values.sort) {
			case 'era':
				// Earliest-born first; unknown birth years sink to the end.
				return arr.sort(
					(a, b) => (a.birth_year ?? 9999) - (b.birth_year ?? 9999) || a.name.localeCompare(b.name)
				);
			case 'books':
				// Ranks by everything readable, matching the filter above.
				return arr.sort((a, b) => worksCount(b) - worksCount(a) || a.name.localeCompare(b.name));
			default:
				return arr.sort((a, b) => a.name.localeCompare(b.name));
		}
	});

	// --- Paging ---------------------------------------------------------------
	// One writer per row makes 35 a long scroll. Client-side only: the API
	// already returns every writer (that is what the A–Z rail and the filters
	// count against), so this is purely how many are PAINTED. The A–Z stays the
	// fast path — jumping to a letter reveals whatever page holds it, below.
	const PER_PAGE = 24;
	let pageNum = $state(1);
	const paged = $derived(sorted.slice(0, pageNum * PER_PAGE));
	const remaining = $derived(sorted.length - paged.length);
	// Narrowing the list must not strand you on page 3 of 1.
	$effect(() => {
		void filters.values.q;
		void filters.values.filter;
		void filters.values.full;
		void filters.values.sort;
		pageNum = 1;
	});


	const FILTERS: { v: Filter; k: string }[] = [
		{ v: 'all', k: 'bios.filterAll' },
		{ v: 'library', k: 'bios.filterInLibrary' },
		{ v: 'bio', k: 'bios.filterBioOnly' }
	];

	// --- Eras -------------------------------------------------------------------
	// ERAS / eraOf live in $lib/eras (shared with the per-era landing pages).
	// Grouped, era-ordered sections built from `sorted` (already ascending by
	// birth year in the era sort), keeping only eras that have writers.
	const eraGroups = $derived.by(() => {
		const byId = new Map<EraId, AuthorBio[]>();
		for (const a of sorted) {
			const id = eraOf(a.birth_year);
			const arr = byId.get(id);
			if (arr) arr.push(a);
			else byId.set(id, [a]);
		}
		return ERAS.filter((e) => byId.has(e.id)).map((e) => ({ era: e, authors: byId.get(e.id)! }));
	});

	// BreadcrumbList JSON-LD (Home › Biographies). No visible trail on this
	// top-level page (see the header below); the schema still describes the
	// site's detail pages. The last item is the current page but stays in the
	// structured list (Google expects the full trail including the leaf).
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('bios.eyebrow'), href: '/biographies' }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));

	// The page as a schema.org CollectionPage whose mainEntity is the roster of
	// writers — an ItemList of Person entities, one per writer, mirroring the
	// Person data on each author page. Gives search engines both a typed page
	// (collection) and a structured list (rich results + entity discovery). Built
	// from the full list, not the current filter, so the markup describes the
	// page's whole content.
	const peopleLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: `${t('bios.metaTitle')} — Ochorus`,
			url: absUrl(localizeHref('/biographies')),
			description: t('bios.metaDescription'),
			mainEntity: {
				'@type': 'ItemList',
				name: 'Christian writers on Ochorus',
				numberOfItems: authors.length,
				itemListElement: authors.map((a, i) => ({
					'@type': 'ListItem',
					position: i + 1,
					item: {
						'@type': 'Person',
						name: a.name,
						url: absUrl(localizeHref(`/authors/${a.slug}`)),
						image: a.photo_url ? absUrl(a.photo_url) : undefined,
						description: a.bio || undefined,
						birthDate: a.birth_year ? String(a.birth_year) : undefined,
						deathDate: a.death_year ? String(a.death_year) : undefined
					}
				}))
			}
		})
	);

	// Redirect old /biographies#<slug> deep-links to the new author pages —
	// but ONLY for a fragment that names an author we actually have. Any other
	// fragment used to be forwarded too, so `/biographies#main` (the target of
	// the layout's own skip link, and a natural thing to copy or share after
	// using the keyboard) replaced a working page with the 404 — and
	// `replaceState` erased the good URL from history on the way.
	onMount(() => {
		const slug = location.hash.replace(/^#/, '');
		if (slug && authors.some((a) => a.slug === slug)) {
			goto(localizeHref(`/authors/${slug}`), { replaceState: true });
		}
	});

	// Gated on ADVERTISED_LOCALES, not Paraglide's full `locales`: a locale that
	// is wired in the UI but has an empty catalog must not be advertised to
	// crawlers (see advertised-locales.ts). This page was claiming alternates
	// for draft locales while sitemap.xml, the detail pages and the footer all
	// correctly omitted them — two contradictory claims, with the wrong one on
	// the site's most-crawled pages.
	const hreflang = hreflangAll('/biographies');
	const canonical = `${SITE_URL}${localizeHref('/biographies')}`;
</script>

<Seo
	title={`${t('bios.metaTitle')} — Ochorus`}
	description={t('bios.metaDescription')}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/biographies.png`}
	structuredData={[peopleLd, crumbsLd]}
/>

<!--
	`--pinned-offset` is how far down the page the first unobstructed pixel is:
	the sticky app nav plus this page's own pinned controls bar. Everything that
	pins or scrolls into view below reads it, so there is one number to be right
	rather than four hard-coded ones drifting apart.
-->
{#snippet clearFiltersAction()}
	<button class="btn btn-ghost" onclick={clearFilters}>{t('common.clearFilters')}</button>
{/snippet}

<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {controlsH}px)">
	<!-- No visible breadcrumb: this is a top-level destination already marked
	     active in the nav, and it was the only one of the six browse pages
	     carrying a trail. Detail pages (a book, an author) still get one, where
	     the hierarchy is real. The BreadcrumbList JSON-LD stays — it describes
	     the page's position for search results, which is still true. -->
	<PageHeader title={t('nav.biographies')} tagline={t('bios.tagline')} />

	<!-- Controls + A–Z, pinned under the app nav (which is itself sticky, hence
	     the --appnav-h offset). With one writer per row the list is 35 screens
	     long, so the filters and the letter jump have to come WITH you.
	     -mx-5 px-5 lets the background span the container's padding.
	     Its height is measured rather than assumed: the filter row and the A–Z
	     strip both wrap, so the bar is anywhere from ~70px to ~160px tall and
	     the era headings below have to pin under whatever it currently is. -->
	<div
		bind:clientHeight={controlsH}
		class="sticky z-20 -mx-5 mb-6 border-b border-border bg-bg px-5 pb-2.5 pt-3" style="top: var(--appnav-h, 0px)"
	>
	<!-- Controls: search · filter · sort -->
	<div class="filter-row">
		<input
			bind:value={filters.values.q}
			type="search"
			class="filter-field grow"
			placeholder={t('bios.filterPlaceholder')}
			aria-label={t('bios.filterPlaceholder')}
		/>

		<!-- Mobile only: reveals the rest. Carries a count so a collapsed panel
		     can never hide the fact that the list is being narrowed. -->
		<button
			class="chip flex shrink-0 items-center gap-1 sm:hidden"
			onclick={() => (filtersOpen = !filtersOpen)}
			aria-expanded={filtersOpen}
		>
			{t('bios.filters')}
			{#if activeCount}
				<span class="rounded-full bg-accent-soft px-1.5 text-eyebrow font-semibold text-accent"
					>{activeCount}</span
				>
			{/if}
		</button>

		<div class="seg sm:flex" class:hidden={!filtersOpen} class:flex={filtersOpen}>
			{#each FILTERS as opt (opt.v)}
				<button
					class:active={filters.values.filter === opt.v}
					onclick={() => (filters.values.filter = opt.v)}
					aria-pressed={filters.values.filter === opt.v}>{t(opt.k)}</button
				>
			{/each}
		</div>

		<!-- Orthogonal to the library/bio segments: narrows to writers with a
		     full-length biography (the "Full life" badge). Shown only when it
		     actually splits the roster (see showFullLife) — in English almost every
		     writer has a full bio, so the chip would remove almost no one. -->
		{#if showFullLife}
			<button
				class="chip sm:block"
				class:hidden={!filtersOpen}
				class:active={filters.values.full === '1'}
				onclick={() => (filters.values.full = filters.values.full ? '' : '1')}
				aria-pressed={filters.values.full === '1'}>{t('bios.fullLife')}</button
			>
		{/if}

		<select
			bind:value={filters.values.sort}
			class="filter-field sm:block"
			class:hidden={!filtersOpen}
			aria-label={t('bios.sort')}
		>
			<option value="name">{t('bios.sortName')}</option>
			<option value="era">{t('bios.sortEra')}</option>
			<option value="books">{t('bios.sortBooks')}</option>
		</select>
	</div>

	<!-- Result count + a one-tap escape hatch when a filter is narrowing the list.
	     Positioned by this bar rather than by the component's own default: it
	     lives INSIDE the pinned controls, and follows them open and shut on a
	     phone. -->
	{#if isFiltered}
		<FilterSummary
			shown={sorted.length}
			total={authors.length}
			template={t('bios.showing')}
			onClear={clearFilters}
			chips={activeChips}
			class="mt-1.5 {filtersOpen ? 'flex' : 'hidden'} sm:flex"
		/>
	{/if}

	<!-- A–Z rail: jump to the first writer under each initial (name sort only). -->
	{#if filters.values.sort === 'name' && sorted.length > 1}
		<nav class="mt-1.5 hidden flex-wrap gap-x-1 gap-y-0.5 text-small sm:flex" aria-label={t('bios.jumpAz')}>
			{#each AZ as letter (letter)}
				{#if firstByLetter.has(letter)}
					<!-- A BUTTON, not an anchor. Paging paints 24 rows, so a writer under
					     a late letter has no element to anchor to yet — the prerender
					     crawler caught exactly that ("no element with id=r-a-torrey").
					     Reveal first, then scroll; and with no href there is no dangling
					     fragment in the static output. -->
					<button
						class="rounded-sm px-1.5 py-0.5 font-semibold text-accent hover:bg-accent-soft"
						onclick={() => jumpTo(firstByLetter.get(letter)!)}>{letter}</button
					>
				{:else}
					<span class="px-1.5 py-0.5 text-muted opacity-40" aria-hidden="true">{letter}</span>
				{/if}
			{/each}
		</nav>
	{/if}
	</div>

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if sorted.length === 0}
		<EmptyState message={t('bios.noResults')} action={isFiltered ? clearFiltersAction : undefined} />
	{:else if filters.values.sort === 'era'}
		{#if eraGroups.length > 1}
			<!-- A slim timeline: each era is a node on a baseline, its name + year
			     range below, jumping to that section. Scrolls horizontally when the
			     eras outrun the width. -->
			<nav class="mb-10 flex gap-0.5 overflow-x-auto pb-2" aria-label={t('bios.sortEra')}>
				{#each eraGroups as g (g.era.id)}
					<a
						href="#era-{g.era.id}"
						class="group flex shrink-0 flex-col items-center gap-1.5 px-2 hover:no-underline"
					>
						<span class="relative flex h-2.5 w-full items-center justify-center">
							<span class="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-border"></span>
							<span
								class="relative h-2.5 w-2.5 rounded-full border border-border bg-surface transition-colors group-hover:border-accent group-hover:bg-accent"
							></span>
						</span>
						<span
							class="whitespace-nowrap text-eyebrow font-semibold text-muted transition-colors group-hover:text-accent"
							>{t(g.era.k)}</span
						>
						{#if g.era.range}<span class="whitespace-nowrap text-eyebrow text-muted opacity-70"
								>{g.era.range}</span
							>{/if}
					</a>
				{/each}
			</nav>
		{/if}
		{#each eraGroups as g (g.era.id)}
			<section
				id="era-{g.era.id}"
				class="mb-12"
				style="scroll-margin-top: calc(var(--pinned-offset, 5rem) + 0.5rem)"
			>
				<!-- Pinned under the controls bar: four centuries of writers scroll
				     past, and without this you lose track of which era you are in.
				     `GroupHeading`'s sticky variant reads `--pinned-offset` (set on
				     the page column above — the nav plus the MEASURED controls bar; a
				     hard-coded 125px once parked the heading inside the bar and it
				     vanished on scroll) and pushes the count to the far end. -->
				<GroupHeading
					sticky
					name={t(g.era.k)}
					href={localizeHref(`/biographies/era/${g.era.id}`)}
					count={g.authors.length}
				>
					{#snippet detail()}
						<!-- Same nowrap rule as the per-writer dates: a year range must
						     never break across lines ("–" / "1499"). The longer era names
						     make the heading wrap on narrow screens, so this is
						     load-bearing here. -->
						{#if g.era.range}<span class="whitespace-nowrap text-small font-normal text-muted"
								>{g.era.range}</span
							>{/if}
					{/snippet}
				</GroupHeading>
				<div class="space-y-4">
					{#each g.authors as author (author.slug)}
						<AuthorBioCard {author} {showFullLife} shelf={booksByAuthor.get(author.slug) ?? []} />
					{/each}
				</div>
			</section>
		{/each}
	{:else}
		<div class="space-y-4">
			{#each paged as author (author.slug)}
				<AuthorBioCard {author} {showFullLife} shelf={booksByAuthor.get(author.slug) ?? []} />
			{/each}
		</div>
		{#if remaining > 0}
			<div class="mt-8 flex flex-col items-center gap-2">
				<button class="btn btn-ghost" onclick={() => (pageNum += 1)}>
					{t('bios.showMore').replace('%n%', String(Math.min(PER_PAGE, remaining)))}
				</button>
				<p class="text-small text-muted">
					{t('bios.showing')
						.replace('%shown%', String(paged.length))
						.replace('%total%', String(sorted.length))}
				</p>
			</div>
		{/if}
	{/if}
</div>
