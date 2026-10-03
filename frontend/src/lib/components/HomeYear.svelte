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
		<div class="flex flex-col gap-8 rounded-card border border-border bg-surface p-6 sm:flex-row sm:items-center sm:p-8">
			<div class="flex shrink-0 flex-col gap-2 sm:w-64">
				<p class="eyebrow text-gold">{t('year.title')} · {year}</p>
				<p class="font-display text-h1 leading-none">{stats.finished}</p>
				<p class="text-body text-muted">{t('year.statFinished')}</p>
				<a
					href="{localizeHref('/favorites')}#year"
					class="mt-2 text-small font-semibold text-accent hover:underline">{t('year.title')} <Arrow /></a
				>
			</div>
			<!-- The covers as a slightly tilted collage, newest first, each a way back
			     into its book (as on the Bookshelf's year). Only covers this language
			     has: the count above is the year's, as YearInBooks shows it. -->
			{#if stats.books.length}
				<ul class="year-collage grid flex-1 grid-cols-4 gap-2.5 sm:grid-cols-6" aria-label={t('year.title')}>
					{#each stats.books.slice(0, MAX_COVERS) as book (book.slug)}
						<li>
							<a href={localizeHref(`/books/${book.slug}`)} title={book.title} aria-label={book.title}>
								<BookCover {book} rounded="rounded-sm" />
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</section>
{/if}

<style>
	.year-collage {
		transform: rotate(-1.5deg);
	}
</style>
