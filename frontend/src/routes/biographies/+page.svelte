<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { AuthorBio } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

	const t = i18n.t;

	let { data } = $props();
	const authors = $derived<AuthorBio[]>(data.authors);

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
					class:text-white={filter === opt.v}
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

	{#if sorted.length === 0}
		<p class="py-16 text-center text-body text-muted">{t('bios.noResults')}</p>
	{/if}

	<div class="space-y-10">
		{#each sorted as author (author.slug)}
			<article id={author.slug} class="scroll-mt-24">
				<div class="flex items-center gap-4">
					<a href={localizeHref(`/authors/${author.slug}`)} class="shrink-0 hover:no-underline">
						{#if author.photo_url}
							<img
								src={author.photo_url}
								alt="Portrait of {author.name}"
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
				<p class="mt-4 line-clamp-3 text-body leading-relaxed text-muted">{author.bio}</p>
				<!-- The "View biography →" CTA above already serves book-less authors;
				     add the read-more only where the CTA above is a book count. -->
				{#if author.book_count > 0}
					<a
						href={localizeHref(`/authors/${author.slug}`)}
						class="mt-1.5 inline-block text-small font-semibold text-accent"
					>
						{t('bios.readMore')} →
					</a>
				{/if}
			</article>
		{/each}
	</div>
</div>
