<script lang="ts">
	import { scriptureBookHref, scripturePageHref, type ScriptureBookPage } from '$lib/library-public';
	import { scriptureBookCardUrl } from '$lib/verseCard';
	import { LANDSCAPE_HEIGHT, LANDSCAPE_WIDTH } from '$lib/coverArt';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, collectionPage, hreflangFor } from '$lib/seo';
	import { relativeHeat } from '$lib/scriptureIndex';
	import { authorPath } from '$lib/originals';
	import { withTrailingSlash } from '$lib/href';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import ScriptureChapterChips from '$lib/components/ScriptureChapterChips.svelte';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	// One book of the Bible across the library: its chapter pages, the verses
	// the writers stop at, and the library books that return to it most. English
	// data, localized chrome — the chapter page's rule (see its note).
	let { data } = $props();
	const page = $derived<ScriptureBookPage>(data.page);
	const book = $derived(page.book);

	const passagesTpl = $derived(t('scripture.passagesCount'));
	const passages = (n: number) => passagesTpl.replace('%count%', String(n));
	// Shaded against this book's own chapters (relativeHeat): the brightest chip
	// is the chapter of THIS book the library cites most.
	const chapters = $derived(page.chapters.map((c) => ({ chapter: c.chapter, count: c.citing_count })));
	const heat = $derived(relativeHeat(chapters.map((c) => c.count)));

	const path = $derived(scriptureBookHref(book.slug));
	const canonical = $derived(`${SITE_URL}${path}`);
	// Only `en` is offered as an alternate, as on the chapter page.
	const hreflang = $derived(hreflangFor(path, ['en']));
	// Drawn at build by scripts/build-verse-cards.mjs from this page's own data.
	const ogImage = $derived(`${SITE_URL}${scriptureBookCardUrl(book.slug)}`);

	const title = $derived(`${book.title} — what the classics say — Ochorus`);
	const description = $derived(
		page.citing_count !== null && page.books_count !== null
			? `${page.citing_count} passage${page.citing_count === 1 ? '' : 's'} from ` +
					`${page.books_count} Christian classic${page.books_count === 1 ? '' : 's'} that treat ` +
					`${book.title}, chapter by chapter, each quoted and linked to its source.`
			: `How the Christian classics treat ${book.title}, chapter by chapter — ` +
					'every passage quoted and linked to its source.'
	);

	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('reader.scripture'), href: '/scripture' },
		{ name: book.title, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
	const collectionLd = $derived(
		collectionPage({
			name: `${book.title} in the Christian classics`,
			description,
			url: canonical,
			items: page.chapters.map((c) => ({
				name: `${book.title} ${c.chapter}`,
				url: scripturePageHref(book.slug, c.chapter, null)
			}))
		})
	);
</script>

<Seo
	{title}
	{description}
	{canonical}
	{hreflang}
	structuredData={[crumbsLd, collectionLd]}
	{ogImage}
	ogImageWidth={LANDSCAPE_WIDTH}
	ogImageHeight={LANDSCAPE_HEIGHT}
	ogImageAlt="What the classics say about {book.title} — Ochorus"
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<header class="mb-8">
		<h1 class="text-h1">{book.title}</h1>
		{#if page.citing_count !== null}
			<p class="mt-2 text-small text-muted">
				{t('scripture.treated').replace('%count%', String(page.citing_count))}
			</p>
		{/if}
	</header>

	<section class="mb-10">
		<h2 class="section-label">{t('scripture.chaptersHeading')}</h2>
		<ScriptureChapterChips {book} {chapters} {heat} {passages} />
	</section>

	{#if page.verses.length}
		<section class="mb-10">
			<h2 class="section-label">{t('scripture.versesHeading')}</h2>
			<ul class="verses">
				{#each page.verses as v (`${v.chapter}:${v.verse}`)}
					<li class="verse">
						<a href={scripturePageHref(book.slug, v.chapter, v.verse)}>
							<span class="num">{v.chapter}:{v.verse}</span>
							{#if v.text}<span class="vtext">{v.text}</span>{/if}
						</a>
						<span class="count text-small">{v.citing_count}</span>
					</li>
				{/each}
			</ul>
			{#if page.version}<p class="mt-2 text-small text-muted">{page.version}</p>{/if}
		</section>
	{/if}

	{#if page.top_books.length}
		<section>
			<h2 class="section-label">{t('scripture.booksHeading')}</h2>
			<!-- English works, linked unlocalized like CitingPassages: the citations
			     were found in the English text. -->
			<ul class="works">
				{#each page.top_books as w (w.slug)}
					<li class="work">
						<span class="min-w-0">
							<a class="work-title" href={`/books/${w.slug}/`}>{w.title}</a>
							<a class="work-author text-small" href={withTrailingSlash(authorPath(w.author_slug))}>{w.author_name}</a>
						</span>
						<span class="count text-small">{passages(w.citing_count)}</span>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	<!-- Walk the Bible book by book (adjacent books that have a page). -->
	{#if page.prev || page.next}
		<nav
			class="mt-12 flex items-stretch justify-between gap-3 border-t border-border pt-6"
			aria-label={t('scripture.bookNav')}
		>
			{#if page.prev}
				<a
					href={scriptureBookHref(page.prev.book)}
					class="btn btn-ghost flex-1 flex-col items-start gap-0.5 text-start"
				>
					<span class="eyebrow text-muted">{t('reader.previous')}</span>
					<span class="text-small">{page.prev.book_title}</span>
				</a>
			{:else}
				<span class="flex-1"></span>
			{/if}
			{#if page.next}
				<a
					href={scriptureBookHref(page.next.book)}
					class="btn btn-ghost flex-1 flex-col items-end gap-0.5 text-end"
				>
					<span class="eyebrow text-muted">{t('reader.next')}</span>
					<span class="text-small">{page.next.book_title}</span>
				</a>
			{:else}
				<span class="flex-1"></span>
			{/if}
		</nav>
	{/if}
</div>

<style>
	/* The verse rows are the chapter page's, for the same job. */
	.verses,
	.works {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.4rem;
	}
	.verse {
		display: flex;
		align-items: baseline;
		gap: 0.75rem;
		padding: 0.55rem 0.8rem;
		border-radius: var(--radius-card);
		background: var(--color-surface-2);
	}
	.verse a {
		flex: 1;
		color: inherit;
		text-decoration: none;
		display: flex;
		gap: 0.6rem;
		align-items: baseline;
	}
	.verse a:hover .vtext {
		text-decoration: underline;
	}
	.num {
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
		color: var(--color-accent);
	}
	.vtext {
		font-size: var(--fs-small);
		line-height: 1.55;
	}
	.work {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 0.5rem 0;
		border-top: 1px solid var(--color-border);
	}
	.work:first-child {
		border-top: 0;
	}
	.work-title {
		font-weight: 600;
		color: var(--color-text);
		text-decoration: none;
	}
	.work-title:hover {
		text-decoration: underline;
	}
	.work-author {
		margin-inline-start: 0.5rem;
		color: var(--color-muted);
		text-decoration: none;
	}
	.work-author:hover {
		text-decoration: underline;
	}
</style>
