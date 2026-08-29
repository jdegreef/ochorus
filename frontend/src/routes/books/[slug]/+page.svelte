<script lang="ts">
	import { isArtCover, twinUrl } from '$lib/coverArt';
	import { type BookDetail, formatLifespan } from '$lib/library-public';
	import { getProgress } from '$lib/progress';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { chapterName, readingMinutes, readingTime } from '$lib/reading';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumb, hreflangFor } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { scopedSearchHref } from '$lib/searchState';
	import BookCard from '$lib/components/BookCard.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import SourceBadge from '$lib/components/SourceBadge.svelte';
	import { offlineBooks } from '$lib/offlineBooks.svelte';
	import { pwa } from '$lib/pwa.svelte';

	let { data } = $props();
	const t = i18n.t;
	const book = $derived<BookDetail>(data.book);

	// Download-for-offline state for THIS EDITION. `book.language` is the
	// language the API actually served (getBook falls back to English for a book
	// with no copy in this locale), so it is what was cached and what must be
	// asked for — not the UI locale.
	const savedOffline = $derived(offlineBooks.has(book.slug, book.language));
	const downloading = $derived(
		offlineBooks.active?.slug === book.slug && offlineBooks.active?.language === book.language
			? offlineBooks.active
			: null
	);

	let resumeOrder = $state<number | null>(null);
	$effect(() => {
		resumeOrder = getProgress(book.slug);
	});

	const years = $derived(
		formatLifespan(book.author.birth_year, book.author.death_year, t('common.bornPrefix'))
	);

	const totalWords = $derived(book.chapters.reduce((sum, c) => sum + c.word_count, 0));

	// "Prefer Modern English" (settings): when it's on and this book has a modern
	// edition, the read CTAs open that edition by carrying ?edition=modern. The
	// preference is applied at the link (not in the reader) so the reader's own
	// Modern⇄Original toggle — which represents "original" as *no* param — still
	// works within a session.
	const useModern = $derived(readerPrefs.preferModern && book.has_modern_edition);
	const readHref = (order: number) =>
		localizeHref(`/books/${book.slug}/${order}${useModern ? '?edition=modern' : ''}`);

	// Self-referential canonical + hreflang: this page is prerendered per locale,
	// so each localized copy points at ITSELF (not the English URL, which would
	// deindex the translations) and links its siblings. Books are per-language
	// rows with no English fallback, so hreflang lists only the locales this book
	// actually exists in — see hreflangFor.
	const path = $derived(`/books/${book.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const hreflang = $derived(hreflangFor(path, book.available_languages));
	// Localized fallback, not an English literal: this page prerenders per locale,
	// so a work without a description was shipping an English <meta description>
	// and og:description at its /sw, /ar, … URL. Mirrors author.metaFallback.
	const description = $derived(
		(
			book.description ||
			t('book.metaFallback')
				.replace('%title%', book.title)
				.replace('%name%', book.author.name)
		).slice(0, 300)
	);
	// The <title> carries the words people actually type. It was
	// "{title} — {author} — Ochorus", which names the book and says nothing about
	// what you can do with it; the query patterns this page competes for are
	// "<title> read online free" and "<title> by <author>". Localized, and each
	// locale's wording is DERIVED from its own reviewed `book_meta_fallback`
	// rather than newly translated — same vocabulary, "on Ochorus." traded for
	// the site's "· Ochorus" title suffix.
	//
	// It runs long — about 73 characters for this book against a ~60 character
	// display budget — and the ordering is the answer to that: title, author,
	// then the qualifier, then the brand, so what truncates is the least
	// load-bearing part. A truncated title still counts for relevance.
	const titleTag = $derived(
		t('book.titleTag').replace('%title%', book.title).replace('%name%', book.author.name)
	);
	// og:image must be raster — WhatsApp/Facebook/Twitter refuse SVG preview
	// images — and it must carry the book's TITLE, since a preview card is often
	// all a reader sees. Two covers can't stand in for themselves: a generated
	// `.svg`, and a `covers/art/` painting, which is a background the reader's
	// browser draws the type over and so has no words in the pixels. Both fall
	// back to the pre-rasterized twin.
	//
	// THE TWIN IS PER EDITION, because the title is in its pixels. Keyed by slug
	// alone, this served the ENGLISH card on every translated page — and these
	// pages are prerendered, so it was baked into the HTML a crawler reads
	// rather than something the runtime could put right. It also made the share
	// layer the one place in the app that falls back to English, which the
	// content model does not do anywhere else.
	const ogImage = $derived(
		book.cover_url && !book.cover_url.endsWith('.svg') && !isArtCover(book.cover_url)
			? absUrl(book.cover_url)
			: absUrl(twinUrl(book.slug, book.language))
	);
	const bookLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Book',
			name: book.title,
			author: {
				'@type': 'Person',
				name: book.author.name,
				url: absUrl(localizeHref(`/authors/${book.author.slug}`))
			},
			description: book.description || undefined,
			image: ogImage || undefined,
			inLanguage: book.language,
			url: canonical,
			isAccessibleForFree: true,
			numberOfPages: book.chapter_count,
			datePublished: book.publication_year ? String(book.publication_year) : undefined,
			publisher: { '@type': 'Organization', name: 'Ochorus' }
		})
	);
	// One crumb trail feeds both the visible <Breadcrumb> and the JSON-LD, so the
	// on-page path and the structured BreadcrumbList can't drift apart.
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.books'), href: '/books' },
		{ name: book.title, href: `/books/${book.slug}` }
	]);
	const crumbsLd = $derived(
		jsonLd(breadcrumb(crumbs.map((c) => ({ name: c.name, url: c.href }))))
	);
</script>

<Seo
	title={titleTag}
	{description}
	{canonical}
	{hreflang}
	ogType="book"
	ogTitle="{book.title} — {book.author.name}"
	{ogImage}
	structuredData={[bookLd, crumbsLd]}
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<header class="mt-5 flex flex-col gap-5 sm:flex-row sm:items-start">
		<!-- One component decides what a cover is. This page used to branch on
		     cover_url itself and paint its own gradient box in the else, so the
		     same cover-less book looked one way on a shelf and another here — and
		     a cover file that 404s showed a broken image here while every shelf
		     fell back to the plate. `priority` marks it as the page's LCP image. -->
		<div class="w-32 shrink-0">
			<BookCover {book} priority />
		</div>

		<div class="flex-1">
			<h1 class="text-h1" dir="auto">{book.title}</h1>
			{#if book.subtitle}<p class="mt-1 text-h3 text-muted">{book.subtitle}</p>{/if}
			<!-- Separator as an expression, not literal text: the span's leading space
			     sits at an {#if} boundary and gets compiler-trimmed, which rendered
			     "Booth· 1829" with the space missing. -->
			<p class="mt-2 text-body">
				<a href={localizeHref(`/authors/${book.author.slug}`)} class="text-accent hover:underline"
					>{book.author.name}</a
				>{#if years}<span class="text-muted">{` · ${years}`}</span>{/if}
			</p>

			<SourceBadge sourceType={book.source_type} class="mt-3" />

			<div class="mt-5 flex flex-wrap items-center gap-3">
				{#if resumeOrder && resumeOrder > 1}
					<a href={readHref(resumeOrder)} class="btn btn-primary">
						{t('book.continueCh')} {resumeOrder}
					</a>
					<a href={readHref(1)} class="btn btn-ghost">{t('book.startOver')}</a>
				{:else}
					<a href={readHref(1)} class="btn btn-primary">{t('book.beginReading')}</a>
				{/if}
				<FavoriteButton kind="book" slug={book.slug} />
				<!-- Search inside this book. Goes to the real search scoped to the
				     book rather than a second, weaker search over cached text: the
				     reader gets the same ranking, snippets and paging they get
				     everywhere else, and the scope is visible and reversible. -->
				<a
					href={localizeHref(scopedSearchHref('book', book.slug))}
					class="btn btn-ghost">{t('search.inBook')}</a
				>
				<!-- Download for offline: precache every chapter so the whole book
				     reads with no connection (see lib/offlineBooks). -->
				{#if downloading}
					<span class="btn btn-ghost cursor-default">
						{t('offline.downloading')} {Math.round((downloading.done / downloading.total) * 100)}%
					</span>
				{:else if savedOffline}
					<button
						class="btn btn-ghost"
						title={t('offline.remove')}
						onclick={() => offlineBooks.remove(book.slug, book.language)}
					>
						✓ {t('offline.saved')}
					</button>
				{:else}
					<button
						class="btn btn-ghost"
						disabled={!pwa.online}
						title={pwa.online ? undefined : t('offline.needsConnection')}
						onclick={() => offlineBooks.download(book)}
					>
						{t('offline.download')}
					</button>
				{/if}
				<!-- PDF download withdrawn (2026-07-26). 33 of the 34 books carrying a
				     pdf_url pointed at /pdfs/<slug>.pdf, and only soar-like-the-eagle.pdf
				     was ever committed to static/pdfs — every other button 404'd. The
				     rows were repointed off ochorus.com's WordPress media without the
				     files coming with them, and the earlier rel="external" was added to
				     stop the prerender crawler failing the build on exactly those missing
				     files, which hid the breakage rather than surfacing it.
				     pdf_url is left intact in the data; restore this block once the files
				     are actually hosted (and drop rel="external" then, so a missing file
				     fails the build loudly instead of shipping a dead button). -->

				{#if book.has_modern_edition}
					{@const readOrder = resumeOrder && resumeOrder > 1 ? resumeOrder : 1}
					{#if useModern}
						<!-- Primary CTA already opens modern; offer the original as the alt. -->
						<a href={localizeHref(`/books/${book.slug}/${readOrder}`)} class="btn btn-ghost">
							{t('reader.readOriginal')}
						</a>
					{:else}
						<a
							href={localizeHref(`/books/${book.slug}/${readOrder}?edition=modern`)}
							class="btn btn-ghost"
						>
							{t('book.readModern')}
						</a>
					{/if}
				{/if}
				<span class="text-small text-muted">
					{book.chapter_count}
					{book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')} · {readingTime(
						totalWords
					)}{#if book.difficulty}&nbsp;·
						<span title={t('reader.difficulty')}>{t(`reader.difficulty_${book.difficulty}`)}</span>{/if}
				</span>
			</div>
		</div>
	</header>

	{#if book.author.bio}
		<p class="mt-6 max-w-xl text-body text-muted" dir="auto">{book.author.bio}</p>
	{/if}

	{#if book.topics?.length}
		<nav class="mt-6 flex flex-wrap items-center gap-2" aria-label={t('topics.title')}>
			<span class="text-small text-muted">{t('topics.title')}:</span>
			{#each book.topics as topic (topic.slug)}
				<a
					href={localizeHref(`/topics/${topic.slug}`)}
					class="rounded-full border border-border px-3 py-1 text-small text-muted hover:border-accent hover:text-accent hover:no-underline"
				>
					{topic.title}
				</a>
			{/each}
		</nav>
	{/if}

	<section class="mt-8">
		<h2 class="mb-3 text-h3">{t('reader.contents')}</h2>
		<ol class="divide-y divide-border">
			{#each book.chapters as ch (ch.order)}
				<li>
					<a
						href={localizeHref(`/books/${book.slug}/${ch.order}`)}
						class="flex items-baseline gap-3 py-2.5 hover:no-underline"
					>
						<span class="w-6 shrink-0 text-small text-muted">{ch.order}</span>
						<span class="flex-1 text-body text-text" dir="auto">{chapterName(ch.order, ch.title)}</span>
						<span class="text-small text-muted">{readingMinutes(ch.word_count)} {t('common.min')}</span>
					</a>
				</li>
			{/each}
		</ol>
	</section>

	{#if book.related?.length}
		<section class="mt-12">
			<h2 class="mb-4 text-h3">{t('book.related')}</h2>
			<div class="book-grid">
				{#each book.related as rel (rel.slug)}
					<BookCard book={rel} showAuthor />
				{/each}
			</div>
		</section>
	{/if}

	{#if book.source_url && book.source_type === 'public_domain'}
		<p class="mt-8 text-small text-muted">
			{t('book.publicDomain')}
			<a href={book.source_url} target="_blank" rel="noreferrer">{t('book.originalEdition')}</a>.
		</p>
	{:else if book.source_url}
		<p class="mt-8 text-small text-muted">
			{t('book.translationOf')}
			<a href={book.source_url} target="_blank" rel="noreferrer">{t('book.originalEdition')}</a>.
		</p>
	{/if}

	{#if book.artwork_credit}
		<!-- The painter, for the covers that wear a real painting. This used to sit
		     in the composited SVG's <desc>, where nothing surfaced it. The art is
		     Met Open Access (CC0) so the credit isn't owed — it is simply right,
		     and it is the provenance a reader would otherwise have to take on
		     trust. Not translated: it is a name, a title and a year. -->
		<p class="mt-2 text-eyebrow text-muted">{book.artwork_credit}</p>
	{/if}
</div>
