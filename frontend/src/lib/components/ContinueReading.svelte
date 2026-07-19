<script lang="ts">
	import { onMount } from 'svelte';
	import type { BookSummary } from '$lib/library';
	import { allProgress } from '$lib/progress';
	import { bookProgressPercent } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

	/**
	 * In-progress books with a progress bar and a resume link. Progress comes
	 * from the local cache (which the sign-in merge keeps in step with the
	 * account), joined against the provided book list for titles and covers.
	 * Books unknown in this language are skipped; a book stays here through its
	 * last chapter (opening the last chapter isn't finishing it — the old code
	 * hid it immediately) and ages off naturally as newer reads push it past the
	 * limit. Renders nothing when there's nothing in progress.
	 */
	let { books, limit = 4 }: { books: BookSummary[]; limit?: number } = $props();

	const t = i18n.t;

	// localStorage is read on mount (not during load) so a sign-in sync that
	// lands after navigation still shows up via the ochorus:sync event below.
	let ticks = $state(0);
	onMount(() => {
		const bump = () => ticks++;
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	const items = $derived.by(() => {
		void ticks;
		const bySlug = new Map(books.map((b) => [b.slug, b]));
		return allProgress()
			.map((p) => {
				const book = bySlug.get(p.slug);
				if (!book) return null;
				// order is the chapter currently open. Treat it as in-progress, not
				// finished — the midpoint estimate keeps the book visible (and honest
				// about position) all the way through the last chapter.
				const pct = bookProgressPercent(p.order, book.chapter_count);
				return { book, order: p.order, pct };
			})
			.filter((x) => x !== null)
			.slice(0, limit);
	});
</script>

{#if items.length}
	<section class="mx-auto max-w-5xl px-5 pt-14">
		<h2 class="text-h1 mb-6">{t('continue.title')}</h2>
		<div class="grid gap-4 sm:grid-cols-2" class:lg:grid-cols-4={limit >= 4}>
			{#each items as item (item.book.slug)}
				<a
					href={localizeHref(`/books/${item.book.slug}/${item.order}`)}
					class="group flex gap-4 rounded-card border border-border p-4 hover:bg-surface-2 hover:no-underline"
				>
					{#if item.book.cover_url}
						<img
							src={item.book.cover_url}
							alt=""
							loading="lazy"
							class="h-20 w-14 shrink-0 rounded-sm object-cover shadow-sm"
						/>
					{:else}
						<div
							class="h-20 w-14 shrink-0 rounded-sm shadow-sm"
							style="background: {item.book.cover_color || '#3b5bdb'}"
						></div>
					{/if}
					<div class="min-w-0 flex-1 self-center">
						<div class="truncate text-small font-semibold text-text">{item.book.title}</div>
						<div class="mt-0.5 truncate text-[0.78rem] text-muted">{item.book.author.name}</div>
						<div class="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-2">
							<div class="h-full rounded-full bg-accent" style="width: {item.pct}%"></div>
						</div>
						<div class="mt-1 text-[0.72rem] text-muted">
							{t('continue.chapter')}
							{item.order} / {item.book.chapter_count} · {item.pct}%
						</div>
					</div>
				</a>
			{/each}
		</div>
	</section>
{/if}
