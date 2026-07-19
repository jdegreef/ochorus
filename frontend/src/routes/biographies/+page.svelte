<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { AuthorBio, BookSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import BookCover from '$lib/components/BookCover.svelte';

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

	const initials = (name: string) =>
		name.split(' ').filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase();

	// --- Search · filter · sort -------------------------------------------------
	type Filter = 'all' | 'library' | 'bio';
	type Sort = 'name' | 'era' | 'books';
	let queryText = $state('');
	let filter = $state<Filter>('all');
	let sort = $state<Sort>('name');

	const filtered = $derived.by(() => {
		const q = queryText.trim().toLowerCase();
		return authors.filter((a) => {
			if (filter === 'library' && a.book_count === 0) return false;
			if (filter === 'bio' && a.book_count > 0) return false;
			if (!q) return true;
			return a.name.toLowerCase().includes(q) || (a.bio ?? '').toLowerCase().includes(q);
		});
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
				return arr.sort((a, b) => b.book_count - a.book_count || a.name.localeCompare(b.name));
			default:
				return arr.sort((a, b) => a.name.localeCompare(b.name));
		}
	});

	const FILTERS: { v: Filter; k: string }[] = [
		{ v: 'all', k: 'bios.filterAll' },
		{ v: 'library', k: 'bios.filterInLibrary' },
		{ v: 'bio', k: 'bios.filterBioOnly' }
	];

	// --- Eras -------------------------------------------------------------------
	// Named church-history buckets derived purely from birth year (no per-author
	// data). The label characterises the era; the year range beside it keeps the
	// generalisation honest. Undated writers (Ochorus' contemporary contributors)
	// fall to a trailing "Contemporary" group.
	type EraId = 'puritans' | 'awakenings' | 'missionary' | 'modern' | 'contemporary';
	const ERAS: { id: EraId; k: string; range: string }[] = [
		{ id: 'puritans', k: 'bios.eraPuritans', range: '–1699' },
		{ id: 'awakenings', k: 'bios.eraAwakenings', range: '1700–1799' },
		{ id: 'missionary', k: 'bios.eraMissionary', range: '1800–1899' },
		{ id: 'modern', k: 'bios.eraModern', range: '1900–' },
		{ id: 'contemporary', k: 'bios.eraContemporary', range: '' }
	];
	function eraOf(birth: number | null): EraId {
		if (birth == null) return 'contemporary';
		if (birth < 1700) return 'puritans';
		if (birth < 1800) return 'awakenings';
		if (birth < 1900) return 'missionary';
		return 'modern';
	}
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

	// schema.org ItemList of Person entities — one per writer, mirroring the
	// Person data on each author page. Gives search engines a structured roster
	// of the writers (rich results + entity discovery). Built from the full list,
	// not the current filter, so the markup describes the page's whole content.
	const peopleLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
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
		})
	);

	// Redirect old /biographies#<slug> deep-links to the new author pages.
	onMount(() => {
		const slug = location.hash.replace(/^#/, '');
		if (slug) goto(localizeHref(`/authors/${slug}`), { replaceState: true });
	});
</script>

<svelte:head>
	<title>{t('bios.eyebrow')} — Ochorus</title>
	<meta name="description" content={t('bios.metaDescription')} />
	<link rel="canonical" href="{SITE_URL}{localizeHref('/biographies')}" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="{t('bios.eyebrow')} — Ochorus" />
	<meta property="og:url" content="{SITE_URL}{localizeHref('/biographies')}" />
	{@html peopleLd}
</svelte:head>

<div class="mx-auto max-w-3xl px-5 py-12">
	<header class="mb-10">
		<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">{t('bios.eyebrow')}</p>
		<h1 class="text-display mb-3">{t('bios.title')}</h1>
		<p class="text-body text-muted">
			{t('bios.tagline')}
		</p>
	</header>

	<!-- Controls: search · filter · sort -->
	<div class="mb-8 flex flex-wrap items-center gap-2">
		<input
			bind:value={queryText}
			type="search"
			class="min-w-[10rem] flex-1 rounded-sm border border-border bg-surface px-3 py-1.5 text-small text-text"
			placeholder={t('bios.filterPlaceholder')}
			aria-label={t('bios.filterPlaceholder')}
		/>

		<div class="flex overflow-hidden rounded-sm border border-border text-[0.78rem]">
			{#each FILTERS as opt (opt.v)}
				<button
					class="px-2.5 py-1.5"
					class:bg-accent={filter === opt.v}
					class:text-accent-contrast={filter === opt.v}
					class:text-muted={filter !== opt.v}
					onclick={() => (filter = opt.v)}
					aria-pressed={filter === opt.v}>{t(opt.k)}</button
				>
			{/each}
		</div>

		<select
			bind:value={sort}
			class="rounded-sm border border-border bg-surface px-2 py-1.5 text-small text-text"
			aria-label={t('bios.sort')}
		>
			<option value="name">{t('bios.sortName')}</option>
			<option value="era">{t('bios.sortEra')}</option>
			<option value="books">{t('bios.sortBooks')}</option>
		</select>
	</div>

	{#snippet card(author: AuthorBio)}
		{@const shelf = booksByAuthor.get(author.slug) ?? []}
			<article id={author.slug} class="scroll-mt-24">
				<div class="flex items-center gap-4">
					<a href={localizeHref(`/authors/${author.slug}`)} class="shrink-0 hover:no-underline">
						{#if author.photo_url}
							<img
								src={author.photo_url}
								alt="{t('a11y.portraitOf')} {author.name}"
								loading="lazy"
								class="h-14 w-14 rounded-full border border-border object-cover"
								style="filter: grayscale(1)"
							/>
						{:else}
							<span
								class="flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-h3 font-semibold text-accent"
								style="font-family: var(--font-display)"
							>
								{initials(author.name)}
							</span>
						{/if}
					</a>
					<div>
						<h2 class="text-h2">
							<a href={localizeHref(`/authors/${author.slug}`)} class="!text-text hover:underline">{author.name}</a>
							{#if author.birth_year}
								<span class="ml-2 text-body font-normal text-muted"
									>{author.birth_year}–{author.death_year ?? ''}</span
								>
							{/if}
						</h2>
						<a href={localizeHref(`/authors/${author.slug}`)} class="text-small font-semibold text-accent">
							{#if author.book_count > 0}
								{author.book_count}
								{author.book_count === 1 ? t('bios.booksInLibraryOne') : t('bios.booksInLibraryMany')} →
							{:else}
								{t('bios.viewBiography')} →
							{/if}
						</a>
					</div>
				</div>
				<!-- An author can be in the library before their bio is written: show
				     their works and omit the blurb rather than render an empty gap. -->
				{#if author.bio}
					<p class="mt-4 line-clamp-3 text-body leading-relaxed text-muted">{author.bio}</p>
				{/if}
				<!-- The "View biography →" CTA above already serves book-less authors;
				     add the read-more only where the CTA is a book count AND there is
				     actually a biography to go and read. -->
				{#if author.book_count > 0 && author.bio}
					<a
						href={localizeHref(`/authors/${author.slug}`)}
						class="mt-1.5 inline-block text-small font-semibold text-accent"
					>
						{t('bios.readMore')} →
					</a>
				{/if}

				<!-- Their works: a scrollable strip of the writer's books, straight
				     into the reader. -->
				{#if shelf.length}
					<div class="mt-4 flex gap-3 overflow-x-auto pb-1" aria-label={t('nav.books')}>
						{#each shelf.slice(0, 8) as book (book.slug)}
							<a
								href={localizeHref(`/books/${book.slug}`)}
								class="w-16 shrink-0 hover:no-underline"
								title={book.title}
							>
								<BookCover {book} />
							</a>
						{/each}
					</div>
				{/if}
			</article>
	{/snippet}

	{#if sorted.length === 0}
		<p class="py-16 text-center text-body text-muted">{t('bios.noResults')}</p>
	{:else if sort === 'era'}
		{#if eraGroups.length > 1}
			<nav class="mb-8 flex flex-wrap gap-1.5" aria-label={t('bios.sortEra')}>
				{#each eraGroups as g (g.era.id)}
					<a
						href="#era-{g.era.id}"
						class="rounded-full border border-border px-2.5 py-1 text-[0.75rem] text-muted hover:border-accent hover:text-accent hover:no-underline"
					>{t(g.era.k)}</a>
				{/each}
			</nav>
		{/if}
		{#each eraGroups as g (g.era.id)}
			<section id="era-{g.era.id}" class="mb-12 scroll-mt-24">
				<h2 class="mb-6 flex items-baseline gap-2 border-b border-border pb-2 text-h3 text-text">
					{t(g.era.k)}
					{#if g.era.range}<span class="text-small font-normal text-muted">{g.era.range}</span>{/if}
					<span class="ml-auto text-small font-normal text-muted">{g.authors.length}</span>
				</h2>
				<div class="space-y-10">
					{#each g.authors as author (author.slug)}
						{@render card(author)}
					{/each}
				</div>
			</section>
		{/each}
	{:else}
		<div class="space-y-10">
			{#each sorted as author (author.slug)}
				{@render card(author)}
			{/each}
		</div>
	{/if}
</div>
