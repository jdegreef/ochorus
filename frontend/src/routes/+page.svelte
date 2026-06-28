<script lang="ts">
	import type { BookSummary } from '$lib/library';

	let { data } = $props();
	const books = $derived<BookSummary[]>(data.books);

	// Group books by author, preserving shelf order.
	const groups = $derived.by(() => {
		const map = new Map<string, { name: string; books: BookSummary[] }>();
		for (const b of books) {
			const g = map.get(b.author.slug) ?? { name: b.author.name, books: [] };
			g.books.push(b);
			map.set(b.author.slug, g);
		}
		return [...map.values()];
	});

	const onCover = (hex: string) => `linear-gradient(150deg, ${hex} 0%, ${shade(hex, -28)} 100%)`;

	// Darken a #rrggbb hex by `amt` (percentage points of each channel).
	function shade(hex: string, amt: number): string {
		const n = hex.replace('#', '');
		if (n.length !== 6) return hex;
		const c = [0, 2, 4].map((i) => {
			const v = Math.round(parseInt(n.slice(i, i + 2), 16) * (1 + amt / 100));
			return Math.max(0, Math.min(255, v)).toString(16).padStart(2, '0');
		});
		return `#${c.join('')}`;
	}
</script>

<svelte:head><title>Ochorus — public-domain Christian classics</title></svelte:head>

<div class="mx-auto max-w-3xl px-5 py-10">
	<section class="mb-10">
		<h1 class="text-display mb-3">A quiet library of Christian classics.</h1>
		<p class="text-body max-w-xl text-muted">
			Timeless devotional books from Andrew Murray, Charles Spurgeon, and more —
			free to read, beautifully set, in your language soon.
		</p>
	</section>

	{#each groups as group (group.name)}
		<section class="mb-10">
			<h2 class="mb-4 text-h3 text-muted">{group.name}</h2>
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
				{#each group.books as book (book.slug)}
					<a
						href="/books/{book.slug}"
						class="group block hover:no-underline"
						data-testid="book-card"
					>
						<div
							class="flex aspect-[3/4] flex-col justify-between rounded-card p-4 shadow-sm transition-transform group-hover:-translate-y-1"
							style="background: {onCover(book.cover_color || '#3b5bdb')}"
						>
							<span class="text-[0.7rem] font-semibold uppercase tracking-wider text-white/70">
								{book.author.name.split(' ').slice(-1)}
							</span>
							<span
								style="font-family: var(--font-display)"
								class="text-[1.15rem] font-semibold leading-tight text-white"
							>
								{book.title}
							</span>
						</div>
						<div class="mt-2 px-0.5">
							<div class="text-small font-medium text-text">{book.title}</div>
							<div class="text-[0.8rem] text-muted">{book.chapter_count} chapters</div>
						</div>
					</a>
				{/each}
			</div>
		</section>
	{/each}
</div>
