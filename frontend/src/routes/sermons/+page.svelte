<script lang="ts">
	import { onMount } from 'svelte';
	import type { SermonSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { itemList, hreflangAll } from '$lib/seo';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { readJSON, writeJSON } from '$lib/persisted';
	import SermonOfTheWeek from '$lib/components/SermonOfTheWeek.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import CatalogLanguageNudge from '$lib/components/CatalogLanguageNudge.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';
	import { portraitPosition } from '$lib/portraits';

	const t = i18n.t;

	let { data } = $props();
	const sermons = $derived<SermonSummary[]>(data.sermons);
	const loadError = $derived<boolean>(data.loadError);

	// schema.org ItemList of the sermon shelf — an ordered roster for crawlers.
	const sermonsLd = $derived(
		itemList(
			t('nav.sermons'),
			sermons.map((s) => ({ name: s.title, url: localizeHref(`/sermons/${s.slug}`) }))
		)
	);

	// --- Filters ----------------------------------------------------------------
	let queryText = $state('');
	let bibleBook = $state('');

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

	const filtered = $derived.by(() => {
		const q = queryText.trim().toLowerCase();
		return sermons.filter((s) => {
			if (bibleBook && s.scripture_book !== bibleBook) return false;
			if (!q) return true;
			return (
				s.title.toLowerCase().includes(q) ||
				s.author.name.toLowerCase().includes(q) ||
				s.scripture_ref.toLowerCase().includes(q)
			);
		});
	});

	const filtering = $derived(queryText.trim() !== '' || bibleBook !== '');
	// Clears what narrows the shelf, not how it is arranged — the grouping and
	// sort are the reader's own preference and survive.
	function clearFilters() {
		queryText = '';
		bibleBook = '';
	}

	// --- Arrangement (persisted per device, mirroring the Books shelf) ----------
	// "By preacher" keeps the author sections the shelf was built around; "All
	// sermons" drops them for one continuous list.
	type Group = 'preacher' | 'all';
	type Sort = 'shelf' | 'scripture' | 'title' | 'shortest';
	const PREFS_KEY = 'ochorus:sermons-view';

	let group = $state<Group>('preacher');
	let sort = $state<Sort>('shelf');

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

<svelte:head>
	<title>{t('nav.sermons')} — Ochorus</title>
	<meta name="description" content={t('sermons.metaDescription')} />
	<link rel="canonical" href="{SITE_URL}{localizeHref('/sermons')}" />
	{#each hreflang.alternates as a (a.loc)}
		<link rel="alternate" hreflang={a.loc} href={a.href} />
	{/each}
	<link rel="alternate" hreflang="x-default" href={hreflang.xDefault} />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="{t('nav.sermons')} — Ochorus" />
	<meta property="og:description" content={t('sermons.metaDescription')} />
	<meta property="og:url" content="{SITE_URL}{localizeHref('/sermons')}" />
	<meta property="og:image" content="{SITE_URL}/og/sermons.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{#if sermons.length}{@html sermonsLd}{/if}
</svelte:head>

<div class="page-col px-5 py-10">
	<PageHeader eyebrow={t('nav.sermons')} title={t('sermons.title')} tagline={t('sermons.tagline')} />

	<CatalogLanguageNudge kind="sermons" localizedCount={sermons.length} />

	<!-- A weekly pick to open the page on a focal point rather than a cold list.
	     Hidden once the reader is actively filtering (they've stated intent). -->
	{#if !filtering}
		<div class="mb-8">
			<SermonOfTheWeek embedded />
		</div>
	{/if}

	<!-- Filter bar: free text + which book of the Bible the sermon expounds. -->
	<div class="filter-row mb-8">
		<input
			bind:value={queryText}
			type="search"
			autocomplete="off"
			placeholder={t('sermons.filterPlaceholder')}
			aria-label={t('sermons.filterPlaceholder')}
			class="filter-field grow"
		/>
		<select bind:value={bibleBook} aria-label={t('sermons.allBooks')} class="filter-field">
			<option value="">{t('sermons.allBooks')}</option>
			{#each bookFacets as b (b.name)}
				<option value={b.name}>{b.name} ({b.count})</option>
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

		{#if filtering}
			<button class="btn btn-ghost py-2" onclick={clearFilters}>{t('sermons.clear')}</button>
		{/if}
	</div>

	<!-- No onClear here: this shelf's controls bar already carries a Clear,
	     right above. Two of them side by side is one too many. -->
	{#if filtering}
		<FilterSummary
			shown={filtered.length}
			total={sermons.length}
			template={t('sermons.showing')}
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
			<nav class="mb-8 flex flex-wrap gap-1.5" aria-label={t('sermons.groupPreacher')}>
				{#each groups as g (g.slug)}
					<a href="#preacher-{g.slug}" class="chip hover:no-underline">{g.name}</a>
				{/each}
			</nav>
		{/if}
		{#each groups as g (g.slug)}
			<section id="preacher-{g.slug}" class="mb-10 scroll-mt-20">
				<h2 class="mb-4 flex items-center gap-2.5 text-h3 text-muted">
					{#if g.photo_url}
						<img
							src={g.photo_url}
							alt=""
							loading="lazy"
							width="32"
							height="32"
							class="h-8 w-8 shrink-0 rounded-full border border-border object-cover"
							style="object-position: {portraitPosition(g.slug)}"
						/>
					{/if}
					<a href={localizeHref(`/authors/${g.slug}`)} class="text-text hover:underline">{g.name}</a>
					<span class="text-small font-normal opacity-60">{g.items.length}</span>
				</h2>
				{@render sermonList(g.items)}
			</section>
		{/each}
	{:else}
		{@render sermonList(sorted)}
	{/if}
</div>
