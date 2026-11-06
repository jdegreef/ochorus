<script lang="ts">
	import { authorPath } from '$lib/originals';
	import { formatLifespan, type SermonSummary } from '$lib/library-public';
	import { SvelteSet } from 'svelte/reactivity';
	import { SITE_URL } from '$lib/config';
	import { collectionPage, breadcrumbLd, hreflangAll } from '$lib/seo';
	import ForPromo from '$lib/components/ForPromo.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { pager, pagedSnapshot } from '$lib/paging.svelte';
	import { featuredOrder, startWith } from '$lib/sermonPicks';
	import { canonGrid } from '$lib/sermonCanon';
	import { isPlainPrimaryClick } from '$lib/plainClick';
	import { tick } from 'svelte';
	import Portrait from '$lib/components/Portrait.svelte';
	import ShowMore from '$lib/components/ShowMore.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import SermonOfTheDay from '$lib/components/SermonOfTheDay.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';
	import TopicFilterRow from '$lib/components/TopicFilterRow.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import FilterSheet from '$lib/components/FilterSheet.svelte';
	import SheetChoices from '$lib/components/SheetChoices.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import AuthorJumpStrip from '$lib/components/AuthorJumpStrip.svelte';
	import { queryChip, topicChip, type FilterChip } from '$lib/filterChips';
	import { urlFilters } from '$lib/urlFilters.svelte';
	import { writeFilters } from '$lib/urlFilters';
	import { getLang } from '$lib/lang.svelte';
	import { page } from '$app/stores';
	import { portraitPosition } from '$lib/portraits';
	import { readingMinutes, readingTime } from '$lib/reading';
	import { lengthBucket, LENGTH_BUCKETS } from '$lib/sermonLength';
	import type { LengthBucket } from '$lib/sermonLength';

	const t = i18n.t;

	let { data } = $props();
	const sermons = $derived<SermonSummary[]>(data.sermons);
	const loadError = $derived<boolean>(data.loadError);

	// How much is on the shelf, for the header counts line — over the WHOLE shelf,
	// not the current filter (it describes the library, like the Books header).
	const preacherCount = $derived(new Set(sermons.map((s) => s.author.slug)).size);

	// Self-referential canonical: each localized copy of this prerendered page
	// points at ITSELF, not the English URL (which would deindex translations).
	const canonical = `${SITE_URL}${localizeHref('/sermons')}`;

	// The shelf as a CollectionPage carrying its own ordered ItemList — a crawler
	// sees the works (not an opaque grid), hung off the page entity rather than a
	// floating list. `url` is the canonical so the two never disagree.
	const sermonsLd = $derived(
		collectionPage({
			name: t('nav.sermons'),
			description: t('sermons.metaDescription'),
			url: canonical,
			items: sermons.map((s) => ({ name: s.title, url: localizeHref(`/sermons/${s.slug}`) }))
		})
	);
	// Home › Sermons — this shelf's place in the hierarchy, as a BreadcrumbList.
	// The same breadcrumbLd() the sermon detail pages feed their trail through.
	const crumbsLd = breadcrumbLd([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.sermons'), href: '/sermons' }
	]);

	// --- Filters ----------------------------------------------------------------
	// The shelf's filters live in the URL (shareable, reloadable, Back-able) via
	// $lib/urlFilters — the same helper Books and Biographies use. The
	// arrangement (`group`, `sort`) rides along, as Biographies' sort does, so
	// Back and a reload keep it (see Arrangement below).
	const FILTER_DEFAULTS = { q: '', book: '', len: '', topic: '', group: 'all', sort: 'shelf' };
	const filters = urlFilters({
		defaults: FILTER_DEFAULTS,
		// `len`, `group` and `sort` are enums — an off-list value in the URL falls
		// back to the default. `topic` is a free-text slug (like `book`).
		allowed: { len: LENGTH_BUCKETS, group: ['all', 'preacher'], sort: ['shelf', 'scripture', 'title', 'shortest'] },
		url: () => $page.url
	});

	/** The reading-time bucket a sermon falls in — at THIS reader's pace, so it
	 *  agrees with the "N min read" the row shows. */
	const lengthOf = (s: SermonSummary): LengthBucket => lengthBucket(readingMinutes(s.word_count));

	/** Length buckets present on the shelf, with counts, for the filter's options.
	 *  Reactive: the reader's pace can carry a sermon across a boundary, exactly
	 *  as it moves the printed times. */
	const lengthFacets = $derived.by(() => {
		const c: Record<LengthBucket, number> = { short: 0, mid: 0, long: 0 };
		for (const s of sermons) c[lengthOf(s)]++;
		return c;
	});

	/** Option labels per bucket — the boundaries the buckets actually use. */
	const LENGTH_LABEL: Record<LengthBucket, string> = {
		short: 'sermons.lengthShort',
		mid: 'sermons.lengthMid',
		long: 'sermons.lengthLong'
	};

	/** Canonical position of a sermon's book; undated books sink to the end. */
	const bookOrder = (s: SermonSummary) => s.scripture_book_order ?? 999;

	// Books of the Bible present on this shelf, in canonical order, with counts.
	const bookFacets = $derived.by(() => {
		const m = new Map<string, { name: string; order: number; count: number }>();
		for (const s of sermons) {
			if (!s.scripture_book) continue;
			const e = m.get(s.scripture_book);
			if (e) e.count++;
			else m.set(s.scripture_book, { name: s.scripture_book, order: bookOrder(s), count: 1 });
		}
		return [...m.values()].sort((a, b) => a.order - b.order);
	});

	// Distinct topics present on the shelf, alphabetical — the topic-filter chips.
	// Mirrors BooksShelf; chips come from each sermon's `topics` payload.
	const allTopics = $derived.by(() => {
		const m = new Map<string, string>();
		for (const s of sermons) for (const tc of s.topics ?? []) m.set(tc.slug, tc.title);
		return [...m]
			.map(([slug, title]) => ({ slug, title }))
			.sort((a, b) => a.title.localeCompare(b.title));
	});

	const filtered = $derived.by(() => {
		const q = filters.values.q.trim().toLowerCase();
		return sermons.filter((s) => {
			if (filters.values.book && s.scripture_book !== filters.values.book) return false;
			if (filters.values.len && lengthOf(s) !== filters.values.len) return false;
			if (filters.values.topic && !(s.topics ?? []).some((tc) => tc.slug === filters.values.topic))
				return false;
			if (!q) return true;
			return (
				s.title.toLowerCase().includes(q) ||
				s.author.name.toLowerCase().includes(q) ||
				s.scripture_ref.toLowerCase().includes(q)
			);
		});
	});

	// Narrowing, not arranging: a grouping or sort is not a filter.
	const filtering = $derived(
		!!(filters.values.q.trim() || filters.values.book || filters.values.len || filters.values.topic)
	);

	// The filters currently narrowing the shelf, each liftable on its own. The
	// query and the topic (shared with every shelf) come from filterChips; book
	// and length ride along too, so one row shows the whole state and every part
	// of it has a ×.
	const activeChips = $derived.by(() => {
		const c: FilterChip[] = [];
		const q = queryChip(filters);
		if (q) c.push(q);
		if (filters.values.book)
			c.push({ kind: 'book', label: filters.values.book, onRemove: () => (filters.values.book = '') });
		if (filters.values.len) {
			const b = filters.values.len as LengthBucket;
			c.push({ kind: 'len', label: t(LENGTH_LABEL[b]), onRemove: () => (filters.values.len = '') });
		}
		const topic = topicChip(filters, allTopics);
		if (topic) c.push(topic);
		return c;
	});

	// Clears what narrows the shelf, not how it is arranged — the grouping and
	// sort survive.
	function clearFilters() {
		filters.reset({ group: filters.values.group, sort: filters.values.sort });
	}

	// --- Arrangement -----------------------------------------------------------
	// "All sermons" — one continuous list in featured order, paged — is the
	// default (design review #28): grouped under 38 preachers the page ran
	// ~23,000px and opened on A. B. Simpson for the alphabet's sake. "By
	// preacher" keeps the author sections as a choice.
	//
	// URL state, not localStorage: the page is prerendered with the default, and
	// restoring a stored grouping or sort in onMount swapped the whole list after
	// the reader could see it on EVERY load (page-design: never restore a
	// layout-changing view after first paint). In the URL it only differs from
	// the default when the reader chose it — a Back or a shared link — as on
	// Biographies.
	type Group = 'preacher' | 'all';
	type Sort = 'shelf' | 'scripture' | 'title' | 'shortest';

	const group = $derived(filters.values.group as Group);
	const sort = $derived(filters.values.sort as Sort);
	/** The arrangement the page opens on — the only one the start row shows in. */
	const defaultView = $derived(!filtering && group === 'all' && sort === 'shelf');

	/** What the phone Filters sheet is narrowing by (FilterSheet's `count`). */
	const sheetCount = $derived((filters.values.book ? 1 : 0) + (filters.values.len ? 1 : 0));
	const SORTS: { v: Sort; k: string }[] = [
		{ v: 'shelf', k: 'common.sortShelf' },
		{ v: 'scripture', k: 'sermons.sortScripture' },
		{ v: 'title', k: 'common.sortTitle' },
		{ v: 'shortest', k: 'common.sortShortest' }
	];

	// How much the pinned controls bar covers (0 where it doesn't pin). The
	// filter row wraps to a second line on narrow screens, so the offset the
	// preacher anchors clear can't be assumed — it feeds `--pinned-offset`.
	let pinnedH = $state(0);

	// "Start with these": three hand-picked sermons for a newcomer, shown only
	// in the default view — a filter, sort or grouping is the reader saying
	// what they want, and in any other order the picks would repeat right
	// under the row.
	const starters = $derived(startWith(sermons));
	const startSlugs = $derived(new Set(starters.map((s) => s.slug)));

	const sorted = $derived.by(() => {
		// "Featured": the flat list lets the preachers take turns ($lib/sermonPicks);
		// grouped, it is the API's own order (preacher A–Z, then their sequence),
		// returned as-is rather than copied only to not sort it. While the row
		// shows them, its three wait for their preacher's last turn.
		if (sort === 'shelf')
			return group === 'all' ? featuredOrder(filtered, defaultView ? startSlugs : undefined) : filtered;
		const arr = [...filtered];
		switch (sort) {
			case 'scripture':
				// Canonical order, Genesis → Revelation; sermons on no stated book
				// sink to the end. Ties fall back to the title so the order is stable.
				return arr.sort((a, b) => bookOrder(a) - bookOrder(b) || a.title.localeCompare(b.title));
			case 'title':
				return arr.sort((a, b) => a.title.localeCompare(b.title));
			default:
				return arr.sort((a, b) => a.word_count - b.word_count);
		}
	});

	// Sermons by author, in the order `sorted` produced. null = one flat list.
	const groups = $derived.by(() => {
		if (group === 'all') return null;
		const map = new Map<string, { author: SermonSummary['author']; items: SermonSummary[] }>();
		for (const s of sorted) {
			const key = s.author.slug;
			if (!map.has(key)) map.set(key, { author: s.author, items: [] });
			map.get(key)!.items.push(s);
		}
		return [...map.values()];
	});

	// The flat list pages 24 at a time (page-design: a flat list over ~30 items).
	// Keyed to the filters and sort, so a new filter starts over at the first
	// page; the snapshot brings Back to where the reader was. Every sermon page
	// stays reachable for the prerender crawler without this list's full HTML:
	// each preacher's page (/authors/<slug>, from the seeded A–Z) lists all of
	// their sermons.
	const pages = pager(
		() => sorted,
		() => Object.values(filters.values).join('|')
	);
	export const snapshot = pagedSnapshot(() => (groups ? undefined : pages));

	// A preacher section opens on its first few sermons, so Spurgeon's eighteen
	// don't fill three screens before the next preacher. The rest stay in the
	// HTML (hidden, so every row is still a crawlable link) behind "Show N more".
	// A filter shows every match — it already narrowed the list on purpose.
	// "Show all" for one more sermon is noise, so a section only collapses when
	// it would hide at least two.
	const PREVIEW = 3;
	const expanded = new SvelteSet<string>();
	const collapsible = (n: number) => !filtering && n > PREVIEW + 1;
	function toggleSection(slug: string) {
		if (!expanded.has(slug)) {
			expanded.add(slug);
			return;
		}
		expanded.delete(slug);
		// Collapsing a long section pulls everything after it up by many screens;
		// bring its heading back into view so the reader stays where they were.
		const section = document.getElementById(`preacher-${slug}`);
		if (section && section.getBoundingClientRect().top < 0)
			section.scrollIntoView({ block: 'start' });
	}

	// --- Browse by Scripture (design review #21) ----------------------------------
	// The 66 books, each shaded by how many sermons on this shelf preach from
	// it; a cell sets the book filter. Built from `bookFacets`, so a cell's
	// count is the select's count. Null (no grid) where the shelf's references
	// don't resolve to enough books, and off the English shelf: the cells'
	// abbreviations and names are English ($lib/sermonCanon).
	const canon = $derived(getLang() === 'en' ? canonGrid(bookFacets) : null);
	/** A cell's link: this view (group, sort) narrowed to the book, so a new
	 *  tab opens what a plain click shows. Built from the filter VALUES, never
	 *  the query string, which the prerender may not read. */
	function bookHref(book: string) {
		// A placeholder origin: only the path and query are kept (SITE_URL can
		// be blank in the app build).
		const base = new URL(localizeHref('/sermons'), 'https://x.invalid');
		const u = writeFilters(base, { ...filters.values, book }, FILTER_DEFAULTS);
		return u.pathname + u.search;
	}
	// Phone only: the grid opens on a tap, so it doesn't stand between the start
	// row and the list. From sm it is always open (CSS — the prerendered HTML
	// is the same at every width, so nothing moves after first paint).
	let canonOpen = $state(false);
	const sermonsLabel = (n: number) => `${n} ${n === 1 ? t('common.sermonOne') : t('common.sermonMany')}`;

	/** A cell is a real link (shareable, opens in a new tab); a plain click
	 *  filters in place and brings the narrowed list into view, since the grid
	 *  and the rows above it give way to it. Focus goes there too: the link
	 *  the reader pressed is gone, and focus would otherwise fall to <body>. */
	function pickBook(e: MouseEvent, name: string) {
		if (!isPlainPrimaryClick(e)) return;
		e.preventDefault();
		filters.values.book = name;
		tick().then(() => {
			const results = document.getElementById('sermon-results');
			results?.focus({ preventScroll: true });
			results?.scrollIntoView({ block: 'start' });
		});
	}

	// A row states its writer only when no heading above it does.
	const showAuthor = $derived(groups === null);

	// Gated on ADVERTISED_LOCALES, not Paraglide's full `locales`: a locale that
	// is wired in the UI but has an empty catalog must not be advertised to
	// crawlers (see advertised-locales.ts). This page was claiming alternates
	// for draft locales while sitemap.xml, the detail pages and the footer all
	// correctly omitted them — two contradictory claims, with the wrong one on
	// the site's most-crawled pages.
	const hreflang = hreflangAll('/sermons');
</script>

<Seo
	title={`${t('sermons.metaTitle')} — Ochorus`}
	description={t('sermons.metaDescription')}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/sermons.png`}
	ogImageWidth={1200}
	ogImageHeight={630}
	structuredData={sermons.length ? [sermonsLd, crumbsLd] : [crumbsLd]}
/>

<!-- Shared by the inline row (sm up) and the phone sheet, so a control is
     defined once. -->
{#snippet bookSelect(cls: string)}
	<select bind:value={filters.values.book} aria-label={t('sermons.allBooks')} class="filter-field {cls}">
		<option value="">{t('sermons.allBooks')}</option>
		{#each bookFacets as b (b.name)}
			<option value={b.name}>{b.name} ({b.count})</option>
		{/each}
	</select>
{/snippet}
{#snippet groupSeg(cls: string, btnCls: string)}
	<div class="seg {cls}">
		<button
			class={btnCls}
			class:active={group === 'all'}
			onclick={() => (filters.values.group = 'all')}
			aria-pressed={group === 'all'}>{t('sermons.groupAll')}</button
		>
		<button
			class={btnCls}
			class:active={group === 'preacher'}
			onclick={() => (filters.values.group = 'preacher')}
			aria-pressed={group === 'preacher'}>{t('sermons.groupPreacher')}</button
		>
	</div>
{/snippet}

{#snippet clearFiltersAction()}
	<button class="btn btn-ghost" onclick={clearFilters}>{t('common.clearFilters')}</button>
{/snippet}

<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {pinnedH}px)">
	<PageHeader
		title={t('nav.sermons')}
		tagline={t('sermons.tagline')}
		meta={sermons.length ? sermonCounts : undefined}
	/>
	<!-- "N sermons · M preachers" — mirrors the Books shelf's count line, but names
	     the writers behind the sermons as PREACHERS, not "authors": it's the
	     accurate word (and the one this page's "By preacher" grouping already
	     uses), and it stops the sermon count from clashing with the distinct
	     "authors" figures on the home and Books pages. -->
	{#snippet sermonCounts()}
		{sermonsLabel(sermons.length)}
		<span class="sep">·</span>
		{preacherCount}
		{preacherCount === 1 ? t('common.preacherOne') : t('common.preacherMany')}
	{/snippet}

	<!-- Filter bar, pinned under the app nav so the filters come WITH you — 24
	     preacher sections run many screens. Below sm it is one line — search +
	     a Filters button whose sheet holds the rest (four stacked controls were
	     ~300px before the first sermon). `compact`: between sm and md the inline
	     row wraps too tall to pin, so there it scrolls away (FilterBar). -->
	<FilterBar bind:pinned={pinnedH} pin="compact" class="mb-8">
		<div class="filter-row">
			<input
				bind:value={filters.values.q}
				type="search"
				autocomplete="off"
				placeholder={t('sermons.filterPlaceholder')}
				aria-label={t('sermons.filterPlaceholder')}
				class="filter-field grow"
			/>
			<!-- Phone only: the same controls, as one-tap choices in a sheet. -->
			<FilterSheet
				count={sheetCount}
				shown={filtered.length}
				showLabel={t('sermons.showResults')}
				filtered={filtering}
				onClear={clearFilters}
			>
				{@render bookSelect('w-full')}

				<SheetChoices
					label={t('sermons.allLengths')}
					showLabel={false}
					options={[
						{ v: '', label: t('sermons.allLengths') },
						...LENGTH_BUCKETS.filter((b) => lengthFacets[b]).map((b) => ({
							v: b,
							label: t(LENGTH_LABEL[b]),
							count: lengthFacets[b]
						}))
					]}
					value={filters.values.len}
					onselect={(v) => (filters.values.len = v)}
				/>
				<SheetChoices
					label={t('common.sort')}
					options={SORTS.map((o) => ({ v: o.v, label: t(o.k) }))}
					value={sort}
					onselect={(v) => (filters.values.sort = v)}
				/>
				{@render groupSeg('w-full', 'flex-1')}
			</FilterSheet>
			<div class="hidden sm:contents">
				{@render bookSelect('')}

				<!-- How long it runs, in reading-time buckets (<10 / 10–30 / 30+ min) —
				     a length you can shop for, not just sort by. An empty bucket is
				     dropped, like the book scope above. -->
				<select bind:value={filters.values.len} aria-label={t('sermons.allLengths')} class="filter-field">
					<option value="">{t('sermons.allLengths')}</option>
					{#each LENGTH_BUCKETS as b (b)}
						{#if lengthFacets[b]}
							<option value={b}>{t(LENGTH_LABEL[b])} ({lengthFacets[b]})</option>
						{/if}
					{/each}
				</select>

				<select bind:value={filters.values.sort} class="filter-field" aria-label={t('common.sort')}>
					{#each SORTS as o (o.v)}
						<option value={o.v}>{t(o.k)}</option>
					{/each}
				</select>

				{@render groupSeg('', '')}
			</div>
		</div>
	</FilterBar>

	<!-- One sermon to start with, for a reader who doesn't yet know whom to
	     read — the same weekly pick as the home page, hidden while the reader is
	     filtering (page-design: a shelf's secondary section). BELOW the filter
	     bar, not above it as the anatomy's order has it: hiding it on the first
	     keystroke would otherwise yank the search box out from under the
	     reader's typing. `reserve` holds its height until the pick lands. -->
	{#if !filtering && !loadError && sermons.length}
		<div class="mb-8">
			<SermonOfTheDay embedded reserve />
		</div>
	{/if}

	<!-- Topic filter — a chip row for taxonomy, under the controls. Mirrors the
	     Books shelf; the shared component reuses the Books labels (the same "All
	     topics" / "Filter by topic") and shows only when the shelf spans >1 topic. -->
	<TopicFilterRow
		topics={allTopics}
		selected={filters.values.topic}
		onSelect={(topic) => (filters.values.topic = topic)}
	/>

	<!-- Where a Browse by Scripture pick lands the reader: the top of the results. -->
	<div
		id="sermon-results"
		tabindex="-1"
		class="outline-none"
		style="scroll-margin-top: calc(var(--pinned-offset, 5rem) + 0.5rem)"
	></div>

	<!-- One clear affordance, on the FilterSummary — same as Books and
	     Biographies. (The bespoke in-row "Clear" and sermons.clear are retired.) -->
	{#if filtering}
		<FilterSummary
			shown={filtered.length}
			total={sermons.length}
			template={t('sermons.showing')}
			onClear={clearFilters}
			chips={activeChips}
			class="mb-6"
		/>
	{/if}

	<!-- Three to start with (design #28): large faces, the title, preacher ·
	     minutes — a way in for a reader who doesn't yet know whom to read. -->
	{#if defaultView && !loadError && starters.length}
		<section class="mb-10" aria-labelledby="start-with">
			<h2 id="start-with" class="section-label mb-4">{t('sermons.startWith')}</h2>
			<ul class="start-with">
				{#each starters as s (s.slug)}
					<li>
						<a href={localizeHref(`/sermons/${s.slug}`)} class="start-card">
							<Portrait
								slug={s.author.slug}
								name={s.author.name}
								url={s.author.photo_url}
								px={72}
								tone="color"
								decorative
								class="start-face"
							/>
							<span class="min-w-0">
								<span class="start-title">{s.title}</span>
								<span class="block text-small text-muted"
									>{s.author.name}{' '}<span class="sep" aria-hidden="true">·</span>{' '}<span
										class="whitespace-nowrap">{readingTime(s.word_count)}</span
									></span
								>
							</span>
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	<!-- Browse by Scripture (design #21): every book of the Bible, shaded by how
	     many sermons here preach from it (the shared .heat-N wash, the count
	     printed in the cell and in its name, so the shade is never the only
	     signal). An empty book is muted text, not a link. A secondary section:
	     hidden while filtering — the chosen book shows as a chip instead. -->
	{#if canon && !filtering && !loadError}
		<section class="mb-10" class:canon-open={canonOpen} aria-labelledby="by-scripture">
			<h2 id="by-scripture" class="section-label mb-4">
				<button
					type="button"
					class="canon-toggle"
					aria-expanded={canonOpen}
					aria-controls="canon-body"
					onclick={() => (canonOpen = !canonOpen)}
				>
					{t('sermons.byScripture')}
					<svg class="chev" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"
						><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.75" /></svg
					>
				</button>
				<span class="hidden sm:inline">{t('sermons.byScripture')}</span>
			</h2>
			<div id="canon-body" class="canon-body">
				{#each [canon.old, canon.new] as cells, i (i)}
					<h3 class="eyebrow text-muted mb-2" class:mt-4={i > 0}>
						{t(i ? 'scripture.newTestament' : 'scripture.oldTestament')}
					</h3>
					<ul class="canon">
						{#each cells as c (c.name)}
							<!-- The visible label is the abbreviation (and count); the
							     accessible name is the full book and "N sermons". -->
							{#snippet label()}<span aria-hidden="true" class="canon-abbr">{c.abbr}</span
								>{#if c.count}<span aria-hidden="true" class="canon-count">{c.count}</span
									>{/if}<span class="sr-only">{c.name}, {sermonsLabel(c.count)}</span
								>{/snippet}
							<li>
								{#if c.count}
									<a
										href={bookHref(c.name)}
										rel="nofollow"
										class="canon-cell heat-{c.heat}"
										onclick={(e) => pickBook(e, c.name)}>{@render label()}</a
									>
								{:else}
									<span class="canon-cell canon-empty">{@render label()}</span>
								{/if}
							</li>
						{/each}
					</ul>
				{/each}
			</div>
		</section>
	{/if}

	<!-- One sermon per line, a plain list (design #8): the title, one meta line
	     (preacher · passage · length) and the first line of the "In brief",
	     hairlines between. The whole row opens the sermon. -->
	{#snippet sermonList(items: SermonSummary[], limit = Infinity, id?: string)}
		<div {id} class="sermon-list">
			{#each items as sermon, i (sermon.slug)}
				<div class="contents" hidden={i >= limit}>
					<SermonCard {sermon} {showAuthor} />
				</div>
			{/each}
		</div>
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if sorted.length === 0}
		<EmptyState
			art={filtering ? 'search' : 'book'}
			message={filtering ? t('sermons.noMatches') : t('sermons.empty')}
			action={filtering ? clearFiltersAction : undefined}
		/>
	{:else if groups}
		<!-- Jump to a preacher — the sections are long, so they need a way in
		     that isn't scrolling: the shared faces strip (Books uses it too). -->
		{#if groups.length > 1}
			<AuthorJumpStrip
				class="mb-8"
				label={t('sermons.jumpPreacher')}
				href={(slug) => `#preacher-${slug}`}
				writers={groups.map((g) => ({ ...g.author, count: g.items.length }))}
			/>
		{/if}
		{#each groups as g (g.author.slug)}
			{@const a = g.author}
			{@const lifespan = formatLifespan(a.birth_year, a.death_year, t('common.bornPrefix'))}
			{@const canCollapse = collapsible(g.items.length)}
			{@const collapsed = canCollapse && !expanded.has(a.slug)}
			<section
				id="preacher-{a.slug}"
				class="mb-10"
				style="scroll-margin-top: calc(var(--pinned-offset, 5rem) + 0.5rem)"
			>
				<!-- Who the preacher was, before what they preached: their years and
				     one line on who they were, so a newcomer can tell Chrysostom's
				     Antioch from Tozer's Chicago. The line is the tagline, written for
				     this spot (a bio often opens "Name (1897–1963) was…", repeating
				     the heading); a language without one falls back to the bio's
				     opening. The name links to the full life. -->
				<GroupHeading
					name={a.name}
					href={localizeHref(authorPath(a.slug))}
					portraitUrl={a.photo_url}
					portraitPosition={portraitPosition(a.slug)}
					blurb={a.tagline || a.bio}
				>
					<!-- Years, then the count as words: a bare count after a
					     lifespan read as one figure ("1843–1919 15"). -->
					{#snippet detail()}
						<span class="text-small font-normal count"
							>{#if lifespan}{lifespan}<span class="sep">{' · '}</span>{/if}{sermonsLabel(g.items.length)}</span
						>
					{/snippet}
				</GroupHeading>
				{@render sermonList(g.items, collapsed ? PREVIEW : Infinity, `preacher-list-${a.slug}`)}
				{#if canCollapse}
					<button
						type="button"
						class="btn btn-ghost btn-sm mt-3"
						aria-expanded={!collapsed}
						aria-controls="preacher-list-{a.slug}"
						onclick={() => toggleSection(a.slug)}
					>
						{collapsed
							? t('bios.showMore').replace('%n%', String(g.items.length - PREVIEW))
							: t('search.showLess')}
					</button>
				{/if}
			</section>
		{/each}
	{:else}
		{@render sermonList(pages.visible)}
		<ShowMore pager={pages} />
	{/if}
	<!-- The leader's way on, at the end of the shelf rather than in its head
	     (design review #4): a reader came for the sermons first. Only under
	     real results — never as the answer to an empty filter. -->
	{#if !loadError && sorted.length}
		<ForPromo place="sermons-shelf" class="mt-8" />
	{/if}
</div>

<style>
	/* Three across from sm up, a face over its title; a phone stacks them as
	   rows, the face beside the words, so three fit one screen. */
	.start-with {
		display: grid;
		gap: 1.25rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.start-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		color: var(--text);
		text-decoration: none;
	}
	.start-card :global(.start-face) {
		flex: none;
		width: 4rem;
		height: 4rem;
	}
	.start-title {
		display: block;
		margin-block-end: 0.15rem;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		line-height: 1.3;
	}
	.start-card:hover .start-title,
	.start-card:focus-visible .start-title {
		color: var(--accent);
		text-decoration: underline;
		text-underline-offset: 0.2em;
	}

	/* The canon grid: as many ~3.5rem cells across as fit, each a 44px target. */
	.canon {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(3.5rem, 1fr));
		gap: 0.3rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.canon-cell {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 2.75rem;
		padding: 0.2rem 0.25rem;
		border-radius: var(--radius-sm);
		color: var(--text);
		font-size: var(--fs-small);
		line-height: 1.15;
		text-align: center;
		text-decoration: none;
		white-space: nowrap;
	}
	.canon-abbr {
		font-weight: 600;
	}
	.canon-count {
		font-size: var(--fs-micro);
		font-variant-numeric: tabular-nums;
	}
	/* The top shade is the solid accent: its ink needs this specificity to beat
	   the body colour above (as ScriptureChapterChips does). */
	.canon-cell.heat-4 {
		color: var(--accent-contrast);
	}
	a.canon-cell:hover,
	a.canon-cell:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 1px;
	}
	/* No sermons: the name in muted ink on a hairline, nothing to tap. */
	.canon-empty {
		color: var(--muted);
		box-shadow: inset 0 0 0 1px var(--border);
	}
	/* A phone's way to open the grid; from sm the plain label beside it shows
	   instead (this scoped display would beat a `sm:hidden` utility). */
	.canon-toggle {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		font: inherit;
		letter-spacing: inherit;
		text-transform: inherit;
		color: inherit;
	}
	.canon-toggle .chev {
		transition: transform 0.15s ease;
	}
	.canon-open .canon-toggle .chev {
		transform: rotate(180deg);
	}
	/* Collapsed on a phone until the toggle opens it; always open from sm. */
	.canon-body {
		display: none;
	}
	.canon-open .canon-body {
		display: block;
	}
	@media (min-width: 40rem) {
		.canon-body {
			display: block;
		}
		.canon-toggle {
			display: none;
		}
		.start-with {
			grid-template-columns: repeat(3, minmax(0, 1fr));
			gap: 1.5rem;
		}
		.start-card {
			flex-direction: column;
			align-items: flex-start;
			gap: 0.75rem;
		}
		.start-card :global(.start-face) {
			width: 4.5rem;
			height: 4.5rem;
		}
	}
</style>
