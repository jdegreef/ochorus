<script lang="ts">
	import type { AuthorDetail } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumb } from '$lib/seo';

	let { data } = $props();
	const author = $derived<AuthorDetail>(data.author);

	const initials = (name: string) =>
		name.split(' ').filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase();

	const years = $derived(
		author.birth_year ? `${author.birth_year}–${author.death_year ?? ''}` : ''
	);
	const canonical = $derived(`${SITE_URL}/authors/${author.slug}`);
	const description = $derived(
		(author.bio || `${author.name} on Ochorus — free classic Christian books.`).slice(0, 300)
	);
	const ogImage = $derived(author.books[0]?.cover_url ? absUrl(author.books[0].cover_url) : '');

	const personLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Person',
			name: author.name,
			description: author.bio || undefined,
			birthDate: author.birth_year ? String(author.birth_year) : undefined,
			deathDate: author.death_year ? String(author.death_year) : undefined,
			url: canonical
		})
	);
	const crumbsLd = $derived(
		jsonLd(
			breadcrumb([
				{ name: 'Home', url: '/' },
				{ name: 'Biographies', url: '/biographies' },
				{ name: author.name, url: `/authors/${author.slug}` }
			])
		)
	);
</script>

<svelte:head>
	<title>{author.name} — Ochorus</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={canonical} />
	<meta property="og:type" content="profile" />
	<meta property="og:title" content="{author.name} — Ochorus" />
	<meta property="og:description" content={description} />
	<meta property="og:url" content={canonical} />
	{#if ogImage}<meta property="og:image" content={ogImage} />{/if}
	<meta name="twitter:card" content={ogImage ? 'summary_large_image' : 'summary'} />
	{@html personLd}
	{@html crumbsLd}
</svelte:head>

<div class="mx-auto max-w-3xl px-5 py-12">
	<!-- Breadcrumb -->
	<nav class="mb-6 flex flex-wrap items-center gap-1.5 text-small text-muted" aria-label="Breadcrumb">
		<a href="/" class="hover:text-text">Home</a>
		<span>›</span>
		<a href="/biographies" class="hover:text-text">Biographies</a>
		<span>›</span>
		<span class="text-text">{author.name}</span>
	</nav>

	<header class="flex items-center gap-4">
		<span
			class="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-accent-soft text-h2 font-semibold text-accent"
			style="font-family: var(--font-display)"
		>
			{initials(author.name)}
		</span>
		<div>
			<h1 class="text-h1">{author.name}</h1>
			{#if years}<p class="text-body text-muted">{years}</p>{/if}
		</div>
	</header>

	{#if author.bio}
		<p class="mt-6 text-body leading-relaxed text-muted">{author.bio}</p>
	{/if}

	{#if author.books.length}
		<section class="mt-10">
			<h2 class="mb-4 text-h3">
				Books by {author.name}
				<span class="text-small font-normal text-muted">({author.books.length})</span>
			</h2>
			<div class="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
				{#each author.books as book (book.slug)}
					<a href="/books/{book.slug}" class="group block hover:no-underline">
						{#if book.cover_url}
							<img
								src={book.cover_url}
								alt="Cover of {book.title}"
								loading="lazy"
								class="aspect-[3/4] w-full rounded-card object-cover shadow-sm transition-transform group-hover:-translate-y-1"
							/>
						{:else}
							<div
								class="aspect-[3/4] w-full rounded-card shadow-sm"
								style="background: {book.cover_color || '#3b5bdb'}"
							></div>
						{/if}
						<div class="mt-2 text-small font-medium text-text">{book.title}</div>
						<div class="text-[0.8rem] text-muted">{book.chapter_count} chapters</div>
					</a>
				{/each}
			</div>
		</section>
	{:else}
		<p class="mt-8 text-body text-muted">No books in the library yet for this writer.</p>
	{/if}
</div>
