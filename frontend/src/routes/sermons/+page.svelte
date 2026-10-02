<script lang="ts">
	import { onMount } from 'svelte';
	import { authorPath } from '$lib/originals';
	import { formatLifespan, type SermonSummary } from '$lib/library-public';
	import { SvelteSet } from 'svelte/reactivity';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { initials } from '$lib/strings';
	import { SITE_URL } from '$lib/config';
	import { collectionPage, breadcrumbLd, hreflangAll } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { readJSON, writeJSON } from '$lib/persisted';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import SermonOfTheWeek from '$lib/components/SermonOfTheWeek.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';
	import TopicFilterRow from '$lib/components/TopicFilterRow.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import FilterSheet from '$lib/components/FilterSheet.svelte';
	import SheetChoices from '$lib/components/SheetChoices.svelte';
	import { queryChip, topicChip, type FilterChip } from '$lib/filterChips';
	import { urlFilters } from '$lib/urlFilters.svelte';
	import { page } from '$app/stores';
	import { portraitPosition, portraitSrcset } from '$lib/portraits';
	import { readingMinutes } from '$lib/reading';
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
	// $lib/urlFilters — the same helper Books and Biographies use. Grouping and
	// sort stay in localStorage below: they describe the reader, not the shelf.
	const filters = urlFilters({
		defaults: { q: '', book: '', len: '', topic: '' },
		// `len` is an enum — an off-list value in the URL falls back to "any".
		// `topic` is a free-text slug (like `book`), so it isn't listed here.
		allowed: { len: LENGTH_BUCKETS },
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

	const filtering = $derived(filters.active);

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
	// sort are the reader's own preference (localStorage) and survive.
	function clearFilters() {
		filters.reset();
	}

	// --- Arrangement (persisted per device, mirroring the Books shelf) ----------
	// "By preacher" keeps the author sections the shelf was built around; "All
	// sermons" drops them for one continuous list.
	type Group = 'preacher' | 'all';
	type Sort = 'shelf' | 'scripture' | 'title' | 'shortest';
	const PREFS_KEY = 'ochorus:sermons-view';

	let group = $state<Group>('preacher');
	let sort = $state<Sort>('shelf');

	/** What the phone Filters sheet is narrowing by (FilterSheet's `count`). */
	const sheetCount = $derived((filters.values.book ? 1 : 0) + (filters.values.len ? 1 : 0));
	const SORTS: { v: Sort; k: string }[] = [
		{ v: 'shelf', k: 'common.sortShelf' },
		{ v: 'scripture', k: 'sermons.sortScripture' },
		{ v: 'title', k: 'common.sortTitle' },
		{ v: 'shortest', k: 'common.sortShortest' }
	];

	// Measured height of the pinned controls bar. The filter row wraps to a
	// second line on narrow screens, so the offset the preacher anchors clear
	// can't be assumed — it feeds `--pinned-offset`, mirroring Biographies.
	let controlsH = $state(0);

	// Hydrated after mount, not during load: the page is prerendered, so reading
	// localStorage while rendering would desync the static HTML from the client.
	onMount(() => {
		const p = readJSON<{ group?: Group; sort?: Sort }>(PREFS_KEY, {});
		if (p.group) group = p.group;
		if (p.sort) sort = p.sort;
	});
	const save = () => writeJSON(PREFS_KEY, { group, sort });
	const setGroup = (g: Group) => ((group = g), save());

	const sorted = $derived.by(() => {
		// Shelf order is the API's own (author, then their sequence) — return the
		// filter's array as-is rather than copying it only to not sort it.
		if (sort === 'shelf') return filtered;
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
			class:active={group === 'preacher'}
			onclick={() => setGroup('preacher')}
			aria-pressed={group === 'preacher'}>{t('sermons.groupPreacher')}</button
		>
		<button
			class={btnCls}
			class:active={group === 'all'}
			onclick={() => setGroup('all')}
			aria-pressed={group === 'all'}>{t('sermons.groupAll')}</button
		>
	</div>
{/snippet}

<div class="page-col px-5 py-10 sermon-shell" style="--controls-h: {controlsH}px">
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
		{sermons.length}
		{sermons.length === 1 ? t('common.sermonOne') : t('common.sermonMany')}
		<span class="opacity-50">·</span>
		{preacherCount}
		{preacherCount === 1 ? t('common.preacherOne') : t('common.preacherMany')}
	{/snippet}

	<!-- Filter bar, pinned under the app nav (itself sticky, hence the
	     --appnav-h offset) so the filters come WITH you — 24 preacher sections
	     run many screens. Its height is measured: the
	     preacher sections pin under whatever it currently is. Same recipe as
	     Biographies (page-design B6/L3).
	     Below sm it is one line — search + a Filters button whose sheet holds
	     the rest (four stacked controls were ~300px before the first sermon) —
	     and pins. From sm the controls sit inline; between sm and md that row
	     wraps too tall to pin, so there it scrolls away. The sticky rules and the
	     matching --pinned-offset live in the <style> block below. -->
	<div
		bind:clientHeight={controlsH}
		class="sermon-filter z-20 -mx-5 mb-8 border-b border-border bg-bg px-5 pb-2.5 pt-3"
	>
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
					onselect={(v) => ((sort = v), save())}
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

				<select bind:value={sort} onchange={save} class="filter-field" aria-label={t('common.sort')}>
					{#each SORTS as o (o.v)}
						<option value={o.v}>{t(o.k)}</option>
					{/each}
				</select>

				{@render groupSeg('', '')}
			</div>
		</div>
	</div>

	<!-- One sermon to start with, for a reader who doesn't yet know whom to
	     read — the same weekly pick as the home page, hidden while the reader is
	     filtering (page-design: a shelf's secondary section). BELOW the filter
	     bar, not above it as the anatomy's order has it: hiding it on the first
	     keystroke would otherwise yank the search box out from under the
	     reader's typing. `reserve` holds its height until the pick lands. -->
	{#if !filtering && !loadError && sermons.length}
		<div class="mb-8">
			<SermonOfTheWeek embedded reserve />
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

	<!-- One sermon per line: title, the passage it expounds, the "In brief", and
	     how long it runs — enough to decide whether to read or listen without
	     opening it. A tile can't carry a 300–400 character brief without becoming
	     mostly text, and prose set across a 76rem page is unreadable, so the row
	     gives the brief a real measure and the meta a column of its own. -->
	{#snippet sermonList(items: SermonSummary[], limit = Infinity, id?: string)}
		<div {id} class="flex flex-col gap-3">
			{#each items as sermon, i (sermon.slug)}
				<div class="contents" hidden={i >= limit}>
					<SermonCard {sermon} {showAuthor} variant="row" />
				</div>
			{/each}
		</div>
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if sorted.length === 0}
		<EmptyState message={filtering ? t('sermons.noMatches') : t('sermons.empty')} />
	{:else if groups}
		<!-- Jump to a writer — the sections are long, so they need a way in that
		     isn't scrolling. One scrolling row of faces, each with its count: it
		     holds its height however many preachers join (the chip wall it
		     replaced ran to three rows at 24), and a face is found faster than a
		     name. In section order, so the strip reads like the page below it. -->
		{#if groups.length > 1}
			<nav class="cover-rail mb-8 flex gap-1 pb-1" aria-label={t('sermons.jumpPreacher')}>
				{#each groups as g (g.author.slug)}
					<a href="#preacher-{g.author.slug}" class="preacher-jump">
						<span class="preacher-face" aria-hidden="true">
							{#if g.author.photo_url}
								{@const source = {
									src: g.author.photo_url,
									srcset: portraitSrcset(g.author.photo_url)
								}}
								<img
									src={source.src}
									srcset={source.srcset}
									use:hydrateSrc={source}
									sizes="44px"
									alt=""
									loading="lazy"
									width="44"
									height="44"
									style="object-position: {portraitPosition(g.author.slug)}"
								/>
							{:else}
								{initials(g.author.name)}
							{/if}
						</span>
						<span class="preacher-name">{g.author.name}</span>
						<span class="count text-micro">{g.items.length}</span>
					</a>
				{/each}
			</nav>
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
							>{#if lifespan}{lifespan}<span class="opacity-50">{' · '}</span>{/if}{g.items.length}
							{g.items.length === 1 ? t('common.sermonOne') : t('common.sermonMany')}</span
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
		{@render sermonList(sorted)}
	{/if}
</div>

<style>
	/* The filter bar pins below sm (one line: search + Filters) and from md
	   (the inline row fits a line or two); between sm and md the inline row
	   wraps too tall to pin, so it scrolls away and the preacher anchors only
	   clear the app nav. */
	.sermon-shell {
		--pinned-offset: calc(var(--appnav-h, 0px) + var(--controls-h, 0px));
	}
	.sermon-filter {
		position: sticky;
		top: var(--appnav-h, 0px);
	}
	@media (min-width: 640px) and (max-width: 767.98px) {
		.sermon-shell {
			--pinned-offset: var(--appnav-h, 0px);
		}
		.sermon-filter {
			position: static;
		}
	}
	/* One face in the preacher strip (the strip itself is the shared .cover-rail):
	   portrait or initials over the name and count. */
	.preacher-jump {
		flex: none;
		width: 5.5rem;
		display: grid;
		justify-items: center;
		align-content: start;
		gap: 0.2rem;
		padding: 0.4rem 0.25rem;
		border-radius: var(--radius-card);
		text-align: center;
		color: var(--text);
		text-decoration: none;
	}
	.preacher-jump:hover {
		background: var(--surface-2);
	}
	.preacher-jump:hover .preacher-face {
		border-color: var(--accent);
	}
	.preacher-jump:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 1px;
	}
	.preacher-face {
		width: 2.75rem;
		height: 2.75rem;
		border-radius: 9999px;
		overflow: hidden;
		display: grid;
		place-items: center;
		border: 2px solid var(--border);
		background: var(--surface-2);
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--muted);
		transition: border-color var(--duration-fast);
	}
	.preacher-face img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	.preacher-name {
		font-size: var(--fs-small);
		line-height: 1.2;
	}
</style>
