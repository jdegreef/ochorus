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
	const ogImage = $derived(
		author.photo_url
			? absUrl(author.photo_url)
			: author.books[0]?.cover_url
				? absUrl(author.books[0].cover_url)
				: ''
	);

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

	<header class="flex items-center gap-5">
		{#if author.photo_url}
			<img
				src={author.photo_url}
				alt="Portrait of {author.name}"
				class="h-24 w-24 shrink-0 rounded-full border border-border object-cover shadow-sm"
				style="filter: grayscale(1)"
			/>
		{:else}
			<span
				class="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-accent-soft text-h2 font-semibold text-accent"
				style="font-family: var(--font-display)"
			>
				{initials(author.name)}
			</span>
		{/if}
		<div>
			<h1 class="text-h1">{author.name}</h1>
			{#if years}<p class="text-body text-muted">{years}</p>{/if}
		</div>
	</header>

	<!-- Biography -->
	{#if author.bio_html}
		<div class="bio mx-auto mt-8 max-w-[40rem]">
			<!-- Long-form biography; cleaned HTML with pull-quotes + prayer callouts. -->
			{@html author.bio_html}
		</div>
	{:else if author.bio}
		<p class="mt-6 text-body leading-relaxed text-muted">{author.bio}</p>
	{/if}

	<!-- Books -->
	{#if author.books.length}
		<section class="mt-14">
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
	{/if}

	<!-- Sermons -->
	{#if author.sermons.length}
		<section class="mt-14">
			<h2 class="mb-4 text-h3">
				Sermons by {author.name}
				<span class="text-small font-normal text-muted">({author.sermons.length})</span>
			</h2>
			<ul class="divide-y divide-border">
				{#each author.sermons as sermon (sermon.slug)}
					<li>
						<a
							href="/sermons/{sermon.slug}"
							class="flex items-baseline justify-between gap-3 py-3 hover:no-underline"
						>
							<span class="flex-1">
								<span class="block text-body font-medium text-text">{sermon.title}</span>
								{#if sermon.scripture_ref}
									<span class="text-small text-accent">{sermon.scripture_ref}</span>
								{/if}
							</span>
							<span class="shrink-0 text-[0.8rem] text-muted">
								{Math.max(1, Math.round(sermon.word_count / 200))} min
							</span>
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if !author.books.length && !author.sermons.length}
		<p class="mt-10 text-body text-muted">No books or sermons in the library yet for this writer.</p>
	{/if}
</div>

<style>
	/* Long-form biography styling. Targets the injected {@html} via :global.
	   Prose in the reading serif; pull-quotes and prayer callouts stand out. */
	:global(.bio) {
		font-family: var(--font-display);
		font-size: 1.12rem;
		line-height: 1.8;
		color: var(--text);
	}
	:global(.bio p) {
		margin: 0 0 1.15em;
	}
	:global(.bio h2) {
		font-family: var(--font-display);
		font-size: var(--fs-h2);
		font-weight: 600;
		line-height: 1.25;
		margin: 1.9em 0 0.55em;
	}
	:global(.bio a) {
		color: var(--accent);
	}

	/* Pull-quote: a called-out saying, visually distinct. */
	:global(.bio blockquote) {
		margin: 1.7em 0;
		padding: 0.1em 0 0.1em 1.25rem;
		border-left: 3px solid var(--gold);
		font-size: 1.45rem;
		line-height: 1.45;
		font-style: italic;
		color: var(--text);
	}
	:global(.bio blockquote p) {
		margin: 0;
	}
	:global(.bio blockquote cite) {
		display: block;
		margin-top: 0.55em;
		font-size: 0.9rem;
		font-style: normal;
		color: var(--muted);
	}

	/* Prayer callout: highlights a key time of prayer. `.answered` marks an
	   answer to prayer with the indigo accent instead of gold. */
	:global(.bio .prayer) {
		margin: 1.7em 0;
		padding: 1rem 1.2rem;
		border-radius: var(--radius-card);
		background: color-mix(in srgb, var(--gold) 12%, transparent);
		border: 1px solid color-mix(in srgb, var(--gold) 32%, transparent);
	}
	:global(.bio .prayer > *:last-child) {
		margin-bottom: 0;
	}
	:global(.bio .prayer)::before {
		content: '✦ In prayer';
		display: block;
		margin-bottom: 0.5rem;
		font-family: var(--font-sans);
		font-size: 0.72rem;
		font-weight: 700;
		letter-spacing: 0.09em;
		text-transform: uppercase;
		color: var(--gold);
	}
	:global(.bio .prayer.answered) {
		background: var(--accent-soft);
		border-color: var(--accent-soft-border);
	}
	:global(.bio .prayer.answered)::before {
		content: '✦ Answer to prayer';
		color: var(--accent);
	}
</style>
