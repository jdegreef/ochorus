<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { type AuthorBio, type BookSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumb } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { locales } from '$lib/paraglide/runtime';
	import { ERAS, eraOf, type EraId } from '$lib/eras';
	import AuthorBioCard from '$lib/components/AuthorBioCard.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';

	const t = i18n.t;

	let { data } = $props();
	const authors = $derived<AuthorBio[]>(data.authors);
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
	const coerce = <T extends string>(v: string | null, allowed: readonly T[], dflt: T): T =>
		allowed.includes((v ?? '') as T) ? ((v ?? '') as T) : dflt;

	// The controls are URL-addressable (?q=&filter=&sort=&full=1) so a filtered
	// view is shareable, survives a reload, and comes back with the Back button.
	// State starts at defaults and is hydrated from the URL on mount by the
	// reader $effect below (client-only), then written on change (syncUrl).
	// We must NOT read $page.url.searchParams here: SvelteKit forbids query-param
	// access while prerendering this page, and the prerendered HTML must not
	// depend on the query string anyway (it's served for the bare /biographies).
	// `urlState` is the loop guard shared by writer and reader — same pattern as
	// /search.
	let queryText = $state('');
	let filter = $state<Filter>('all');
	let sort = $state<Sort>('name');
	let fullBioOnly = $state(false);

	const snapshot = (q: string, f: Filter, s: Sort, full: boolean) =>
		`${q.trim()}|${f}|${s}|${full ? '1' : '0'}`;
	let urlState = snapshot('', 'all', 'name', false);

	function syncUrl() {
		const key = snapshot(queryText, filter, sort, fullBioOnly);
		if (key === urlState) return;
		urlState = key;
		const url = new URL($page.url);
		// Omit defaults so a pristine view stays a clean /biographies URL.
		const put = (k: string, v: string) =>
			v ? url.searchParams.set(k, v) : url.searchParams.delete(k);
		put('q', queryText.trim());
		put('filter', filter === 'all' ? '' : filter);
		put('sort', sort === 'name' ? '' : sort);
		put('full', fullBioOnly ? '1' : '');
		goto(url, { replaceState: true, keepFocus: true, noScroll: true });
	}

	// URL → state, for shared links and Back/Forward. The urlState guard makes
	// our own syncUrl writes fall straight through (no writer/reader loop).
	$effect(() => {
		const p = $page.url.searchParams;
		const next = {
			q: p.get('q') ?? '',
			f: coerce(p.get('filter'), FILTER_VALUES, 'all'),
			s: coerce(p.get('sort'), SORT_VALUES, 'name'),
			full: p.get('full') === '1'
		};
		const key = snapshot(next.q, next.f, next.s, next.full);
		if (key === urlState) return;
		urlState = key;
		queryText = next.q;
		filter = next.f;
		sort = next.s;
		fullBioOnly = next.full;
	});

	function clearFilters() {
		// Clears the search + filters but keeps the chosen sort order.
		queryText = '';
		filter = 'all';
		fullBioOnly = false;
		syncUrl();
	}

	// "In the library" means "has something to read here" — including writers
	// represented only by sermons.
	const worksCount = (a: AuthorBio) => a.book_count + a.sermon_count;

	const filtered = $derived.by(() => {
		const q = queryText.trim().toLowerCase();
		return authors.filter((a) => {
			if (filter === 'library' && worksCount(a) === 0) return false;
			if (filter === 'bio' && worksCount(a) > 0) return false;
			if (fullBioOnly && !a.has_long_bio) return false;
			if (!q) return true;
			return a.name.toLowerCase().includes(q) || (a.bio ?? '').toLowerCase().includes(q);
		});
	});

	// The pinned bar was 177px on a 375px screen — 22% of the viewport, kept
	// forever. On mobile the secondary controls now collapse behind a Filters
	// toggle, leaving search (the thing you actually reach for) plus the toggle.
	// `hidden` is conditional and `sm:` overrides it, so desktop is untouched
	// and there is no duplicated markup.
	let filtersOpen = $state(false);
	const activeCount = $derived(
		(queryText.trim() !== '' ? 1 : 0) + (filter !== 'all' ? 1 : 0) + (fullBioOnly ? 1 : 0)
	);

	// Count summary + whether any narrowing is active (sort doesn't count).
	const isFiltered = $derived(queryText.trim() !== '' || filter !== 'all' || fullBioOnly);

	/** Reveal the page holding `slug`, then scroll to it once it has painted. */
	function jumpTo(slug: string) {
		const i = sorted.findIndex((a) => a.slug === slug);
		if (i < 0) return;
		const needed = Math.ceil((i + 1) / PER_PAGE);
		if (needed > pageNum) pageNum = needed;
		// The row may not exist yet this frame; wait for the render it triggered.
		tick().then(() =>
			document.getElementById(slug)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
		);
	}

	// A–Z jump targets for the name sort: first writer per initial letter. Each
	// card already carries id={slug} + scroll-mt, so the rail links to #<slug>.
	const AZ = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
	const firstByLetter = $derived.by(() => {
		const m = new Map<string, string>();
		if (sort !== 'name') return m;
		for (const a of sorted) {
			const c = a.name.trim()[0]?.toUpperCase() ?? '';
			if (c >= 'A' && c <= 'Z' && !m.has(c)) m.set(c, a.slug);
		}
		return m;
	});

	const sorted = $derived.by(() => {
		const arr = [...filtered];
		switch (sort) {
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
	const pageCount = $derived(Math.max(1, Math.ceil(sorted.length / PER_PAGE)));
	const paged = $derived(sorted.slice(0, pageNum * PER_PAGE));
	const remaining = $derived(sorted.length - paged.length);
	// Narrowing the list must not strand you on page 3 of 1.
	$effect(() => {
		void queryText; void filter; void fullBioOnly; void sort;
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

	// Breadcrumb trail (Home › Biographies) — the visible <Breadcrumb> below and
	// this BreadcrumbList JSON-LD describe the same path, matching the rest of the
	// site's detail pages. The last item is the current page but stays in the
	// structured list (Google expects the full trail including the leaf).
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('bios.eyebrow'), href: '/biographies' }
	]);
	const crumbsLd = $derived(
		jsonLd(breadcrumb(crumbs.map((c) => ({ name: c.name, url: c.href }))))
	);

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

	// Redirect old /biographies#<slug> deep-links to the new author pages.
	onMount(() => {
		const slug = location.hash.replace(/^#/, '');
		if (slug) goto(localizeHref(`/authors/${slug}`), { replaceState: true });
	});
</script>

<svelte:head>
	<title>{t('bios.metaTitle')} — Ochorus</title>
	<meta name="description" content={t('bios.metaDescription')} />
	<link rel="canonical" href="{SITE_URL}{localizeHref('/biographies')}" />
	{#each locales as loc (loc)}
		<link rel="alternate" hreflang={loc} href="{SITE_URL}{localizeHref('/biographies', { locale: loc })}" />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_URL}/biographies" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="{t('bios.metaTitle')} — Ochorus" />
	<meta property="og:description" content={t('bios.metaDescription')} />
	<meta property="og:url" content="{SITE_URL}{localizeHref('/biographies')}" />
	<meta property="og:image" content="{SITE_URL}/og/biographies.png" />
	<meta name="twitter:card" content="summary_large_image" />
	{@html peopleLd}
	{@html crumbsLd}
</svelte:head>

<div class="mx-auto max-w-4xl px-5 py-8">
	<Breadcrumb items={crumbs} />
	<!-- No eyebrow: the breadcrumb directly above already reads "Biographies",
	     and the pair cost a whole row of the first screen to say it twice. -->
	<header class="mb-5">
		<h1 class="text-display mb-2">{t('bios.title')}</h1>
		<p class="text-body text-muted">
			{t('bios.tagline')}
		</p>
	</header>

	<!-- Controls + A–Z, pinned. With one writer per row the list is 35 screens
	     long, so the filters and the letter jump have to come WITH you — the app
	     nav is position:relative and scrolls away, so top-0 is free.
	     -mx-5 px-5 lets the background span the container's padding. -->
	<div
		class="sticky top-0 z-20 -mx-5 mb-6 border-b border-border bg-bg px-5 pb-2.5 pt-3"
	>
	<!-- Controls: search · filter · sort -->
	<div class="flex flex-wrap items-center gap-2">
		<input
			bind:value={queryText}
			oninput={syncUrl}
			type="search"
			class="min-w-[10rem] flex-1 rounded-sm border border-border bg-surface px-3 py-1.5 text-small text-text"
			placeholder={t('bios.filterPlaceholder')}
			aria-label={t('bios.filterPlaceholder')}
		/>

		<!-- Mobile only: reveals the rest. Carries a count so a collapsed panel
		     can never hide the fact that the list is being narrowed. -->
		<button
			class="flex shrink-0 items-center gap-1 rounded-sm border border-border px-2.5 py-1.5 text-[0.78rem] text-muted sm:hidden"
			onclick={() => (filtersOpen = !filtersOpen)}
			aria-expanded={filtersOpen}
		>
			{t('bios.filters')}
			{#if activeCount}
				<span class="rounded-full bg-accent px-1.5 text-[0.68rem] font-semibold text-accent-contrast"
					>{activeCount}</span
				>
			{/if}
		</button>

		<div class="overflow-hidden rounded-sm border border-border text-[0.78rem] sm:flex" class:hidden={!filtersOpen} class:flex={filtersOpen}>
			{#each FILTERS as opt (opt.v)}
				<button
					class="px-2.5 py-1.5"
					class:bg-accent={filter === opt.v}
					class:text-accent-contrast={filter === opt.v}
					class:text-muted={filter !== opt.v}
					onclick={() => { filter = opt.v; syncUrl(); }}
					aria-pressed={filter === opt.v}>{t(opt.k)}</button
				>
			{/each}
		</div>

		<!-- Orthogonal to the library/bio segments: narrows to writers with a
		     full-length biography (the "Full life" badge). -->
		<button
			class="rounded-sm border border-border px-2.5 py-1.5 text-[0.78rem] sm:block"
			class:hidden={!filtersOpen}
			class:bg-accent={fullBioOnly}
			class:text-accent-contrast={fullBioOnly}
			class:text-muted={!fullBioOnly}
			onclick={() => { fullBioOnly = !fullBioOnly; syncUrl(); }}
			aria-pressed={fullBioOnly}>{t('bios.fullLife')}</button
		>

		<select
			bind:value={sort}
			onchange={syncUrl}
			class="rounded-sm border border-border bg-surface px-2 py-1.5 text-small text-text sm:block"
			class:hidden={!filtersOpen}
			aria-label={t('bios.sort')}
		>
			<option value="name">{t('bios.sortName')}</option>
			<option value="era">{t('bios.sortEra')}</option>
			<option value="books">{t('bios.sortBooks')}</option>
		</select>
	</div>

	<!-- Result count + a one-tap escape hatch when a filter is narrowing the list. -->
	<div class="mt-1.5 items-center gap-2 text-small text-muted sm:flex" class:hidden={!filtersOpen} class:flex={filtersOpen}>
		<span
			>{t('bios.showing')
				.replace('%shown%', String(sorted.length))
				.replace('%total%', String(authors.length))}</span
		>
		{#if isFiltered}
			<button onclick={clearFilters} class="font-semibold text-accent hover:underline"
				>{t('bios.clearFilters')}</button
			>
		{/if}
	</div>

	<!-- A–Z rail: jump to the first writer under each initial (name sort only). -->
	{#if sort === 'name' && sorted.length > 1}
		<nav class="mt-1.5 hidden flex-wrap gap-x-1 gap-y-0.5 text-small sm:flex" aria-label={t('bios.jumpAz')}>
			{#each AZ as letter (letter)}
				{#if firstByLetter.has(letter)}
					<!-- A BUTTON, not an anchor. Paging paints 24 rows, so a writer under
					     a late letter has no element to anchor to yet — the prerender
					     crawler caught exactly that ("no element with id=r-a-torrey").
					     Reveal first, then scroll; and with no href there is no dangling
					     fragment in the static output. -->
					<button
						class="rounded px-1.5 py-0.5 font-semibold text-accent hover:bg-accent-soft"
						onclick={() => jumpTo(firstByLetter.get(letter)!)}>{letter}</button
					>
				{:else}
					<span class="px-1.5 py-0.5 text-muted opacity-40" aria-hidden="true">{letter}</span>
				{/if}
			{/each}
		</nav>
	{/if}
	</div>

	{#if sorted.length === 0}
		<div class="py-16 text-center">
			<p class="text-body text-muted">{t('bios.noResults')}</p>
			{#if isFiltered}
				<button
					onclick={clearFilters}
					class="mt-3 text-small font-semibold text-accent hover:underline"
					>{t('bios.clearFilters')}</button
				>
			{/if}
		</div>
	{:else if sort === 'era'}
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
							class="whitespace-nowrap text-[0.72rem] font-semibold text-muted transition-colors group-hover:text-accent"
							>{t(g.era.k)}</span
						>
						{#if g.era.range}<span class="whitespace-nowrap text-[0.65rem] text-muted opacity-70"
								>{g.era.range}</span
							>{/if}
					</a>
				{/each}
			</nav>
		{/if}
		{#each eraGroups as g (g.era.id)}
			<section id="era-{g.era.id}" class="mb-12 scroll-mt-36">
				<!-- Pinned under the controls bar: four centuries of writers scroll
				     past, and without this you lose track of which era you are in.
				     top-[125px] clears the bar; z-10 keeps it under the bar's z-20. -->
				<h2
					class="sticky top-[125px] z-10 mb-6 flex items-baseline gap-2 border-b border-border bg-bg pb-2 pt-2 text-h3 text-text"
				>
					<a
						href={localizeHref(`/biographies/era/${g.era.id}`)}
						class="!text-text hover:text-accent hover:no-underline">{t(g.era.k)}</a
					>
					<!-- Same nowrap rule as the per-writer dates: a year range must never
					     break across lines ("–" / "1499"). The longer era names make the
					     heading wrap on narrow screens, so this is load-bearing here. -->
					{#if g.era.range}<span class="whitespace-nowrap text-small font-normal text-muted">{g.era.range}</span>{/if}
					<span class="ms-auto text-small font-normal text-muted">{g.authors.length}</span>
				</h2>
				<div class="space-y-4">
					{#each g.authors as author (author.slug)}
						<AuthorBioCard {author} shelf={booksByAuthor.get(author.slug) ?? []} />
					{/each}
				</div>
			</section>
		{/each}
	{:else}
		<div class="space-y-4">
			{#each paged as author (author.slug)}
				<AuthorBioCard {author} shelf={booksByAuthor.get(author.slug) ?? []} />
			{/each}
		</div>
		{#if remaining > 0}
			<div class="mt-8 flex flex-col items-center gap-2">
				<button
					class="rounded-sm border border-border px-4 py-2 text-small font-semibold text-accent hover:border-accent"
					onclick={() => (pageNum += 1)}
				>
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
