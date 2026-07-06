<script lang="ts">
	import type { BookSummary, AuthorBio } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import ContinueReading from '$lib/components/ContinueReading.svelte';
	import TodaysReading from '$lib/components/TodaysReading.svelte';
	import SermonOfTheWeek from '$lib/components/SermonOfTheWeek.svelte';

	let { data } = $props();
	const featured = $derived<BookSummary[]>(data.featured);
	const authors = $derived<AuthorBio[]>(data.authors);
	const totalBooks = $derived<number>(data.totalBooks);

	const initials = (name: string) =>
		name
			.split(' ')
			.filter(Boolean)
			.map((w) => w[0])
			.slice(0, 2)
			.join('')
			.toUpperCase();
</script>

<svelte:head>
	<title>Ochorus — Equipping People with Classic Christian Books</title>
	<meta
		name="description"
		content="Ochorus — read classic Christian books from Andrew Murray, Charles Spurgeon, Watchman Nee and more. Free, beautifully set, in your language."
	/>
	<link rel="canonical" href="{SITE_URL}/" />
	<meta property="og:type" content="website" />
	<meta property="og:site_name" content="Ochorus" />
	<meta property="og:title" content="Ochorus — Equipping People with Classic Christian Books" />
	<meta
		property="og:description"
		content="Read classic Christian books from Andrew Murray, Charles Spurgeon, Watchman Nee and more — free, beautifully set, in your language."
	/>
	<meta property="og:url" content="{SITE_URL}/" />
	<meta name="twitter:card" content="summary" />
</svelte:head>

<!-- Hero -->
<section class="border-b border-border bg-surface-2">
	<div class="mx-auto max-w-4xl px-5 py-20 text-center">
		<p class="mb-4 text-small font-semibold uppercase tracking-widest text-accent">
			Read, Reflect, and Be Transformed
		</p>
		<h1 class="text-display mx-auto mb-5 max-w-3xl">
			Equipping People with Classic Christian Books
		</h1>
		<p class="mx-auto mb-8 max-w-xl text-body text-muted">
			Timeless devotional classics from Andrew Murray, Charles Spurgeon, Watchman Nee and more —
			free to read, beautifully set, in your language soon.
		</p>
		<div class="flex flex-wrap justify-center gap-3">
			<a href="/books" class="btn btn-primary">Browse the Library</a>
			<a href="/about" class="btn btn-ghost">About Ochorus</a>
		</div>
	</div>
</section>

<!-- Personal blocks — client-side only (this page is prerendered) -->
<ContinueReading books={data.books} />
<TodaysReading />
<SermonOfTheWeek />

<!-- Discover Your Next Book -->
<section class="mx-auto max-w-5xl px-5 py-14">
	<div class="mb-6 flex items-end justify-between">
		<h2 class="text-h1">Discover Your Next Book</h2>
		<a href="/books" class="text-small font-semibold text-accent">All {totalBooks} books →</a>
	</div>
	<div class="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-6">
		{#each featured as book (book.slug)}
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
			</a>
		{/each}
	</div>
</section>

<!-- Mission teaser -->
<section class="border-y border-border bg-surface-2">
	<div class="mx-auto max-w-3xl px-5 py-14 text-center">
		<h2 class="text-h1 mb-3">Spreading the Gospel Through Literature</h2>
		<p class="mx-auto max-w-xl text-body text-muted">
			Based in Kampala, Uganda and established in 2021, Ochorus is a ministry devoted to making
			exceptional classic Christian literature freely accessible to every corner of the world.
		</p>
		<a href="/about" class="btn btn-ghost mt-6">Our Story</a>
	</div>
</section>

<!-- Christian Authors -->
<section class="mx-auto max-w-5xl px-5 py-14">
	<div class="mb-6 flex items-end justify-between">
		<h2 class="text-h1">Christian Authors</h2>
		<a href="/biographies" class="text-small font-semibold text-accent">All biographies →</a>
	</div>
	<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
		{#each authors as author (author.slug)}
			<a
				href="/authors/{author.slug}"
				class="flex items-center gap-3 rounded-card border border-border p-4 hover:no-underline hover:bg-surface-2"
			>
				<span
					class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent-soft text-small font-semibold text-accent"
					style="font-family: var(--font-display)"
				>
					{initials(author.name)}
				</span>
				<span>
					<span class="block text-small font-semibold text-text">{author.name}</span>
					<span class="block text-[0.8rem] text-muted">
						{author.book_count} book{author.book_count === 1 ? '' : 's'}
					</span>
				</span>
			</a>
		{/each}
	</div>
</section>
