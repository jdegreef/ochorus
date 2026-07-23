<script lang="ts">
	import { onMount } from 'svelte';
	import type { BookSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { i18n } from '$lib/i18n.svelte';
	import { readJSON, writeJSON } from '$lib/persisted';
	import { allProgress } from '$lib/progress';
	import { invalidateAll } from '$app/navigation';
	import BookCard from './BookCard.svelte';
	import BookListRow from './BookListRow.svelte';
	import BookCover from './BookCover.svelte';
	import CatalogLanguageNudge from './CatalogLanguageNudge.svelte';

	let { books, loadError = false }: { books: BookSummary[]; loadError?: boolean } = $props();
	const t = i18n.t;

	// --- View preferences (persisted per device) -------------------------------
	type View = 'grid' | 'list';
	type Sort = 'shelf' | 'title' | 'longest' | 'shortest';
	type Group = 'author' | 'all';
	type Source = 'all' | 'public_domain' | 'translated';
	const PREFS_KEY = 'ochorus:books-view2';

	let view = $state<View>('grid');
	let sort = $state<Sort>('shelf');
	let group = $state<Group>('all');
	let source = $state<Source>('all');
	let topic = $state(''); // selected topic slug; '' = all topics
	let queryText = $state('');

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
	const searching = $derived(queryText.trim().length > 0 || source !== 'all' || topic !== '');
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

	// Newest additions first — a "new to the library" discovery strip. Hidden
	// while searching/filtering, and only when there are enough books to bother.
	const recent = $derived(
		[...books].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 8)
	);

	const filtered = $derived.by(() => {
		const q = queryText.trim().toLowerCase();
		return books.filter((b) => {
			if (source === 'public_domain' && b.source_type !== 'public_domain') return false;
			if (source === 'translated' && b.source_type === 'public_domain') return false;
			if (topic && !(b.topics ?? []).some((tc) => tc.slug === topic)) return false;
			if (!q) return true;
			return (
				b.title.toLowerCase().includes(q) ||
				(b.subtitle ?? '').toLowerCase().includes(q) ||
				b.author.name.toLowerCase().includes(q)
			);
		});
	});

	const sorted = $derived.by(() => {
		const arr = [...filtered];
		switch (sort) {
			case 'title':
				return arr.sort((a, b) => a.title.localeCompare(b.title));
			case 'longest':
				return arr.sort((a, b) => (b.word_count ?? 0) - (a.word_count ?? 0));
			case 'shortest':
				return arr.sort((a, b) => (a.word_count ?? 0) - (b.word_count ?? 0));
			default:
				return arr; // shelf order — the API's sort_order, preserved by filter
		}
	});

	const groups = $derived.by(() => {
		if (group === 'all') return null;
		const map = new Map<string, { slug: string; name: string; books: BookSummary[] }>();
		for (const b of sorted) {
			const g = map.get(b.author.slug) ?? { slug: b.author.slug, name: b.author.name, books: [] };
			g.books.push(b);
			map.set(b.author.slug, g);
		}
		return [...map.values()];
	});

	// --- SEO: ItemList structured data ------------------------------------------
	const jsonLd = $derived(
		JSON.stringify({
			'@context': 'https://schema.org',
			'@type': 'ItemList',
			name: 'Ochorus Library',
			numberOfItems: books.length,
			itemListElement: books.slice(0, 60).map((b, i) => ({
				'@type': 'ListItem',
				position: i + 1,
				url: `${SITE_URL}/books/${b.slug}`,
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
		<!-- eslint-disable-next-line svelte/no-at-html-tags -->
		{@html `<script type="application/ld+json">${jsonLd}<\/script>`}
	{/if}
</svelte:head>

<div class="mx-auto max-w-6xl px-5 py-10">
	<header class="mb-6">
		<h1 class="text-display mb-2">{t('nav.books')}</h1>
		<p class="text-body text-muted">{t('books.tagline')}</p>
		{#if books.length}
			<p class="mt-1 text-small text-muted">
				{books.length}
				{books.length === 1 ? t('common.bookOne') : t('common.bookMany')}
				<span class="opacity-50">·</span>
				{authorCount} {t('books.authorsWord')}
			</p>
		{/if}
	</header>

	<CatalogLanguageNudge kind="books" localizedCount={books.length} />

	{#if loadError}
		<!-- The API couldn't be reached (client-side navigation). -->
		<div class="rounded-card border border-border bg-surface p-8 text-center">
			<p class="text-body text-text">{t('books.loadError')}</p>
			<button class="btn btn-primary mt-4" onclick={() => invalidateAll()}>
				{t('error.tryAgain')}
			</button>
		</div>
	{:else if books.length === 0}
		<!-- The library is empty in this language. -->
		<div class="rounded-card border border-border bg-surface p-8 text-center">
			<p class="text-body text-text">{t('books.noneInLanguage')}</p>
			{#if !isEnglish}
				<a href="/books" class="btn btn-primary mt-4 inline-block">{t('books.readEnglish')}</a>
			{/if}
		</div>
	{:else}
		<!-- Continue reading -->
		{#if continueBooks.length && !searching}
			<section class="mb-8">
				<h2 class="mb-3 text-small font-semibold uppercase tracking-wide text-accent">
					{t('books.continue')}
				</h2>
				<div class="flex gap-4 overflow-x-auto pb-1">
					{#each continueBooks as c (c.book.slug)}
						<a
							href={localizeHref(`/books/${c.book.slug}/${c.order}`)}
							class="w-20 shrink-0 hover:no-underline sm:w-24"
						>
							<BookCover book={c.book} />
							<div class="mt-1.5 line-clamp-2 text-[0.72rem] font-medium text-text">
								{c.book.title}
							</div>
							<div class="text-[0.68rem] text-muted">{t('continue.chapter')} {c.order}</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- New to the library -->
		{#if books.length > 8 && !searching}
			<section class="mb-8">
				<h2 class="mb-3 text-small font-semibold uppercase tracking-wide text-accent">
					{t('books.newTitle')}
				</h2>
				<div class="flex gap-4 overflow-x-auto pb-1">
					{#each recent as book (book.slug)}
						<a
							href={localizeHref(`/books/${book.slug}`)}
							class="w-20 shrink-0 hover:no-underline sm:w-24"
						>
							<BookCover {book} />
							<div class="mt-1.5 line-clamp-2 text-[0.72rem] font-medium text-text">
								{book.title}
							</div>
							<div class="truncate text-[0.68rem] text-muted">{book.author.name}</div>
						</a>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Controls: search · source · sort · group · view -->
		<div class="mb-6 flex flex-wrap items-center gap-2">
			<input
				bind:value={queryText}
				type="search"
				class="min-w-[10rem] flex-1 rounded-sm border border-border bg-surface px-3 py-1.5 text-small text-text"
				placeholder={t('books.filterPlaceholder')}
				aria-label={t('books.filterPlaceholder')}
			/>

			{#if showSourceFilter}
				<div class="flex overflow-hidden rounded-sm border border-border text-[0.78rem]">
					{#each [['all', t('books.sourceAll')], ['public_domain', t('books.sourcePublic')], ['translated', t('books.sourceTranslated')]] as opt (opt[0])}
						<button
							class="px-2.5 py-1.5"
							class:bg-accent={source === opt[0]}
							class:text-accent-contrast={source === opt[0]}
							class:text-muted={source !== opt[0]}
							onclick={() => (source = opt[0] as Source)}
							aria-pressed={source === opt[0]}>{opt[1]}</button
						>
					{/each}
				</div>
			{/if}

			<select
				value={sort}
				onchange={onSort}
				class="rounded-sm border border-border bg-surface px-2 py-1.5 text-small text-text"
				aria-label={t('books.sort')}
			>
				<option value="shelf">{t('books.sortShelf')}</option>
				<option value="title">{t('books.sortTitle')}</option>
				<option value="longest">{t('books.sortLongest')}</option>
				<option value="shortest">{t('books.sortShortest')}</option>
			</select>

			<div class="flex overflow-hidden rounded-sm border border-border text-[0.78rem]">
				<button
					class="px-2.5 py-1.5"
					class:bg-accent={group === 'author'}
					class:text-accent-contrast={group === 'author'}
					class:text-muted={group !== 'author'}
					onclick={() => setGroup('author')}
					aria-pressed={group === 'author'}>{t('books.groupAuthor')}</button
				>
				<button
					class="px-2.5 py-1.5"
					class:bg-accent={group === 'all'}
					class:text-accent-contrast={group === 'all'}
					class:text-muted={group !== 'all'}
					onclick={() => setGroup('all')}
					aria-pressed={group === 'all'}>{t('books.groupAll')}</button
				>
			</div>

			<div class="flex overflow-hidden rounded-sm border border-border">
				<button
					class="px-2.5 py-1.5"
					class:bg-accent={view === 'grid'}
					class:text-accent-contrast={view === 'grid'}
					class:text-muted={view !== 'grid'}
					onclick={() => setView('grid')}
					aria-label={t('books.viewGrid')}
					aria-pressed={view === 'grid'}>▦</button
				>
				<button
					class="px-2.5 py-1.5"
					class:bg-accent={view === 'list'}
					class:text-accent-contrast={view === 'list'}
					class:text-muted={view !== 'list'}
					onclick={() => setView('list')}
					aria-label={t('books.viewList')}
					aria-pressed={view === 'list'}>☰</button
				>
			</div>
		</div>

		<!-- Topic filter -->
		{#if allTopics.length > 1}
			<div class="mb-6 flex flex-wrap gap-1.5" aria-label={t('books.filterTopic')} role="group">
				<button
					class="rounded-full border px-2.5 py-1 text-[0.75rem]"
					class:border-accent={topic === ''}
					class:bg-accent={topic === ''}
					class:text-accent-contrast={topic === ''}
					class:border-border={topic !== ''}
					class:text-muted={topic !== ''}
					onclick={() => (topic = '')}
					aria-pressed={topic === ''}
				>
					{t('books.topicAll')}
				</button>
				{#each allTopics as tc (tc.slug)}
					<button
						class="rounded-full border px-2.5 py-1 text-[0.75rem]"
						class:border-accent={topic === tc.slug}
						class:bg-accent={topic === tc.slug}
						class:text-accent-contrast={topic === tc.slug}
						class:border-border={topic !== tc.slug}
						class:text-muted={topic !== tc.slug}
						onclick={() => (topic = topic === tc.slug ? '' : tc.slug)}
						aria-pressed={topic === tc.slug}
					>
						{tc.title}
					</button>
				{/each}
			</div>
		{/if}

		<!-- Author quick-nav -->
		{#if groups && groups.length > 1}
			<nav class="mb-8 flex flex-wrap gap-1.5" aria-label={t('books.groupAuthor')}>
				{#each groups as g (g.slug)}
					<a
						href="#author-{g.slug}"
						class="rounded-full border border-border px-2.5 py-1 text-[0.75rem] text-muted hover:border-accent hover:text-accent hover:no-underline"
					>
						{g.name}
					</a>
				{/each}
			</nav>
		{/if}

		<!-- Results -->
		{#if sorted.length === 0}
			<p class="py-16 text-center text-body text-muted">{t('books.noResults')}</p>
		{:else if groups}
			{#each groups as g (g.slug)}
				<section id="author-{g.slug}" class="mb-10 scroll-mt-20">
					<h2 class="mb-4 flex items-baseline gap-2 text-h3 text-muted">
						{g.name}
						<span class="text-small font-normal opacity-60">{g.books.length}</span>
					</h2>
					{#if view === 'grid'}
						<div class="grid grid-cols-3 gap-x-4 gap-y-6 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6">
							{#each g.books as book (book.slug)}
								<BookCard {book} />
							{/each}
						</div>
					{:else}
						<div class="flex flex-col gap-1">
							{#each g.books as book (book.slug)}
								<BookListRow {book} showAuthor={false} />
							{/each}
						</div>
					{/if}
				</section>
			{/each}
		{:else if view === 'grid'}
			<div class="grid grid-cols-3 gap-x-4 gap-y-6 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6">
				{#each sorted as book (book.slug)}
					<BookCard {book} showAuthor />
				{/each}
			</div>
		{:else}
			<div class="flex flex-col gap-1">
				{#each sorted as book (book.slug)}
					<BookListRow {book} />
				{/each}
			</div>
		{/if}
	{/if}
</div>
