<script lang="ts">
	import { onMount } from 'svelte';
	import { listBooks, type BookSummary } from '$lib/library';
	import { allProgress } from '$lib/progress';
	import { favorites } from '$lib/favorites.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import BookCard from './BookCard.svelte';

	/**
	 * "Recommended for you" — unread books matching the topics and authors of
	 * what the reader has actually read or favorited. A plain heuristic, no
	 * model: their history IS the signal. Client-side only (personal, and the
	 * homepage is prerendered); renders nothing for a reader with no history,
	 * whom the Discover section already serves.
	 */
	const t = i18n.t;

	const LIMIT = 4;
	let catalog = $state<BookSummary[]>([]);

	onMount(async () => {
		try {
			catalog = await listBooks(getLang());
		} catch {
			/* recommendations are a bonus block — never break the homepage */
		}
	});

	const picks = $derived.by<BookSummary[]>(() => {
		void favorites.ticks; // re-derive when hearts change
		if (!catalog.length) return [];

		const bySlug = new Map(catalog.map((b) => [b.slug, b]));
		const readSlugs = new Set(
			allProgress()
				.filter((p) => p.kind === 'book')
				.map((p) => p.slug)
		);
		const favBooks = new Set<string>();
		const favAuthors = new Set<string>();
		for (const f of favorites.all()) {
			if (f.kind === 'book') favBooks.add(f.slug);
			if (f.kind === 'author') favAuthors.add(f.slug);
		}

		// Affinities from the reader's history: which topics and authors their
		// read + hearted books belong to.
		const topicAffinity = new Set<string>();
		const authorAffinity = new Set<string>();
		for (const slug of [...readSlugs, ...favBooks]) {
			const b = bySlug.get(slug);
			if (!b) continue;
			for (const tp of b.topics) topicAffinity.add(tp.slug);
			authorAffinity.add(b.author.slug);
		}
		if (!topicAffinity.size && !authorAffinity.size && !favAuthors.size) return [];

		// Score every unread, unhearted book; a followed author is the strongest
		// signal, then an author they've read, then each shared topic.
		return catalog
			.filter((b) => !readSlugs.has(b.slug) && !favBooks.has(b.slug))
			.map((b) => {
				let score = 0;
				if (favAuthors.has(b.author.slug)) score += 3;
				if (authorAffinity.has(b.author.slug)) score += 2;
				for (const tp of b.topics) if (topicAffinity.has(tp.slug)) score += 1;
				return { b, score };
			})
			.filter((x) => x.score > 0)
			.sort((x, y) => y.score - x.score)
			.slice(0, LIMIT)
			.map((x) => x.b);
	});
</script>

{#if picks.length}
	<section class="mx-auto max-w-5xl px-5 pt-14">
		<div class="mb-6 flex items-end justify-between">
			<h2 class="text-h2">{t('home.recommendedNext')}</h2>
			<a href={localizeHref('/books')} class="text-small font-semibold text-accent"
				>{t('home.allBooks')} →</a
			>
		</div>
		<div class="grid grid-cols-2 gap-5 sm:grid-cols-4">
			{#each picks as book (book.slug)}
				<BookCard {book} showAuthor />
			{/each}
		</div>
	</section>
{/if}
