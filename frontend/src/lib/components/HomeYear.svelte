<script lang="ts">
	import { onMount } from 'svelte';
	import { allProgress } from '$lib/progress';
	import { libraryBooks } from '$lib/resumeBooks';
	import { readingActivity } from '$lib/readingActivity.svelte';
	import { readingPace } from '$lib/readingPace.svelte';
	import { yearStats } from '$lib/yearInBooks';
	import type { BookSummary } from '$lib/library-public';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import BookCover from '$lib/components/BookCover.svelte';

	/**
	 * A home-page glimpse of "Your year in books": how many finished this year,
	 * and their covers as a small collage, linking to the full page on the
	 * Bookshelf (YearInBooks). The numbers are yearInBooks.ts's, so the two
	 * can't disagree. Renders nothing until a book is finished this year, and
	 * fetches the book list (for the covers) only when one has been.
	 * Client-only, like the rest of the dashboard; re-reads on the
	 * `ochorus:sync` a sign-in merge fires.
	 */
	const t = i18n.t;
	const MAX_COVERS = 12;
	const year = new Date().getFullYear();

	let books = $state<BookSummary[]>([]);
	let ticks = $state(0);

	function load() {
		ticks++;
		// yearStats with no catalog still counts the year's finishes (it reads
		// them from progress), so the gate and the card share one definition.
		const finished = yearStats({ progress: allProgress(), books: [], days: [], year, wpm: 0 }).finished;
		if (!finished) return;
		libraryBooks(getLang())
			.then((list) => (books = list))
			.catch(() => {});
	}

	onMount(() => {
		load();
		window.addEventListener('ochorus:sync', load);
		return () => window.removeEventListener('ochorus:sync', load);
	});

	const stats = $derived.by(() => {
		void ticks;
		return yearStats({
			progress: allProgress(),
			books,
			days: readingActivity.days(),
			year,
			wpm: readingPace.wpm
		});
	});
</script>

{#if stats.finished}
	<section class="page-col px-5 pt-14">
		<div class="flex flex-col gap-6 rounded-card border border-border bg-surface p-6 sm:flex-row sm:items-start sm:gap-8 sm:p-8">
			<div class="shrink-0 sm:w-56">
				<p class="eyebrow text-gold">{t('year.title')} · {year}</p>
				<!-- The number and what it counts on one line: stacked, they left a
				     tall empty column beside nothing on a phone. -->
				<p class="mt-2 flex items-baseline gap-3">
					<span class="font-display text-h1 leading-none">{stats.finished}</span>
					<span class="text-body text-muted">{t('year.statFinished')}</span>
				</p>
			</div>
			<!-- The covers as a straight grid, newest first, each a way back
			     into its book (as on the Bookshelf's year). Only covers this language
			     has: the count above is the year's, as YearInBooks shows it. The way
			     to the full year closes the grid as a tile of its own — one link,
			     where a text link repeated the eyebrow, and it fills the gap a short
			     last row would otherwise leave (seven covers in four columns). -->
			{#if stats.books.length}
				<ul class="grid flex-1 grid-cols-4 gap-2.5 sm:grid-cols-6" aria-label={t('year.title')}>
					{#each stats.books.slice(0, MAX_COVERS) as book (book.slug)}
						<li>
							<a href={localizeHref(`/books/${book.slug}`)} title={book.title} aria-label={book.title}>
								<BookCover {book} rounded="rounded-sm" />
							</a>
						</li>
					{/each}
					<li>
						<a href="{localizeHref('/favorites')}#year" class="year-more card-tint">
							<span>{t('year.seeYear')} <Arrow /></span>
						</a>
					</li>
				</ul>
			{:else}
				<a href="{localizeHref('/favorites')}#year" class="inline-block text-small font-semibold text-accent hover:underline"
					>{t('year.seeYear')} <Arrow /></a
				>
			{/if}
		</div>
	</section>
{/if}

<style>
	/* The closing tile: a cover's shape, so the grid stays level, holding the
	   way to the full year. */
	.year-more {
		display: flex;
		align-items: center;
		justify-content: center;
		aspect-ratio: 3 / 4;
		padding: 0.5rem;
		border: 1px dashed var(--border-strong);
		border-radius: var(--radius-sm);
		background: var(--surface-2);
		color: var(--accent);
		font-size: var(--fs-small);
		font-weight: 600;
		line-height: 1.25;
		text-align: center;
		text-decoration: none;
	}
</style>
