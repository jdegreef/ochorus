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
	import PersonCard from '$lib/components/PersonCard.svelte';
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
	// Watson's *All Things for Good* carries "A Divine Cordial" as its SUBTITLE
	// and as an alternate title, so the page printed it twice, two lines apart.
	// Dropped from the visible line, NOT from `alternateName`: a subtitle does
	// not assert that the string names the same work, which is the whole claim
	// the markup makes — and the page still shows the words, so markup and page
	// still agree.
	const otherTitles = $derived(
		(book.alternate_titles ?? []).filter(
			(n) => n.toLowerCase() !== (book.subtitle ?? '').trim().toLowerCase()
		)
	);
	const bookLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Book',
			name: book.title,
			// The names this same work is published and searched under. A reader
			// looking for "A Divine Cordial" or "De Incarnatione" is looking for a
			// book on this shelf; without these the page answers to one name only.
			alternateName: book.alternate_titles?.length ? book.alternate_titles : undefined,
			author: {
				'@type': 'Person',
				name: book.author.name,
				url: absUrl(localizeHref(`/authors/${book.author.slug}`)),
				// The identifiers the author page asserts. Without them this Person
				// is a bare name and the book inherits none of the entity work done
				// on /authors — the two say "Athanasius" and hope a search engine
				// joins them up.
				sameAs: book.author_same_as?.length ? book.author_same_as : undefined
			},
			description: book.description || undefined,
			image: ogImage || undefined,
			inLanguage: book.language,
			url: canonical,
			isAccessibleForFree: true,
			// A digital edition, said plainly. It is also what distinguishes these
			// from the print editions that dominate a title query.
			bookFormat: 'https://schema.org/EBook',
			// `numberOfPages: chapter_count` was here, and it was simply false —
			// On the Incarnation has 57 chapters and nothing resembling 57 pages,
			// and a page count is a physical fact this edition does not have.
			// `wordCount` is the true measure of the same thing, is defined on
			// CreativeWork, and the page already computes it for the reading time.
			wordCount: totalWords || undefined,
			// What the work is ABOUT, as opposed to what it is called — the topical
			// shelves it belongs to, which the page has always rendered as chips
			// and never told a machine.
			about: book.topics?.length
				? book.topics.map((t) => ({
						'@type': 'Thing',
						name: t.title,
						url: absUrl(localizeHref(`/topics/${t.slug}`))
					}))
				: undefined,
			// `isAccessibleForFree` states the fact; this is its verb. The whole
			// book can be read here, now, without an account, and a ReadAction is
			// how that is expressed to a machine rather than implied.
			potentialAction: {
				'@type': 'ReadAction',
				target: absUrl(localizeHref(`/books/${book.slug}/1`)),
				actionStatus: 'https://schema.org/PotentialActionStatus'
			},
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
			<!-- The names this work is also published under. Shown, not merely marked
			     up: a reader who searched "A Divine Cordial" and landed on a page
			     headed "All Things for Good" needs to see, on arrival, that they are
			     in the right place. Held to one line — it is confirmation, not a
			     second title, and it sits above the author so it reads as part of
			     naming the work rather than as a fact about it. -->
			{#if otherTitles.length}
				<p class="mt-1 text-small text-muted" dir="auto">
					{t('book.otherTitles')}: {otherTitles.join(' · ')}
				</p>
			{/if}
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

	<!-- About this book. The page previously said nothing about the WORK: the
	     book's own `description` fed the meta tag and the JSON-LD and was never
	     rendered, while the AUTHOR's bio was. So a reader arriving on a
	     fourth-century treatise met the chapter list and a paragraph about
	     Athanasius, and nothing about the book itself.

	     The author's summary has since been dropped from this page entirely. It
	     sat directly under this heading in muted type, which read as a second
	     paragraph of the book's own prose — E. M. Bounds's dates and Civil War
	     chaplaincy presented as if they were part of what "Prayer and Praying
	     Men" is about. It belongs on the author page, which the byline links to.

	     No `max-w-*`: this band runs the full page width, aligning with the
	     Contents list below it. That is wider than a reading measure, which is
	     the deliberate trade — this is a metadata band the reader scans, not a
	     surface they settle into, and the ragged right edge against a
	     full-width table of contents read worse than the long line does.

	     Falls back to `description` exactly as the author page falls back from
	     bio_html to bio, so the 63 books with a description gain visible prose
	     today rather than waiting for a long-form piece to be written. -->
	{#if book.about_html}
		<section class="about-work mt-8" aria-labelledby="about-work">
			<h2 id="about-work" class="mb-3 text-h3">{t('book.aboutWork')}</h2>
			<div class="text-body leading-relaxed" dir="auto">
				<!-- eslint-disable-next-line svelte/no-at-html-tags -->
				{@html book.about_html}
			</div>
		</section>
	{:else if book.description}
		<section class="mt-8" aria-labelledby="about-work">
			<h2 id="about-work" class="mb-3 text-h3">{t('book.aboutWork')}</h2>
			<p class="text-body leading-relaxed" dir="auto">{book.description}</p>
		</section>
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

	<!-- The first taste of the prose itself. Everything else on this page is
	     ABOUT the book — cover, chapter list, description, the About section —
	     and a reader deciding whether to start a fourth-century treatise wants
	     to know how it reads.

	     Named with its chapter, because an unattributed paragraph leaves the
	     reader unable to tell the opening of the book from something plucked
	     out of the middle. Blockquote, not body text: it is the author's voice,
	     not the page's, and the page has just been speaking in its own.

	     Absent for three books whose front matter yields no clean prose. Server
	     owns that judgement (library/opening.py); the page just renders what it
	     is given. -->
	{#if book.opening}
		<figure class="mt-8 max-w-xl border-s-2 border-border ps-4">
			<blockquote class="text-body leading-relaxed" dir="auto">
				{book.opening.text}
			</blockquote>
			<figcaption class="mt-2 text-small text-muted" dir="auto">
				{t('book.openingFrom').replace('%chapter%', book.opening.chapter)}
			</figcaption>
		</figure>
	{/if}

	<!-- Scripture this book treats. Derived from the book's own chapters rather
	     than declared, which is why no other edition of the same public-domain
	     text carries it — and it turns every book page into a way into the
	     scripture graph, which until now was reachable only from chapter pages
	     and the sitemap.

	     Chips match the chapter page's scripture row exactly, including its
	     fallback: a chip links to its scripture page when one exists, and to a
	     search for the reference when the corpus floor withheld one — never to a
	     page that was not built. Trailing slashes are load-bearing; the bare
	     form costs a 301 (see lib/href.test.ts).

	     English editions only; `scripture` is empty elsewhere because the
	     citations behind it are English. -->
	{#if book.scripture?.length}
		<nav
			class="mt-6 flex flex-wrap items-center gap-2"
			aria-label={t('book.scriptureTreats')}
		>
			<span class="text-small text-muted">{t('book.scriptureTreats')}:</span>
			{#each book.scripture as entry (entry.reference)}
				<a
					href={entry.page
						? `/scripture/${entry.page.book}/${entry.page.chapter}/` +
							(entry.page.verse ? `${entry.page.verse}/` : '')
						: localizeHref(`/search?q=${encodeURIComponent(entry.reference)}`)}
					class="rounded-full border border-border px-3 py-1 text-small text-muted hover:border-accent hover:text-accent hover:no-underline"
				>
					{entry.reference}
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

	<!-- People found IN this work who have a bio of their own — an anthology's
	     subjects, the figures a biography follows. Links to their author pages.
	     Language-gated server-side (a person with no bio in this edition's
	     language is dropped), so every card here is a live link. -->
	{#if book.featured_people?.length}
		<section class="mt-12">
			<h2 class="mb-4 text-h3">{t('book.peopleInBook')}</h2>
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
				{#each book.featured_people as person (person.slug)}
					<PersonCard {person} />
				{/each}
			</div>
		</section>
	{/if}

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
