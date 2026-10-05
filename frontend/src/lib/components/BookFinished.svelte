<script lang="ts">
	import { onMount } from 'svelte';
	import type { BookDetail, BookSummary, PlanSummary } from '$lib/library-public';
	import { listPlans } from '$lib/library-public';
	import { libraryBooks } from '$lib/resumeBooks';
	import { allProgress, bookProgressReader, isFinished } from '$lib/progress';
	import { yearStats } from '$lib/yearInBooks';
	import { marks } from '$lib/marks.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { localizeHref } from '$lib/href';
	import { authorPath } from '$lib/originals';
	import { i18n } from '$lib/i18n.svelte';
	import { finishedPicks } from '$lib/bookFinished';
	import Arrow from '$lib/components/Arrow.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import BookDownloadMenu from '$lib/components/BookDownloadMenu.svelte';

	/**
	 * The end of a book, once it is finished: an arrival worth marking, and
	 * the ways onward from it — reflect, the other editions, more by the same
	 * author, a plan that reads it, something like it, a copy to keep, a friend
	 * to tell. Shown under the last chapter's ending by the chapter route.
	 *
	 * Renders only while the book is stamped finished (`offerFinish` fires as
	 * the reader reaches the end; its Undo takes this away again), so it is
	 * never a congratulation for a book still being read. Client-only: it
	 * reads progress and highlights from this device.
	 *
	 * SEVERAL ROOT BLOCKS, on purpose. The chapter's ending keeps each of its
	 * child blocks whole across page turns (`.paged .chapter-end > *`), so one
	 * tall wrapper would split anyway; separate sections each stay in one piece.
	 */
	let {
		book,
		language,
		shareUrl
	}: {
		book: BookDetail;
		/** The chapter's content language: number formatting, the note's source. */
		language: string;
		/** The book's own page, absolute: what "tell a friend" passes on. */
		shareUrl: string;
	} = $props();

	const t = i18n.t;
	const year = new Date().getFullYear();
	const MAX = 4;

	let ticks = $state(0);
	let catalog = $state<BookSummary[]>([]);
	let plans = $state<PlanSummary[]>([]);

	onMount(() => {
		const bump = () => ticks++;
		window.addEventListener('ochorus:sync', bump);
		const lang = getLang();
		// Bonus blocks: a failed list leaves its section out, never the page.
		libraryBooks(lang)
			.then((list) => (catalog = list))
			.catch(() => {});
		listPlans(lang)
			.then((list) => (plans = list))
			.catch(() => {});
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	const finished = $derived.by(() => {
		void ticks;
		return isFinished(book.slug);
	});
	const finishedThisYear = $derived.by(() => {
		void ticks;
		return yearStats({ progress: allProgress(), books: [], days: [], year, wpm: 0 }).finished;
	});
	const picks = $derived.by(() => {
		void ticks;
		return finishedPicks({ book, catalog, plans, progress: bookProgressReader(), max: MAX });
	});
	// Every edition's marks (the modern English ones too): the link opens all
	// of the reader's highlights, not one edition's.
	const highlightCount = $derived(
		marks
			.allByEdition(language)
			.filter((w) => w.kind === 'book' && w.slug === book.slug)
			.reduce((n, w) => n + w.marks.length, 0)
	);
	const nf = $derived(new Intl.NumberFormat(language));
</script>

{#if finished}
	<!-- 1. The arrival. -->
	<section class="finished-hero mt-14 rounded-card border border-border bg-surface p-6 text-center sm:p-8" aria-labelledby="finished-heading">
		<p class="eyebrow text-gold">{t('finished.eyebrow')}</p>
		<h2 id="finished-heading" class="font-display mt-2 text-h2 text-balance" dir="auto">{book.title}</h2>
		<p class="mt-1 text-small text-muted">
			{book.author.name}
			{#if book.word_count}<span aria-hidden="true"> · </span>{/if}
			{#if book.word_count}
				{t('finished.stats')
					.replace('%c%', nf.format(book.chapter_count))
					.replace('%w%', nf.format(book.word_count))}
			{/if}
		</p>
		{#if finishedThisYear}
			<a href="{localizeHref('/favorites')}#year" class="year-tile mt-6 inline-flex items-center gap-3 rounded-card px-5 py-3">
				<span class="font-display text-h2 leading-none">{nf.format(finishedThisYear)}</span>
				<span class="text-start text-small leading-snug">
					<span class="block font-semibold">{t('year.statFinished')}</span>
					<span class="block text-muted">{t('year.title')} · {year} <Arrow /></span>
				</span>
			</a>
		{/if}
		<div class="mt-6 flex flex-wrap justify-center gap-2">
			<ShareButton url={shareUrl} title={book.title} showLabel />
			<BookDownloadMenu {book} />
		</div>
	</section>

	<!-- 2. Reflect: what the reader carries away, written into their Notebook,
	     and the way back to what they marked on the way through. -->
	<section class="mt-10" aria-labelledby="finished-reflect-heading">
		<h2 id="finished-reflect-heading" class="section-heading">{t('finished.reflectHeading')}</h2>
		{#await import('$lib/components/notebook/ReflectBox.svelte') then { default: ReflectBox }}
			<ReflectBox
				prompt={t('finished.reflectPrompt')}
				title={book.title}
				collection={book.title}
				source={{ kind: 'book', slug: book.slug, order: 0, p: 0, edition: language, title: book.title, quote: '' }}
			/>
		{/await}
		{#if highlightCount}
			<a href={localizeHref('/notebook?view=highlights')} class="mt-3 inline-block text-small font-semibold text-accent hover:underline"
				>{t('finished.highlights').replace('%n%', nf.format(highlightCount))} <Arrow /></a
			>
		{/if}
	</section>

	<!-- 3. Onward, several ways: the same work for another reader, the same
	     author, a plan, and something like it. Each section only when it has
	     something to offer. -->
	{#if book.editions?.length}
		<section class="mt-10" aria-labelledby="finished-editions-heading">
			<h2 id="finished-editions-heading" class="section-heading">{t('book.otherEditions')}</h2>
			<div class="book-grid">
				{#each book.editions.slice(0, MAX) as ed (ed.slug)}
					<BookCard book={ed} />
				{/each}
			</div>
		</section>
	{/if}

	{#if picks.moreByAuthor.length}
		<section class="mt-10" aria-labelledby="finished-author-heading">
			<h2 id="finished-author-heading" class="section-heading" dir="auto">
				{t('finished.moreBy').replace('%name%', book.author.name)}
			</h2>
			<div class="book-grid">
				{#each picks.moreByAuthor as b (b.slug)}
					<BookCard book={b} />
				{/each}
			</div>
			<a href={localizeHref(authorPath(book.author.slug))} class="mt-3 inline-block text-small font-semibold text-accent hover:underline"
				>{t('finished.aboutAuthor')} <Arrow /></a
			>
		</section>
	{/if}

	{#if picks.plans.length}
		<section class="mt-10" aria-labelledby="finished-plans-heading">
			<h2 id="finished-plans-heading" class="section-heading">{t('finished.plans')}</h2>
			<ul class="flex flex-col gap-3">
				{#each picks.plans as plan (plan.slug)}
					<li>
						<a href={localizeHref(`/plans/${plan.slug}`)} class="plan-row card-lift flex items-center gap-4 rounded-card border border-border bg-surface p-4">
							<CoverStrip covers={plan.covers} max={3} />
							<span class="min-w-0">
								<span class="block font-semibold" dir="auto">{plan.title}</span>
								<span class="block text-small text-muted">{plan.day_count} {t('plans.days')}</span>
							</span>
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if picks.related.length}
		<section class="mt-10" aria-labelledby="finished-related-heading">
			<h2 id="finished-related-heading" class="section-heading">{t('book.related')}</h2>
			<div class="book-grid">
				{#each picks.related as b (b.slug)}
					<BookCard book={b} showAuthor />
				{/each}
			</div>
		</section>
	{/if}
{/if}

<style>
	.finished-hero {
		background-image: radial-gradient(
			ellipse at top,
			color-mix(in srgb, var(--gold) 12%, transparent),
			transparent 70%
		);
	}
	.year-tile {
		border: 1px solid color-mix(in srgb, var(--gold) 40%, var(--border));
		background: color-mix(in srgb, var(--gold) 6%, var(--surface));
		color: var(--text);
		text-decoration: none;
	}
	.year-tile:hover {
		border-color: var(--gold);
	}
	.plan-row {
		color: var(--text);
		text-decoration: none;
	}
</style>
