<script lang="ts">
	import { onMount } from 'svelte';
	import type { BookSummary, PlanSummary, SeriesDetail } from '$lib/library-public';
	import { allProgress } from '$lib/progress';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, hreflangExact, itemList } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import {
		BIBLE_PATH,
		BIBLE_SERIES,
		bibleChapterCount,
		bibleIn,
		biblePlace,
		bibleToContinue,
		bibleStarts,
		divisionKey,
		groupBible,
		mayBePassage,
		passageHref,
		testamentKey
	} from '$lib/bible';
	import { goto } from '$app/navigation';
	import { lookupScripture } from '$lib/scripture.svelte';
	import { searchHref } from '$lib/searchState';
	import BookCover from '$lib/components/BookCover.svelte';
	import { OWB_PATH } from '$lib/openWordBible';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import BibleCanonStrip from '$lib/components/BibleCanonStrip.svelte';
	import BibleBookList from '$lib/components/BibleBookList.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import PlanShelfCard from '$lib/components/PlanShelfCard.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import ContinueShelf from '$lib/components/ContinueShelf.svelte';
	import ContinueRow from '$lib/components/ContinueRow.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';

	/**
	 * The Bible hub: the Open Word Bible's books in the library, in canonical
	 * order, under Old Testament / New Testament and then their divisions — a
	 * grouped browse shelf on the Topics model. Only the divisions that have a
	 * book are drawn (`groupBible`), so it reads well with any part of the 66.
	 * The books are the `the-bible` series. The Bible-only plans and the series
	 * page (reading straight through, with the reader's place kept) come right
	 * after "Where to start", where a reader choosing a way in still is.
	 *
	 * The divisions draw as a compact index (`BibleBookList`: a row per book, its
	 * chapters a tap away) — 66 full covers made a phone page ~14,000px tall. The
	 * covers stay one tap away, as the book page's contents keep their list.
	 */
	let { data } = $props();
	const series = $derived<SeriesDetail | null>(data.series);
	const plans = $derived<PlanSummary[]>(data.plans);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	const groups = $derived(groupBible<BookSummary>(series?.books ?? []));
	// In the page's order, so the count, the cards and the JSON-LD agree.
	const books = $derived(groups.flatMap((g) => g.divisions.flatMap((d) => d.books)));
	const chapters = $derived(bibleChapterCount(books));
	const starts = $derived(bibleStarts(series?.books ?? []));
	// The reader's place in the Bible: device-local progress (synced when signed
	// in), read after mount and again on `ochorus:sync`, as the hubs' Continue
	// rows are. The prerender, and a first visit, have none: no Continue shelf,
	// no marked chapters.
	let ticks = $state(0);
	onMount(() => {
		const bump = () => ticks++;
		bump();
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});
	const records = $derived(ticks ? allProgress().filter((r) => r.kind === 'book') : []);
	const continues = $derived(bibleToContinue(books, records));
	const placeOf = $derived.by(() => {
		if (!records.length) return undefined;
		const bySlug = new Map(records.map((r) => [r.slug, r]));
		return (book: BookSummary) => biblePlace(book, bySlug.get(book.slug));
	});

	let asCovers = $state(false);
	// The one book whose chapters are open, across the whole index.
	let openBook = $state<string | null>(null);

	// "Go to a passage": the API parses the reference (names, abbreviations,
	// ranges) and says which reader chapter prints it (`passageHref`); a book
	// named alone opens its page (`mayBePassage`). Anything
	// that is not a passage the library prints goes to search, as the Scripture
	// hub's own finder does — so a query never dead-ends here.
	let jumpQ = $state('');
	let jumping = $state(false);
	let jumpSeq = 0;
	async function jump(e: SubmitEvent) {
		e.preventDefault();
		const q = jumpQ.trim();
		if (q.length < 2) return;
		const seq = ++jumpSeq;
		jumping = true;
		const found = mayBePassage(q) ? await lookupScripture(q) : null;
		if (seq !== jumpSeq) return;
		const href = found ? passageHref(found) : null;
		// Kept busy until the navigation lands, so Read can't fire it twice.
		await goto(localizeHref(href ?? searchHref(q)));
		if (seq === jumpSeq) jumping = false;
	}

	const path = `${BIBLE_PATH}/`;
	const canonical = `${SITE_URL}${localizeHref(path)}`;
	// Exactly the languages the series has a page in (the sitemap lists the
	// same set): no English fallback, and an error panel claims no alternates.
	// Only where the chrome links the hub too (`bibleIn`), as the sitemap does.
	const hreflang = $derived(
		series ? hreflangExact(path, series.available_languages.filter(bibleIn)) : null
	);
	const booksLd = $derived(
		itemList(
			t('nav.bible'),
			books.map((b) => ({ name: b.title, url: localizeHref(`/books/${b.slug}`) }))
		)
	);
	const crumbsLd = breadcrumbLd([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.bible'), href: path }
	]);
</script>

<Seo
	title={`${t('nav.bible')} — Ochorus`}
	description={t('bible.tagline')}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/bible.png`}
	structuredData={books.length ? [booksLd, crumbsLd] : [crumbsLd]}
/>

<svelte:head>
	{#if !books.length}
		<meta name="robots" content="noindex" />
	{/if}
</svelte:head>

<div class="page-col px-5 py-10">
	<PageHeader
		title={t('nav.bible')}
		tagline={t('bible.tagline')}
		meta={books.length ? counts : undefined}
	/>
	{#snippet counts()}
		{books.length}
		{books.length === 1 ? t('common.bookOne') : t('common.bookMany')}
		{#if chapters}
			· {chapters.toLocaleString('en')}
			{chapters === 1 ? t('book.chapterOne') : t('book.chaptersMany')}
		{/if}
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if !books.length}
		<!-- Loaded, and nothing to show: a retry could never help (the series
		     page's own split between a failure and an empty shelf). -->
		<EmptyState message={t('bible.none')} />
	{:else}
		<!-- Straight to a passage: method/action make it a site search before
		     hydration (and for anything not a passage), `jump` opens the chapter. -->
		<form class="jump" method="get" action={localizeHref('/search')} role="search" onsubmit={jump}>
			<label for="bible-jump" class="jump-label">{t('bible.jumpLabel')}</label>
			<div class="jump-row">
				<input
					id="bible-jump"
					name="q"
					type="search"
					class="field"
					autocomplete="off"
					required
					minlength={2}
					enterkeyhint="go"
					placeholder={t('bible.jumpPlaceholder')}
					bind:value={jumpQ}
					oninput={() => {
						jumpSeq++;
						jumping = false;
					}}
				/>
				<button type="submit" class="btn btn-primary" disabled={jumping} aria-busy={jumping}>
					{t('bible.jumpGo')}
				</button>
			</div>
		</form>

		{#if continues.length}
			<!-- A returning reader's way back in: the books they are partway
			     through, the chapter Continue opens named in the Bible's numbers. -->
			<div class="mb-11">
				<ContinueShelf heading={t('books.continue')}>
					{#each continues as row (row.book.slug)}
						{@const caption = `${t('continue.chapter')} ${row.chapter} ${t('plans.of')} ${row.count}`}
						<ContinueRow
							href={localizeHref(row.href)}
							title={row.book.title}
							{caption}
							verb={t('plans.continue')}
						>
							{#snippet visual()}
								<span class="w-10 shrink-0"><BookCover book={row.book} /></span>
							{/snippet}
							{#snippet progress()}
								<ProgressBar
									percent={(row.behind / row.count) * 100}
									label={`${row.book.title}: ${caption}`}
								/>
							{/snippet}
						</ContinueRow>
					{/each}
				</ContinueShelf>
			</div>
		{/if}

		{#if starts.length}
			<!-- For a first reader: a short path in, each step a book and why. -->
			<section class="starts" aria-labelledby="starts-heading">
				<h2 id="starts-heading" class="section-label">{t('bible.startHeading')}</h2>
				<p class="mb-4 text-small text-muted">{t('bible.startLede')}</p>
				<ol class="start-list">
					{#each starts as { book, why }, i (book.slug)}
						<li>
							<a class="start card-tint" href={localizeHref(`/books/${book.slug}`)}>
								<span class="start-cover"><BookCover {book} rounded="rounded-sm" /></span>
								<span class="start-text">
									<span class="start-step">{i + 1}</span>
									<span class="start-title">{book.title}</span>
									<span class="start-why">{why}</span>
								</span>
							</a>
						</li>
					{/each}
				</ol>
			</section>
		{/if}

		<!-- The ways to read the whole of it, or a book of it, a day at a time:
		     the Bible-only plans, then the series page, which reads Genesis to
		     Revelation and keeps the reader's place. -->
		<section class="mb-12" aria-labelledby="read-along-heading">
			<h2 id="read-along-heading" class="section-label mb-5">{t('bible.readAlong')}</h2>
			{#if plans.length}
				<div class="mb-6 grid items-stretch gap-x-6 gap-y-7 sm:grid-cols-2 lg:grid-cols-3">
					{#each plans as plan (plan.slug)}
						<PlanShelfCard {plan} headingLevel={3} />
					{/each}
				</div>
			{/if}
			<p class="text-small">
				<a href={localizeHref(`/series/${BIBLE_SERIES}/`)} class="font-medium text-accent hover:underline"
					>{t('bible.inOrder')} <Arrow /></a
				>
			</p>
		</section>

		<!-- The whole canon at a glance, each spine a link to its book page; the
		     grouped index below is the shelf proper. -->
		<BibleCanonStrip books={series?.books ?? []} />
		{#each groups as testament, ti (testament.testament)}
			<!-- A testament is the section; its divisions are the groups under it,
			     so their headings are h3s (the topic page's nested-group recipe). -->
			<section class="bible-testament">
				<div class="testament-head mb-5">
					<h2 class="section-label">{t(testamentKey(testament.testament))}</h2>
					{#if ti === 0}
						<!-- Covers or the compact index, for the whole list: on the first
						     heading's row, where the list begins. English, like the page's
						     other own copy: the hub exists only in BIBLE_LOCALES. Not the book
						     page's "Show as a grid", which here would read as the chapters. -->
						<button type="button" class="btn btn-sm btn-ghost" onclick={() => (asCovers = !asCovers)}>
							<Icon name={asCovers ? 'list' : 'grid'} size={16} />{asCovers
								? 'Show as a list'
								: 'Show covers'}
						</button>
					{/if}
				</div>
				{#each testament.divisions as group (group.division.id)}
					<section class="bible-division">
						<GroupHeading as="h3" name={t(divisionKey(group.division.id))} count={group.books.length} />
						{#if asCovers}
							<!-- No author line: every book is the Open Word Bible's. No series
							     line: every book is in the one series this page is. -->
							<div class="book-grid">
								{#each group.books as book (book.slug)}
									<BookCard {book} showSeries={false} />
								{/each}
							</div>
						{:else}
							<BibleBookList books={group.books} bind:open={openBook} {placeOf} />
						{/if}
					</section>
				{/each}
			</section>
		{/each}

		<!-- What the translation is, and its home: English prose, like the page
		     it opens (it exists only where the hub does). -->
		<p class="mt-12 text-small">
			<a href={localizeHref(`${OWB_PATH}/`)} class="font-medium text-accent hover:underline"
				>About the Open Word Bible <Arrow /></a
			>
		</p>
	{/if}
</div>

<style>
	.jump {
		margin: 0.25rem 0 2.25rem;
		max-width: 32rem;
	}
	.jump-label {
		display: block;
		margin-bottom: 0.4rem;
		font-size: var(--fs-small);
		font-weight: 600;
	}
	.jump-row {
		display: flex;
		gap: 0.5rem;
	}
	.jump-row .field {
		flex: 1;
		min-width: 0;
	}
	.starts {
		margin-bottom: 2.75rem;
	}
	/* Five steps: a column on a phone, a row of five from the desktop up. */
	.start-list {
		display: grid;
		gap: 0.75rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.start {
		display: flex;
		gap: 0.9rem;
		align-items: center;
		height: 100%;
		padding: 0.6rem;
		border-radius: var(--radius-card);
		color: inherit;
		text-decoration: none;
	}
	.start-cover {
		display: block;
		flex: none;
		width: 3.5rem;
	}
	.start-text {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		min-width: 0;
	}
	.start-step {
		font-size: var(--fs-eyebrow);
		font-weight: 600;
		letter-spacing: 0.08em;
		color: var(--accent);
	}
	.start-title {
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--text);
	}
	.start-why {
		font-size: var(--fs-small);
		color: var(--muted);
		line-height: 1.45;
	}
	/* After the phone rules, so it overrides them. */
	@media (min-width: 1024px) {
		.start-list {
			grid-template-columns: repeat(5, minmax(0, 1fr));
		}
		.start {
			flex-direction: column;
			align-items: flex-start;
		}
		.start-cover {
			width: 5.5rem;
		}
	}
	.testament-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}
	.testament-head h2 {
		margin-bottom: 0;
	}
	.bible-testament + .bible-testament {
		margin-top: 3rem;
	}
	.bible-division + .bible-division {
		margin-top: 2.25rem;
	}
</style>
