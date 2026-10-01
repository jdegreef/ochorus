<script lang="ts">
	import { filingKey, initialOf } from '$lib/authorIndex';
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { fullLifeDiscriminates, type AuthorBio, type BookSummary, type Hub } from '$lib/library-public';
	import { hubPath, placeGroups } from '$lib/hubs';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumbLd, hreflangAll } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { ERAS, eraOf, type EraId } from '$lib/eras';
	import AuthorBioCard from '$lib/components/AuthorBioCard.svelte';
	import BioTile from '$lib/components/BioTile.svelte';
	import EraBand from '$lib/components/EraBand.svelte';
	import FacetMenu from '$lib/components/FacetMenu.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import {
		facetCounts,
		hubMembers,
		inFacets,
		parseFacets,
		toggleIn,
		type EraCard,
		type FacetKey
	} from '$lib/bioFacets';
	import type { FacetOption } from '$lib/components/FacetMenu.svelte';
	import { readJSON, writeJSON } from '$lib/persisted';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import { urlFilters } from '$lib/urlFilters.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FilterSheet from '$lib/components/FilterSheet.svelte';
	import { pager, pagedSnapshot } from '$lib/paging.svelte';
	import SheetChoices from '$lib/components/SheetChoices.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';
	import { queryChip, type FilterChip } from '$lib/filterChips';
	import { jumpToSection } from '$lib/scrollSpy.svelte';

	const t = i18n.t;

	let { data } = $props();
	const authors = $derived<AuthorBio[]>(data.authors);
	const loadError = $derived<boolean>(data.loadError);
	const books = $derived<BookSummary[]>(data.books ?? []);
	const hubs = $derived<Hub[]>(data.hubs ?? []);
	const traditions = $derived(hubs.filter((h) => h.kind === 'tradition'));
	const places = $derived(placeGroups(hubs));

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
	// to get backwards. `trad`, `place` and `era` are comma lists of hub slugs /
	// era ids ($lib/bioFacets) — free text to urlFilters, validated against the
	// hubs this language has by parseFacets.
	const filters = urlFilters({
		defaults: {
			q: '',
			filter: 'all' as Filter,
			sort: 'name' as Sort,
			full: '',
			trad: '',
			place: '',
			era: ''
		},
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

	// Name + bio, lowercased once per roster rather than once per keystroke.
	// The newline keeps a query from matching across the name/bio seam.
	const haystack = $derived(
		new Map(authors.map((a) => [a.slug, `${a.name}\n${a.bio ?? ''}`.toLowerCase()]))
	);
	// Everything but the three facets: search, has-books, full life. The facet
	// menus count within this pool, so it is computed once and shared.
	const basePool = $derived.by(() => {
		const q = filters.values.q.trim().toLowerCase();
		const { filter, full } = filters.values;
		return authors.filter((a) => {
			if (filter === 'library' && worksCount(a) === 0) return false;
			if (filter === 'bio' && worksCount(a) > 0) return false;
			if (showFullLife && full === '1' && !a.has_long_bio) return false;
			return !q || haystack.get(a.slug)!.includes(q);
		});
	});

	// --- Facets: tradition · place · era ----------------------------------------
	// The tradition/place hubs and the eras, as in-page filters. Their pages are
	// still linked (the Browse block under the list) — they are what search
	// engines index — but on the index a tick narrows the list in place.
	const members = $derived(hubMembers(hubs));
	const facets = $derived(
		parseFacets({ trad: filters.values.trad, place: filters.values.place, era: filters.values.era }, hubs)
	);
	// A value this language can't show (a hub that only exists in English, from a
	// shared link) is dropped by parseFacets — so drop it from the URL too, or it
	// would count as "filtered" with no chip to lift it (the stale-?full=1 rule).
	$effect(() => {
		for (const k of ['trad', 'place', 'era'] as const) {
			const clean = facets[k].join(',');
			if (clean !== filters.values[k]) filters.values[k] = clean;
		}
	});
	const toggleFacet = (k: FacetKey, v: string) => (filters.values[k] = toggleIn(filters.values[k], v));

	const filtered = $derived(basePool.filter((a) => inFacets(a, facets, members)));

	/** A facet's options with each one's count attached (facetCounts). */
	const withCounts = (k: FacetKey, opts: Omit<FacetOption, 'count'>[]): FacetOption[] => {
		const n = facetCounts(basePool, facets, members, k, opts.map((o) => o.v));
		return opts.map((o) => ({ ...o, count: n.get(o.v) ?? 0 }));
	};

	// The writers per era, best-known first (portraits, then most to read) —
	// the faces on the band. Depends on the roster only, not the filters.
	const byEra = $derived.by(() => {
		const m = new Map<EraId, AuthorBio[]>();
		for (const a of authors) {
			const id = eraOf(a.birth_year);
			m.set(id, [...(m.get(id) ?? []), a]);
		}
		for (const xs of m.values())
			xs.sort((a, b) => Number(!!b.photo_url) - Number(!!a.photo_url) || worksCount(b) - worksCount(a));
		return m;
	});
	// Only the eras that have writers in this language at all.
	const presentEras = $derived(ERAS.filter((e) => byEra.has(e.id)));

	// The three facets, each with its label and counted options — one list the
	// toolbar menus, the phone sheet and the chips all read. Places are each
	// region with its places indented beneath it; places with no region page in
	// this language follow unindented (placeGroups' "Elsewhere").
	const facetGroups = $derived.by(() => {
		const groups: { k: FacetKey; label: string; options: FacetOption[] }[] = [
			{
				k: 'trad',
				label: t('bios.tradition'),
				options: withCounts('trad', traditions.map((h) => ({ v: h.slug, label: h.label })))
			},
			{
				k: 'place',
				label: t('bios.place'),
				options: withCounts(
					'place',
					places.flatMap((g) => [
						...(g.region ? [{ v: g.region.slug, label: g.region.label, strong: true }] : []),
						...g.places.map((p) => ({ v: p.slug, label: p.label, indent: !!g.region }))
					])
				)
			},
			{
				k: 'era',
				label: t('bios.era'),
				options: withCounts('era', presentEras.map((e) => ({ v: e.id, label: t(e.k) })))
			}
		];
		return groups.filter((g) => g.options.length);
	});
	const facetLabel = $derived(
		new Map(facetGroups.flatMap((g) => g.options.map((o) => [`${g.k}:${o.v}`, o.label])))
	);

	// The era band: each era's count (under the other filters) and three faces.
	const eraCards = $derived.by(() => {
		const counts = facetGroups.find((g) => g.k === 'era')?.options ?? [];
		return presentEras.map(
			(e): EraCard => ({
				id: e.id,
				name: t(e.k),
				range: e.range,
				count: counts.find((o) => o.v === e.id)?.count ?? 0,
				faces: byEra.get(e.id)!.slice(0, 3)
			})
		);
	});

	// --- View: rows or a portrait grid (a reader preference → localStorage) ----
	type View = 'list' | 'grid';
	const VIEW_KEY = 'ochorus:bios-view';
	let view = $state<View>('list');
	onMount(() => {
		if (readJSON<View>(VIEW_KEY, 'list') === 'grid') view = 'grid';
	});
	const setView = (v: View) => {
		view = v;
		writeJSON(VIEW_KEY, v);
	};

	// The pinned bar was 177px on a 375px screen — 22% of the viewport, kept
	// forever. On a phone it is search (the thing you actually reach for) plus a
	// Filters button whose sheet holds the rest; from sm the controls sit inline.
	/** Measured height of the pinned controls bar — the era headings pin below it. */
	let controlsH = $state(0);
	/** What the sheet is narrowing by (FilterSheet's `count`). */
	const sheetCount = $derived(
		(filters.values.filter !== 'all' ? 1 : 0) +
			(showFullLife && filters.values.full ? 1 : 0) +
			Object.values(facets).reduce((n, xs) => n + xs.length, 0)
	);

	// The filters currently narrowing the roster, each liftable on its own. The
	// query (shared with every shelf) comes from filterChips; the has-books switch
	// and the Full-life toggle show their state in their own controls, but ride
	// along so one row carries the whole set and every part has a ×. The
	// `full` chip follows the same showFullLife guard as its control and the
	// badge — a stale ?full=1 with no visible toggle must not surface a chip.
	const activeChips = $derived.by(() => {
		const c: FilterChip[] = [];
		const q = queryChip(filters);
		if (q) c.push(q);
		// 'bio' has no control of its own any more — only an old shared link sets it.
		if (filters.values.filter !== 'all')
			c.push({
				kind: 'filter',
				label: t(filters.values.filter === 'bio' ? 'bios.filterBioOnly' : 'bios.filterInLibrary'),
				onRemove: () => (filters.values.filter = 'all')
			});
		if (showFullLife && filters.values.full === '1')
			c.push({ kind: 'full', label: t('bios.fullLife'), onRemove: () => (filters.values.full = '') });
		for (const k of ['trad', 'place', 'era'] as const)
			for (const v of facets[k])
				c.push({ kind: `${k}:${v}`, label: facetLabel.get(`${k}:${v}`) ?? v, onRemove: () => toggleFacet(k, v) });
		return c;
	});

	// Count summary + whether any narrowing is active (sort doesn't count).
	const isFiltered = $derived(filters.active);

	/** Reveal the page holding `slug`, then scroll to it once it has painted. */
	function jumpTo(slug: string) {
		const i = sorted.findIndex((a) => a.slug === slug);
		if (i < 0) return;
		pages.reveal(i);
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
			// One filing rule with the library A–Z: by surname, accents folded.
			const c = initialOf(filingKey(a.name));
			if (c !== '#' && !m.has(c)) m.set(c, a.slug);
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
				// Filed by surname, like the library A–Z (Tozer under T).
				return arr.sort((a, b) => filingKey(a.name).localeCompare(filingKey(b.name)));
		}
	});

	// --- Paging ---------------------------------------------------------------
	// One writer per row makes 35 a long scroll. Client-side only: the API
	// already returns every writer (that is what the A–Z rail and the filters
	// count against), so this is purely how many are PAINTED. The A–Z stays the
	// fast path — jumping to a letter reveals whatever page holds it, below.
	// Keyed to the filters and sort, so narrowing never strands you on page 3
	// of 1; the snapshot brings Back to where you were ($lib/paging).
	const pages = pager(
		() => sorted,
		() => Object.values(filters.values).join('|')
	);
	export const snapshot = pagedSnapshot(() => pages);

	const SORT_LABEL: Record<Sort, string> = {
		name: 'bios.sortName',
		era: 'bios.sortEra',
		books: 'bios.sortBooks'
	};

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

<!-- The snippets below are each rendered twice: in the inline row (sm up)
     and in the phone sheet. -->
<!-- "Has books to read" — the old All / In the library / Biography only
     segment as the one question people actually ask of it. A shared
     ?filter=bio still works; it shows as a removable chip in the summary. -->
{#snippet hasBooksToggle()}
	<button
		type="button"
		role="switch"
		aria-checked={filters.values.filter === 'library'}
		class="filter-field has-books"
		class:is-active={filters.values.filter === 'library'}
		onclick={() => (filters.values.filter = filters.values.filter === 'library' ? 'all' : 'library')}
	>
		<span class="switch" aria-hidden="true"></span>{t('bios.hasBooks')}
	</button>
{/snippet}
<!-- Orthogonal to the has-books switch: narrows to writers with a
     full-length biography (the "Full life" badge). Shown only when it
     actually splits the roster (see showFullLife) — in English almost every
     writer has a full bio, so the chip would remove almost no one. -->
{#snippet fullLifeChip()}
	<button
		class="chip"
		class:active={filters.values.full === '1'}
		onclick={() => (filters.values.full = filters.values.full ? '' : '1')}
		aria-pressed={filters.values.full === '1'}>{t('bios.fullLife')}</button
	>
{/snippet}

{#snippet clearFiltersAction()}
	<button class="btn btn-ghost" onclick={clearFilters}>{t('common.clearFilters')}</button>
{/snippet}

<!-- One card family per view: the row card, or the portrait tile. -->
{#snippet writers(list: AuthorBio[])}
	{#if view === 'grid'}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-5">
			{#each list as author (author.slug)}
				<BioTile {author} />
			{/each}
		</div>
	{:else}
		<div class="space-y-4">
			{#each list as author (author.slug)}
				<AuthorBioCard {author} {showFullLife} shelf={booksByAuthor.get(author.slug) ?? []} />
			{/each}
		</div>
	{/if}
{/snippet}

<!--
	`--pinned-offset` is how far down the page the first unobstructed pixel is:
	the sticky app nav plus this page's own pinned controls bar. Everything that
	pins or scrolls into view below reads it, so there is one number to be right
	rather than four hard-coded ones drifting apart.
-->
<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {controlsH}px)">
	<!-- No visible breadcrumb: this is a top-level destination already marked
	     active in the nav, and it was the only one of the six browse pages
	     carrying a trail. Detail pages (a book, an author) still get one, where
	     the hierarchy is real. The BreadcrumbList JSON-LD stays — it describes
	     the page's position for search results, which is still true. -->
	<PageHeader title={t('nav.biographies')} tagline={t('bios.tagline')} />

	<!-- The eras as the page's one visual way in. They used to hide behind the
	     "By era" sort; now each is a card that filters the list to it. -->
	{#if eraCards.length > 1 && !loadError}
		<div class="mb-5">
			<EraBand
				eras={eraCards}
				selected={facets.era}
				label={t('bios.era')}
				ontoggle={(id) => toggleFacet('era', id)}
			/>
		</div>
	{/if}

	<!-- Controls + status, pinned under the app nav (which is itself sticky, hence
	     the --appnav-h offset). The list is many screens long, so the filters and
	     the letter jump have to come WITH you. -mx-5 px-5 lets the background span
	     the container's padding. Its height is measured rather than assumed: the
	     row and the status line both wrap, so the era headings below have to pin
	     under whatever it currently is.

	     The tradition and place chip walls that used to sit above this (~400px
	     before the first writer) are the Tradition / Place menus now; their pages
	     are linked from the Browse block under the list. -->
	<div
		bind:clientHeight={controlsH}
		class="sticky z-20 -mx-5 mb-6 border-b border-border bg-bg px-5 pb-2.5 pt-3" style="top: var(--appnav-h, 0px)"
	>
	<!-- Controls: search · tradition · place · era · has-books · sort · view -->
	<div class="filter-row">
		<input
			bind:value={filters.values.q}
			type="search"
			class="filter-field grow"
			placeholder={t('bios.filterPlaceholder')}
			aria-label={t('bios.filterPlaceholder')}
		/>

		<!-- Phone only: the same controls, as one-tap choices in a sheet. -->
		<FilterSheet
			count={sheetCount}
			shown={sorted.length}
			showLabel={t('bios.showResults')}
			filtered={isFiltered}
			onClear={clearFilters}
		>
			<div class="flex flex-wrap gap-2">
				{@render hasBooksToggle()}
				{#if showFullLife}{@render fullLifeChip()}{/if}
			</div>
			{#each facetGroups as g (g.k)}
				<SheetChoices
					label={g.label}
					options={g.options}
					isActive={(v) => facets[g.k].includes(v)}
					onselect={(v) => toggleFacet(g.k, v)}
				/>
			{/each}
			<SheetChoices
				label={t('bios.sort')}
				options={SORT_VALUES.map((v) => ({ v, label: t(SORT_LABEL[v]) }))}
				value={filters.values.sort}
				onselect={(v) => (filters.values.sort = v)}
			/>
			<SheetChoices
				label={t('bios.view')}
				options={[
					{ v: 'list' as View, label: t('bios.viewList') },
					{ v: 'grid' as View, label: t('bios.viewGrid') }
				]}
				value={view}
				onselect={setView}
			/>
		</FilterSheet>

		<div class="hidden sm:contents">
			{#each facetGroups as g (g.k)}
				<FacetMenu
					label={g.label}
					options={g.options}
					selected={facets[g.k]}
					ontoggle={(v) => toggleFacet(g.k, v)}
					onclear={() => (filters.values[g.k] = '')}
				/>
			{/each}
			{@render hasBooksToggle()}
			{#if showFullLife}
				{@render fullLifeChip()}
			{/if}
			<div class="seg ms-auto" role="group" aria-label={t('bios.sort')}>
				{#each SORT_VALUES as v (v)}
					<button
						type="button"
						class:active={filters.values.sort === v}
						aria-pressed={filters.values.sort === v}
						onclick={() => (filters.values.sort = v)}>{t(SORT_LABEL[v])}</button
					>
				{/each}
			</div>
			<div class="seg" role="group" aria-label={t('bios.view')}>
				<button type="button" class="view-btn" class:active={view === 'list'} aria-pressed={view === 'list'} aria-label={t('bios.viewList')} onclick={() => setView('list')}>
					<Icon name="list" />
				</button>
				<button type="button" class="view-btn" class:active={view === 'grid'} aria-pressed={view === 'grid'} aria-label={t('bios.viewGrid')} onclick={() => setView('grid')}>
					<Icon name="grid" />
				</button>
			</div>
		</div>
	</div>

	<!-- Status line: the count and a removable chip per active filter (only while
	     filtering), and the A–Z jump at the far end (name sort only). -->
	{#if isFiltered || (filters.values.sort === 'name' && sorted.length > 1)}
		<div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5">
			{#if isFiltered}
				<FilterSummary
					shown={sorted.length}
					total={authors.length}
					template={t('bios.showing')}
					onClear={clearFilters}
					chips={activeChips}
				/>
			{/if}
			{#if filters.values.sort === 'name' && sorted.length > 1}
				<!-- On a phone a single row that swipes sideways; from sm up it wraps. -->
				<nav
					class="az-rail flex max-w-full gap-x-0.5 gap-y-0.5 overflow-x-auto text-small [scrollbar-width:none] sm:ms-auto sm:flex-wrap sm:overflow-visible"
					aria-label={t('bios.jumpAz')}
				>
					{#each AZ as letter (letter)}
						{#if firstByLetter.has(letter)}
							<!-- A BUTTON, not an anchor. Paging paints 24 rows, so a writer under
							     a late letter has no element to anchor to yet — the prerender
							     crawler caught exactly that ("no element with id=r-a-torrey").
							     Reveal first, then scroll; and with no href there is no dangling
							     fragment in the static output. -->
							<button
								class="shrink-0 rounded-sm px-1 py-0.5 font-semibold text-accent hover:bg-accent-soft"
								onclick={() => jumpTo(firstByLetter.get(letter)!)}>{letter}</button
							>
						{:else}
							<span class="shrink-0 px-1 py-0.5 text-muted opacity-40" aria-hidden="true">{letter}</span>
						{/if}
					{/each}
				</nav>
			{/if}
		</div>
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
				{@render writers(g.authors)}
			</section>
		{/each}
	{:else}
		{@render writers(pages.visible)}
		{#if pages.remaining > 0}
			<div class="mt-8 flex flex-col items-center gap-2">
				<button class="btn btn-ghost" onclick={pages.more}>
					{t('bios.showMore').replace('%n%', String(pages.next))}
				</button>
				<p class="text-small text-muted">
					{t('bios.showing')
						.replace('%shown%', String(pages.visible.length))
						.replace('%total%', String(sorted.length))}
				</p>
			</div>
		{/if}
	{/if}
	<!-- Browse: the tradition, place and era PAGES. The same groupings filter the
	     list in place from the toolbar; these links are the way to each page's
	     own intro, Q&A and "where to start reading" shelf — and they keep every
	     hub and era page linked from the static HTML of the site's most-crawled
	     index (the prerender crawler and search engines both follow them; an era
	     page once went unbuilt because its only link sat behind a client sort). -->
	{#if hubs.length || presentEras.length}
		<nav class="mt-14 flex flex-col gap-5 border-t border-border pt-8" aria-label={t('bios.eyebrow')}>
			{#if traditions.length}
				<div>
					<h2 class="section-label mb-2.5">{t('hubs.byTradition')}</h2>
					<ul class="flex flex-wrap gap-2">
						{#each traditions as h (h.slug)}
							<li><a class="tag" href={localizeHref(hubPath(h))}>{h.label}</a></li>
						{/each}
					</ul>
				</div>
			{/if}
			{#if places.length}
				<div>
					<h2 class="section-label mb-2.5">{t('hubs.byPlace')}</h2>
					<ul class="flex flex-wrap gap-2">
						{#each places as g (g.region?.slug ?? '')}
							{#if g.region}
								<li><a class="tag font-semibold" href={localizeHref(hubPath(g.region))}>{g.region.label}</a></li>
							{/if}
							{#each g.places as h (h.slug)}
								<li><a class="tag" href={localizeHref(hubPath(h))}>{h.label}</a></li>
							{/each}
						{/each}
					</ul>
				</div>
			{/if}
			{#if presentEras.length}
				<div>
					<h2 class="section-label mb-2.5">{t('hubs.byEra')}</h2>
					<ul class="flex flex-wrap gap-2">
						{#each presentEras as e (e.id)}
							<li><a class="tag" href={localizeHref(`/biographies/era/${e.id}`)}>{t(e.k)}</a></li>
						{/each}
					</ul>
				</div>
			{/if}
		</nav>
	{/if}
</div>

<style>
	/* On a touch phone the A–Z letters (21×25) take a full-height target; the
	   strip scrolls sideways there, so width stays letter-sized. Not on a touch
	   tablet: from sm the strip wraps, and 44px rows would swell the pinned
	   header. */
	@media (pointer: coarse) and (max-width: 639.98px) {
		.az-rail button {
			display: inline-flex;
			align-items: center;
			justify-content: center;
			min-width: 2.25rem;
			min-height: 2.75rem;
		}
	}
	/* "Has books to read": a field-shaped switch, so it sits in the row at the
	   same height as the menus beside it. */
	.has-books {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
		white-space: nowrap;
	}
	.switch {
		position: relative;
		flex-shrink: 0;
		width: 1.9rem;
		height: 1.1rem;
		border-radius: 999px;
		background: var(--border-strong);
		transition: background var(--duration-base, 150ms);
	}
	.switch::after {
		content: '';
		position: absolute;
		top: 0.15rem;
		inset-inline-start: 0.15rem;
		width: 0.8rem;
		height: 0.8rem;
		border-radius: 999px;
		background: var(--surface);
		transition: inset-inline-start var(--duration-base, 150ms);
	}
	.has-books.is-active .switch {
		background: var(--accent);
	}
	.has-books.is-active .switch::after {
		inset-inline-start: 0.95rem;
	}
	.view-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}
</style>
