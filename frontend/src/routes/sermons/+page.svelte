<script lang="ts">
	import { onMount } from 'svelte';
	import type { SermonSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { itemList } from '$lib/seo';
	import { localizeHref } from '$lib/href';
	import { locales } from '$lib/paraglide/runtime';
	import { i18n } from '$lib/i18n.svelte';
	import { readingTime } from '$lib/reading';
	import { readJSON, writeJSON } from '$lib/persisted';
	import SermonOfTheWeek from '$lib/components/SermonOfTheWeek.svelte';
	import CatalogLanguageNudge from '$lib/components/CatalogLanguageNudge.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import ShelfCard from '$lib/components/ShelfCard.svelte';
	import { hueForBirthYear } from '$lib/eras';

	const t = i18n.t;

	let { data } = $props();
	const sermons = $derived<SermonSummary[]>(data.sermons);

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

	// Books of the Bible present on this shelf, in canonical order, with counts.
	const bookFacets = $derived.by(() => {
		const m = new Map<string, { name: string; order: number; count: number }>();
		for (const s of sermons) {
			if (!s.scripture_book) continue;
			const e = m.get(s.scripture_book);
			if (e) e.count++;
			else m.set(s.scripture_book, { name: s.scripture_book, order: s.scripture_book_order ?? 999, count: 1 });
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

	// --- Arrangement (persisted per device, mirroring the Books shelf) ----------
	// One card per sermon means the grid can be arranged rather than only
	// grouped: "By preacher" keeps the author sections the shelf was built
	// around, "All sermons" drops them for one continuous grid.
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
		const arr = [...filtered];
		switch (sort) {
			case 'scripture':
				// Canonical order, Genesis → Revelation; sermons on no stated book
				// sink to the end. Ties fall back to the title so the order is stable.
				return arr.sort(
					(a, b) =>
						(a.scripture_book_order ?? 999) - (b.scripture_book_order ?? 999) ||
						a.title.localeCompare(b.title)
				);
			case 'title':
				return arr.sort((a, b) => a.title.localeCompare(b.title));
			case 'shortest':
				return arr.sort((a, b) => a.word_count - b.word_count);
			default:
				return arr; // the API's shelf order (author, then their own sequence)
		}
	});

	// Sermons by author, in the order `sorted` produced. null = one flat grid.
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

	/** Year a sermon was preached, for the card footer; '' when undated. */
	const preachedYear = (s: SermonSummary) => s.preached_on?.slice(0, 4) ?? '';
</script>

<svelte:head>
	<title>{t('nav.sermons')} — Ochorus</title>
	<meta name="description" content={t('sermons.metaDescription')} />
	<link rel="canonical" href="{SITE_URL}{localizeHref('/sermons')}" />
	{#each locales as loc (loc)}
		<link
			rel="alternate"
			hreflang={loc}
			href="{SITE_URL}{localizeHref('/sermons', { locale: loc })}"
		/>
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_URL}/sermons" />
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

		<select bind:value={sort} onchange={save} class="filter-field" aria-label={t('sermons.sort')}>
			<option value="shelf">{t('sermons.sortShelf')}</option>
			<option value="scripture">{t('sermons.sortScripture')}</option>
			<option value="title">{t('sermons.sortTitle')}</option>
			<option value="shortest">{t('sermons.sortShortest')}</option>
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
			<button
				class="btn btn-ghost !py-2"
				onclick={() => {
					queryText = '';
					bibleBook = '';
				}}>{t('sermons.clear')}</button
			>
		{/if}
	</div>

	{#if filtering}
		<p class="mb-6 text-small text-muted" aria-live="polite">
			{filtered.length}
			{filtered.length === 1 ? t('sermons.matchOne') : t('sermons.matches')}
		</p>
	{/if}

	<!-- One sermon, one card.
	     The shelf used to be one card PER WRITER holding that writer's sermons as
	     a list, which made the cards as uneven as the corpus: 1 sermon for Hudson
	     Taylor against 13 for Spurgeon, so a 168px card sat beside a 1073px one
	     and the grid bottomed out ragged. Sizing them to match was worse (700px
	     of dead space under the short ones), so the ragged edge was the price of
	     the grouping.
	     A card per sermon removes the choice: every card holds ONE title, so
	     items-stretch + .shelf-card{height:100%} + the mt-auto footer level the
	     bottoms the same way Topics, Plans and Books do. The grouping survives as
	     section headings above each grid (below), which level per section. -->
	{#snippet sermonCard(sermon: SermonSummary, showAuthor: boolean)}
		<!-- `portrait` answers "whose sermon?" only when nothing else does: under a
		     preacher heading it would be the same face thirteen times over, so the
		     badge falls back to the mic and the heading carries the writer. The era
		     hue stays either way, so one writer's sermons still read as a set. -->
		<ShelfCard
			href={localizeHref(`/sermons/${sermon.slug}`)}
			hue={hueForBirthYear(sermon.author.birth_year)}
			icon="mic"
			portrait={showAuthor ? sermon.author.photo_url : ''}
			title={sermon.title}
		>
			{#snippet bandAside()}
				{#if sermon.scripture_ref}
					<span class="shelf-card-ref">{sermon.scripture_ref}</span>
				{/if}
			{/snippet}
			<!-- All the meta on one muted line at the foot, rather than hanging the
			     reading time beside the title the way Topics and Plans do: those
			     titles are two or three words, sermon titles run to forty characters
			     and a shrink-0 aside squeezed them into three lines on a phone.
			     mt-auto puts the line on the card's floor whether the title runs to
			     one line or three, so a row of cards agrees on its baseline. -->
			<p class="mt-auto pt-3 text-small text-muted">
				{#if showAuthor}{sermon.author.name}<span class="opacity-50"> · </span>{/if}
				{readingTime(sermon.word_count)}
				{#if preachedYear(sermon)}<span class="opacity-50"> · </span>{preachedYear(sermon)}{/if}
			</p>
		</ShelfCard>
	{/snippet}

	{#if sorted.length === 0}
		<p class="text-body text-muted">
			{filtering ? t('sermons.noMatches') : t('sermons.empty')}
		</p>
	{:else if groups}
		<!-- Jump to a writer — the shelf runs to ~90 sermons, so the sections need
		     a way in that isn't scrolling. Same rail the Books shelf uses. -->
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
						/>
					{/if}
					<a href={localizeHref(`/authors/${g.slug}`)} class="!text-text hover:underline">{g.name}</a>
					<span class="text-small font-normal opacity-60">{g.items.length}</span>
				</h2>
				<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
					{#each g.items as sermon (sermon.slug)}
						{@render sermonCard(sermon, false)}
					{/each}
				</div>
			</section>
		{/each}
	{:else}
		<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
			{#each sorted as sermon (sermon.slug)}
				{@render sermonCard(sermon, true)}
			{/each}
		</div>
	{/if}
</div>
