<script lang="ts">
	import { onMount } from 'svelte';
	import { authorPath } from '$lib/originals';
	import type { SermonSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { collectionPage, breadcrumbLd, hreflangAll } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { readJSON, writeJSON } from '$lib/persisted';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';
	import TopicFilterRow from '$lib/components/TopicFilterRow.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import { queryChip, topicChip, type FilterChip } from '$lib/filterChips';
	import { urlFilters } from '$lib/urlFilters.svelte';
	import { page } from '$app/stores';
	import { portraitPosition } from '$lib/portraits';
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
		const map = new Map<
			string,
			{ name: string; slug: string; photo_url: string; items: SermonSummary[] }
		>();
		for (const s of sorted) {
			const key = s.author.slug;
			if (!map.has(key))
				map.set(key, { name: s.author.name, slug: key, photo_url: s.author.photo_url, items: [] });
			map.get(key)!.items.push(s);
		}
		return [...map.values()];
	});

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

	<!-- Filter bar: free text + which book of the Bible the sermon expounds.
	     Pinned under the app nav (itself sticky, hence the --appnav-h offset) so
	     the filters come WITH you — with a brief under every row the shelf runs
	     dozens of screens. Its height is measured, not assumed: the row wraps on
	     narrow screens, and the preacher sections below pin under whatever it
	     currently is. Same recipe as Biographies (page-design B6/L3), EXCEPT
	     below md: there the wrapped row would pin ~40% of the phone viewport, so
	     it scrolls away like the Books filters instead. The sticky rule and the
	     matching --pinned-offset (which drops --controls-h when the bar isn't
	     pinned) live in the <style> block below. (Biographies still pins.) -->
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
		<select bind:value={filters.values.book} aria-label={t('sermons.allBooks')} class="filter-field">
			<option value="">{t('sermons.allBooks')}</option>
			{#each bookFacets as b (b.name)}
				<option value={b.name}>{b.name} ({b.count})</option>
			{/each}
		</select>

		<!-- How long it runs, in reading-time buckets (<10 / 10–30 / 30+ min) — a
		     length you can shop for, not just sort by. A bucket with nothing in it
		     is dropped, like the book scope above. -->
		<select bind:value={filters.values.len} aria-label={t('sermons.allLengths')} class="filter-field">
			<option value="">{t('sermons.allLengths')}</option>
			{#each LENGTH_BUCKETS as b (b)}
				{#if lengthFacets[b]}
					<option value={b}>{t(LENGTH_LABEL[b])} ({lengthFacets[b]})</option>
				{/if}
			{/each}
		</select>

		<select bind:value={sort} onchange={save} class="filter-field" aria-label={t('common.sort')}>
			<option value="shelf">{t('common.sortShelf')}</option>
			<option value="scripture">{t('sermons.sortScripture')}</option>
			<option value="title">{t('common.sortTitle')}</option>
			<option value="shortest">{t('common.sortShortest')}</option>
		</select>

		<div class="seg">
			<button
				class:active={group === 'preacher'}
				onclick={() => setGroup('preacher')}
				aria-pressed={group === 'preacher'}>{t('sermons.groupPreacher')}</button
			>
			<button
				class:active={group === 'all'}
				onclick={() => setGroup('all')}
				aria-pressed={group === 'all'}>{t('sermons.groupAll')}</button
			>
		</div>

	</div>
	</div>

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
	{#snippet sermonList(items: SermonSummary[])}
		<div class="flex flex-col gap-3">
			{#each items as sermon (sermon.slug)}
				<SermonCard {sermon} {showAuthor} variant="row" />
			{/each}
		</div>
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if sorted.length === 0}
		<EmptyState message={filtering ? t('sermons.noMatches') : t('sermons.empty')} />
	{:else if groups}
		<!-- Jump to a writer — with a brief under every sermon the sections are
		     long, so they need a way in that isn't scrolling. Same rail the Books
		     shelf uses. -->
		{#if groups.length > 1}
			<nav
				class="chip-scroller mb-8"
				aria-label={t('sermons.jumpPreacher')}
			>
				<span class="eyebrow text-muted me-1">{t('sermons.jumpPreacher')}</span>
				{#each groups as g (g.slug)}
					<a href="#preacher-{g.slug}" class="tag">{g.name}</a>
				{/each}
			</nav>
		{/if}
		{#each groups as g (g.slug)}
			<section
				id="preacher-{g.slug}"
				class="mb-10"
				style="scroll-margin-top: calc(var(--pinned-offset, 5rem) + 0.5rem)"
			>
				<GroupHeading
					name={g.name}
					href={localizeHref(authorPath(g.slug))}
					portraitUrl={g.photo_url}
					portraitPosition={portraitPosition(g.slug)}
					count={g.items.length}
				/>
				{@render sermonList(g.items)}
			</section>
		{/each}
	{:else}
		{@render sermonList(sorted)}
	{/if}
</div>

<style>
	/* Below md the filter row scrolls away with the page (see the comment on the
	   .sermon-filter element): a phone can't afford a pinned block that wraps to
	   ~40% of the viewport, and the Books shelf's filters already behave this
	   way. So the preacher anchors only need to clear the sticky app nav. */
	.sermon-shell {
		--pinned-offset: var(--appnav-h, 0px);
	}
	@media (min-width: 768px) {
		/* Tablet/desktop: the row fits on a line or two, so it pins under the nav
		   and the anchors clear both the nav and the measured filter height. */
		.sermon-shell {
			--pinned-offset: calc(var(--appnav-h, 0px) + var(--controls-h, 0px));
		}
		.sermon-filter {
			position: sticky;
			top: var(--appnav-h, 0px);
		}
	}
</style>
