<script lang="ts">
	import { chapterPath } from '$lib/editionHref';
	import Arrow from '$lib/components/Arrow.svelte';
	import ReadBar from '$lib/components/ReadBar.svelte';
	import { coverVariants, isPlateCover, shareCard, shareImage } from '$lib/coverArt';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { authorLdType, authorPath } from '$lib/originals';
	import { type BookDetail, formatLifespan } from '$lib/library-public';
	import { getProgressRecord } from '$lib/progress';
	import { furthestOf, resumeOrderOf, type ProgressRecord } from '$lib/reading-schema';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import {
		bookTimeLeft,
		chapterName,
		chapterNameIn,
		contentLang,
		readingMinutes,
		readingTime,
		workPercent
	} from '$lib/reading';
	import {
		absUrl,
		jsonLd,
		breadcrumbLd,
		pickQa,
		toQa,
		truncateMeta,
		topicThings,
		publisherLd,
		PUBLIC_DOMAIN_MARK,
		bookId,
		personId
	} from '$lib/seo';
	import QandA from '$lib/components/QandA.svelte';
	import LanguageFallbackNotice from '$lib/components/LanguageFallbackNotice.svelte';
	import { editionSeo, languageFallback } from '$lib/languageFallback';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { getLang, localeName } from '$lib/lang.svelte';
	import { scopedSearchHref } from '$lib/searchState';
	import { seriesAges, seriesLabel } from '$lib/series';
	import { scrollSpy, elementVisible, realignHashOnMeasure, subnavOffset } from '$lib/scrollSpy.svelte';
	import { tabStrip } from '$lib/actions/tabStrip';
	import { CONTENTS_COLLAPSE_AT, contentsWindow } from '$lib/contentsWindow';
	import BookCard from '$lib/components/BookCard.svelte';
	import PersonCard from '$lib/components/PersonCard.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import ArticleLinkCard from '$lib/components/ArticleLinkCard.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import AddToShelfButton from '$lib/components/AddToShelfButton.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import BookDownloadMenu from '$lib/components/BookDownloadMenu.svelte';
	import { distinctTitle, downloadFormats, titleWithFormats } from '$lib/bookSeo';
	import ProgressBar from '$lib/components/ProgressBar.svelte';

	let { data } = $props();
	const t = i18n.t;
	const book = $derived<BookDetail>(data.book);

	let record = $state<ProgressRecord | null>(null);
	$effect(() => {
		record = getProgressRecord(book.slug);
	});
	const inEdition = (order: number) => book.chapters.some((c) => c.order === order);
	const furthest = $derived(record ? furthestOf(record) : null);
	// The other chapter worth a link beside Continue: the one last opened, when
	// Continue took the reader back from a peek; the furthest reached, when
	// they went back to reread.
	const otherPlace = $derived.by(() => {
		if (!record || furthest == null || record.finished_at != null) return null;
		if (record.order > furthest && inEdition(record.order))
			return { order: record.order, label: t('book.lastOpened') };
		if (record.order < furthest && inEdition(furthest))
			return { order: furthest, label: t('book.backToFurthest') };
		return null;
	});
	// Finished (the end reached, or marked done): the card says so and offers
	// the book again from the start, not "Continue · chapter N of N".
	const finishedAt = $derived(record?.finished_at ?? null);

	// The saved place clamped to THIS edition. Progress is keyed by the bare slug
	// (workSlugKey), so it is shared across language editions — which can have
	// different chapter counts. A resume point carried over from a longer edition
	// would otherwise sit past the end here and mark every chapter "read"; keeping
	// it only when it names a chapter that actually exists in this edition leaves
	// a mismatched place showing no progress rather than a false "finished".
	// Where Continue goes: the chapter last opened, or — when that was a peek
	// past the furthest chapter reached — back to the furthest (resumeOrderOf).
	const resumeHere = $derived(record && inEdition(resumeOrderOf(record)) ? resumeOrderOf(record) : null);
	// Chapters before the furthest reached carry a check (the furthest itself
	// was reached, not necessarily finished) — clamped the same way, so a
	// longer edition's furthest doesn't tick every chapter here.
	const furthestHere = $derived(furthest != null && inEdition(furthest) ? furthest : resumeHere);

	// The cover's painting, blurred and veiled behind the hero as its colour
	// (app.css --wash-veil) — a raster cover only: a plate is the house's own
	// drawing, not a painting, and a file that fails to load leaves the plain page.
	// Its smallest webp, the one the cover itself shows at 1x: blurred to a
	// colour, the full-size original (up to ~400 KB) would be a second download
	// racing the cover for nothing.
	let washBroken = $state<string | null>(null);
	const washSrc = $derived(
		book.cover_url && !isPlateCover(book.cover_url) ? (coverVariants(book.cover_url)[0] ?? book.cover_url) : null
	);
	const wash = $derived(washSrc !== washBroken ? washSrc : null);

	const years = $derived(
		formatLifespan(book.author.birth_year, book.author.death_year, t('common.bornPrefix'))
	);

	const totalWords = $derived(book.chapters.reduce((sum, c) => sum + c.word_count, 0));

	// A saved place past chapter 1 in a book not yet finished: the read verb is
	// Continue, not Begin (a finished book is read again from the start).
	// (Or at chapter 1 with a peek further on: that reader has a place.)
	const resuming = $derived(
		finishedAt == null && resumeHere != null && (resumeHere > 1 || otherPlace != null)
	);
	const firstOrder = $derived(book.chapters[0]?.order ?? 1);
	const readOrder = $derived(resuming && resumeHere != null ? resumeHere : firstOrder);
	const readLabel = $derived(
		finishedAt != null
			? t('fav.readAgain')
			: resuming
				? t('book.continue')
				: t('book.beginReading')
	);

	// The read card: the chapter the reader is in, how far through the book
	// that is (workPercent — the same figure every other surface shows), and the
	// time left from the start of it at the reader's pace.
	const resumeChapter = $derived(book.chapters.find((c) => c.order === resumeHere));
	/** The chapter the read verb opens — where they are, or where the book begins. */
	const readChapter = $derived(book.chapters.find((c) => c.order === readOrder));
	const wordsLeft = $derived(
		resumeHere == null
			? 0
			: book.chapters.filter((c) => c.order >= resumeHere).reduce((n, c) => n + c.word_count, 0)
	);
	const minutesLeft = $derived(wordsLeft ? readingMinutes(wordsLeft) : 0);
	const onChapter = $derived(
		t('book.onChapter')
			.replace('%n%', String(readOrder))
			.replace('%t%', String(book.chapter_count))
	);
	// The same figure the home strip and /reading show (see workPercent).
	const percentRead = $derived(record ? workPercent(record, book.chapter_count) : 0);

	// A long table of contents collapses to the first and last chapters and the
	// reader's place (see contentsWindow). Hidden rows stay in the HTML — the
	// prerendered page links every chapter — and "⋯ N chapters" gaps mark them.
	let showAllChapters = $state(false);
	const visibleOrders = $derived(
		showAllChapters ? null : contentsWindow(book.chapters.map((c) => c.order), resumeHere)
	);
	// How many hidden chapters precede each visible one (the gap row above it).
	const gapBefore = $derived.by(() => {
		const gaps = new Map<number, number>();
		if (!visibleOrders) return gaps;
		let run = 0;
		for (const c of book.chapters) {
			if (visibleOrders.has(c.order)) {
				if (run) gaps.set(c.order, run);
				run = 0;
			} else run++;
		}
		return gaps;
	});

	// Whether the read card has scrolled out of view — the sticky section bar
	// shows its own read verb only then. (The card sits in the hero, so off
	// screen means scrolled past.)
	let readCard = $state<HTMLElement>();
	const cardSeen = elementVisible(() => readCard, { initial: true });

	// "Prefer Modern English" (settings): when it's on and this book has a modern
	// edition, the read CTAs open that edition (its own /modern/ address). The
	// preference is applied at the link (not in the reader) so the reader's own
	// Modern⇄Original toggle still works within a session.
	const useModern = $derived(readerPrefs.preferModern && book.has_modern_edition);
	const readHref = (order: number) =>
		localizeHref(chapterPath(book.slug, order, book.has_modern_edition));

	// Self-referential canonical + hreflang: this page is prerendered per locale,
	// so each localized copy points at ITSELF (not the English URL, which would
	// deindex the translations) and links its siblings. Books are per-language
	// rows with no English fallback, so hreflang lists only the locales this book
	// actually exists in — see hreflangFor.
	const path = $derived(`/books/${book.slug}/`);
	// A missing edition renders the English one (see languageFallback).
	const fallback = $derived(languageFallback(getLang(), book.language));
	const seo = $derived(editionSeo(path, book.available_languages, fallback));
	const hreflang = $derived(seo.hreflang);
	const canonical = $derived(seo.canonical);
	// Localized fallback, not an English literal: this page prerenders per locale,
	// so a work without a description was shipping an English <meta description>
	// and og:description at its /sw, /ar, … URL. Mirrors author.metaFallback.
	// A real editorial description is used as-is. When there is none, the localized
	// metaFallback sentence is enriched with concrete, ALREADY-localized facts — the
	// chapter count and the reading time — so a description-less book still gives the
	// SERP something specific (and a reason to click) instead of a bare "free to read"
	// line. Composed from existing localized helpers, so no new catalogue string is
	// introduced; the facts trail the sentence, so truncateMeta trims them first when
	// a long title crowds the ~160-char budget.
	//
	// A downloadable edition LEADS with that fact ("Free PDF & EPUB download."),
	// so it survives the truncation and matches the "<title> pdf" searches.
	const formats = $derived(downloadFormats(book));
	const description = $derived.by(() => {
		const lead = formats ? `${t('book.metaDownload').replace('%formats%', formats)} ` : '';
		// A hand-written snippet first: the description is the page's blurb, and
		// trimmed to 160 it ended mid-thought. The snippet is written to fit.
		if (book.meta_description) return truncateMeta(lead + book.meta_description);
		if (book.description) return truncateMeta(lead + book.description);
		const base = t('book.metaFallback')
			.replace('%title%', book.title)
			.replace('%name%', book.author.name);
		const facts = [
			book.chapter_count
				? `${book.chapter_count} ${book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')}`
				: '',
			totalWords ? readingTime(totalWords) : ''
		].filter(Boolean);
		return truncateMeta(lead + (facts.length ? `${base} ${facts.join(' · ')}.` : base));
	});
	// The same work's other-language editions, reused from the hreflang set
	// (already the intersection of available_languages with advertised locales,
	// as absolute URLs) for the Book-level translation links below.
	const enEdition = $derived(hreflang.alternates.find((a) => a.loc === 'en'));
	const siblingEditions = $derived(hreflang.alternates.filter((a) => a.loc !== book.language));
	// The hero's "also in" pill: up to three autonyms, the rest as "+N". It jumps
	// to the full list further down rather than switching language itself — a
	// reader arriving on the wrong edition needs to see, near the top, that
	// theirs exists (that list sits below Q&A, several screens down on a phone).
	const PILL_LANGS = 3;
	const editionsPill = $derived({
		names: siblingEditions.slice(0, PILL_LANGS).map((a) => ({ loc: a.loc, name: localeName(a.loc) })),
		more: Math.max(0, siblingEditions.length - PILL_LANGS)
	});
	// The <title> carries the words people actually type. It was
	// "{title} — {author} — Ochorus", which names the book and says nothing about
	// what you can do with it; the query patterns this page competes for are
	// "<title> read online free" and "<title> by <author>". Localized, and each
	// locale's wording is DERIVED from its own reviewed `book_meta_fallback`
	// rather than newly translated — same vocabulary, "on Ochorus." traded for
	// the site's "— Ochorus" title suffix.
	//
	// It runs long — about 73 characters for this book against a ~60 character
	// display budget — and the ordering is the answer to that: title, author,
	// then the qualifier, then the brand, so what truncates is the least
	// load-bearing part. A truncated title still counts for relevance.
	//
	// A downloadable edition names its formats too — see titleWithFormats.
	const titleTag = $derived(
		titleWithFormats(
			t('book.titleTag').replace('%title%', distinctTitle(book)).replace('%name%', book.author.name),
			formats
		)
	);
	// Two pictures of one edition, for two readers.
	//
	// A link preview gets the landscape CARD: Facebook, X and LinkedIn crop to
	// 1.91:1, and a 3:4 cover loses its title in that crop. The card is built
	// from the page itself at deploy (scripts/build-share-cards.mjs).
	//
	// Structured data gets the COVER — `Book.image` says what the book looks
	// like, and a cover on a blurred ground is not that. It must be a raster
	// carrying the TITLE, so a generated `.svg` and a `covers/art/` painting
	// (no words in its pixels) are both stood in for by the edition's twin; see
	// `shareImage`. The twin is per EDITION, because the title is in its
	// pixels: keyed by slug alone it once served the English cover on every
	// translated page, baked into prerendered HTML the runtime never corrects.
	// The card build reads this `Book.image` as its source, so it names the
	// cover the card is made from, too.
	const share = $derived(shareCard(book));
	const ogImage = $derived(share ? absUrl(share.url) : '');
	const cover = $derived(shareImage(book));
	const coverImage = $derived(cover ? absUrl(cover.url) : '');
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
	// What the work is ABOUT: its topical shelves, and the people it gives its
	// pages to (subject role) as the same Person nodes their author pages declare.
	const ldAbout = $derived([
		...(topicThings(book.topics ?? []) ?? []),
		...(book.featured_people ?? [])
			.filter((p) => p.role === 'subject')
			.map((p) => ({
				'@type': 'Person',
				'@id': personId(absUrl(localizeHref(authorPath(p.slug)))),
				name: p.name
			}))
	]);
	// "Ages 8–12" — the series index's wording, for a book written for young
	// readers or teens.
	const ages = $derived(book.ages ? seriesAges(book.ages) : '');
	const bookLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Book',
			// One node per edition, which each chapter's isPartOf names too.
			'@id': bookId(canonical),
			name: book.title,
			// The names this same work is published and searched under. A reader
			// looking for "A Divine Cordial" or "De Incarnatione" is looking for a
			// book on this shelf; without these the page answers to one name only.
			alternateName: book.alternate_titles?.length ? book.alternate_titles : undefined,
			author: {
				// The imprint is a publisher, not a person (see $lib/originals).
				'@type': authorLdType(book.author.slug),
				// The same node the author page declares, so the two join by id
				// rather than by a matching name.
				'@id': personId(absUrl(localizeHref(authorPath(book.author.slug)))),
				name: book.author.name,
				url: absUrl(localizeHref(authorPath(book.author.slug))),
				// The identifiers the author page asserts. Without them this Person
				// is a bare name and the book inherits none of the entity work done
				// on /authors — the two say "Athanasius" and hope a search engine
				// joins them up.
				sameAs: book.author_same_as?.length ? book.author_same_as : undefined
			},
			description: book.description || undefined,
			image: coverImage || undefined,
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
			// Who it is written for: "8-12", or "13-" for "13 and up" (schema.org's
			// open-ended form). Only on the young-reader books (`ages`).
			typicalAgeRange: book.ages
				? `${book.ages.min_age}-${book.ages.max_age ?? ''}`
				: undefined,
			// What the work is ABOUT, as opposed to what it is called — the topical
			// shelves it belongs to, which the page has always rendered as chips
			// and never told a machine. Shared topicThings shape, same as a Person's
			// `knowsAbout`.
			// The people it is about join them: a Portraits of Courage life or a
			// Key Teachings companion is BY the imprint, so this is now the only
			// place the page ties itself to its subject's Person node.
			about: ldAbout.length ? ldAbout : undefined,
			// The same shelves as a flat keyword string. `about` gives the topic
			// entities (with URLs); `keywords` is the plain-text form some engines
			// still read for topical relevance, drawn from the one source so the two
			// can't disagree.
			keywords: book.topics?.length ? book.topics.map((t) => t.title).join(', ') : undefined,
			// The series this edition belongs to, and which volume — the other half
			// of the series page's BookSeries `hasPart`, so the two point at each
			// other. `position` only in an ordered series; a collection has none.
			isPartOf: book.series
				? {
						'@type': 'BookSeries',
						name: book.series.title,
						url: absUrl(localizeHref(`/series/${book.series.slug}/`))
					}
				: undefined,
			position: book.series?.position ?? undefined,
			// `isAccessibleForFree` states the fact; this is its verb. The whole
			// book can be read here, now, without an account, and a ReadAction is
			// how that is expressed to a machine rather than implied.
			potentialAction: {
				'@type': 'ReadAction',
				target: absUrl(localizeHref(`/books/${book.slug}/1`)),
				actionStatus: 'https://schema.org/PotentialActionStatus'
			},
			datePublished: book.publication_year ? String(book.publication_year) : undefined,
			// When this edition last changed — the same date the sitemap gives.
			dateModified: book.updated_at || undefined,
			// The rights, stated only where the API can support the claim: the
			// Public Domain Mark for a public-domain work, and nothing otherwise
			// (a © work, an Original, an author too recently dead).
			license: book.public_domain ? PUBLIC_DOMAIN_MARK : undefined,
			publisher: publisherLd(),
			// The chapters as an explicit, ordered part-list — the book→chapter
			// edges the page renders as a table of contents but never declared to a
			// machine. Each is a resolvable URL with its own length.
			hasPart: book.chapters?.length
				? book.chapters.map((c) => ({
						'@type': 'Chapter',
						name: chapterName(c.order, c.title),
						position: c.order,
						url: absUrl(localizeHref(`/books/${book.slug}/${c.order}/`)),
						...(c.word_count ? { wordCount: c.word_count } : {})
					}))
				: undefined,
			// The same work in other languages, as a Book-level relationship.
			// hreflang tells crawlers the URLs are alternates; this states the
			// translation fact for the entity graph. English is treated as the
			// original: it lists its translations, a translation points back at it.
			// A non-English ORIGINAL (`public_domain`: Pascal's own French) is not
			// a translation of the English, so it claims no translationOfWork; and
			// an English AI translation of one lists no translations of its own.
			translationOfWork:
				book.language !== 'en' && book.source_type !== 'public_domain' && enEdition
					? { '@type': 'Book', inLanguage: 'en', url: enEdition.href }
					: undefined,
			workTranslation:
				book.language === 'en' && book.source_type === 'public_domain' && siblingEditions.length
					? siblingEditions.map((a) => ({ '@type': 'Book', inLanguage: a.loc, url: a.href }))
					: undefined
		})
	);
	// One crumb trail feeds both the visible <Breadcrumb> and the JSON-LD, so the
	// on-page path and the structured BreadcrumbList can't drift apart.
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.books'), href: '/books' },
		{ name: book.title, href: `/books/${book.slug}` }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));

	// Editorial Q&A: hand-authored, grounded in the work, per-language (it rides the
	// book row like about_html, so a translated edition carries its own). Books show
	// ONLY this editorial set — the derived "Common questions" fallback was dropped
	// (founder decision, questions-and-answers-plan.md §8): every Q&A shown is
	// human-authored. Content, not chrome, so it is NOT locale-gated: an es row's qa
	// is Spanish.
	const editorialQa = $derived(toQa(book.qa));

	// The one array the visible section and the FAQPage JSON-LD both read (so the
	// markup can never assert a question the page doesn't show), plus that JSON-LD.
	// The >=2 floor and the faqPage() wiring live once in pickQa; the empty second
	// arg is the (now removed) derived tier — editorial-only.
	const qa = $derived(pickQa(editorialQa, []));

	// On-page jump navigation (A3) — the author page's pattern: scrollSpy for the
	// active section, spy.jump for a smooth scroll that lands below the pinned
	// bars via the `--pinned-offset` scroll-margin contract. Entries are only the
	// sections that actually render, each labelled by its own existing localized
	// heading (the English-only FAQ aside). The bar also keeps the read CTA within
	// reach while scrolling — the page's own value over the author sub-nav.
	const hasAbout = $derived(!!(book.about_html || book.description));
	const navItems = $derived(
		[
			book.editions?.length ? { id: 'editions', label: t('book.otherEditions') } : null,
			// Shares the heading's key: the pill and the <h2> are the same words.
			book.guides?.length ? { id: 'guide', label: t('book.readersGuide') } : null,
			hasAbout ? { id: 'about', label: t('book.aboutWork') } : null,
			{ id: 'contents', label: t('reader.contents') },
			qa.items.length ? { id: 'questions', label: t('qa.sectionTitle') } : null,
			book.related?.length ? { id: 'related', label: t('book.related') } : null
		].filter((x): x is { id: string; label: string } => x != null)
	);
	const showSubnav = $derived(navItems.length >= 2);
	let subnavH = $state(0);
	// A cold #section load jumps against the bar's estimate; re-land it once measured.
	realignHashOnMeasure(() => subnavH);
	const spy = scrollSpy(() => (showSubnav ? navItems.map((n) => n.id) : []));
</script>

<Seo
	title={titleTag}
	{description}
	{canonical}
	{hreflang}
	ogType="book"
	ogTitle="{book.title} — {book.author.name}"
	{ogImage}
	ogImageWidth={share?.width}
	ogImageHeight={share?.height}
	ogImageAlt="{t('a11y.coverOf')} {book.title}"
	structuredData={[bookLd, crumbsLd, qa.ld].filter(Boolean)}
/>

<!-- The hero's band, coloured by the cover's painting (app.css --wash-veil).
     Outside the column, so the colour runs edge to edge. -->
<div class="book-band" class:washed={!!wash}>
	{#if wash}
		<div class="book-band-art" aria-hidden="true">
			<img
				src={wash}
				alt=""
				class="book-band-wash"
				use:hydrateSrc={{ src: wash }}
				onerror={() => (washBroken = wash)}
			/>
		</div>
	{/if}
	<div class="page-col book-hero-col px-5 pt-10">
		<Breadcrumb items={crumbs} />

		<LanguageFallbackNotice {fallback} alternates={hreflang.alternates} browsePath="/books" />

		<!-- A grid, so on a phone the cover sits BESIDE the title (a 9rem cover
		     alone on its row left the right half of the first screen empty) while
		     the read card and actions take the full width beneath. From sm it is the
		     original layout: cover down the left, everything else in one column. -->
		<header class="book-hero mt-5">
			<!-- One component decides what a cover is. This page used to branch on
			     cover_url itself and paint its own gradient box in the else, so the
			     same cover-less book looked one way on a shelf and another here — and
			     a cover file that 404s showed a broken image here while every shelf
			     fell back to the plate. `priority` marks it as the page's LCP image. -->
			<!-- A1: a larger cover raised off the page. `hero-cover` adds a layered
			     drop-shadow that hugs the cover's rounded shape (via `filter`, so it
			     follows any cover — painting, plate or designed raster — without a fake
			     spine drawn over the artwork) and a slim page-edge on the fore-edge. -->
			<div class="book-hero-cover">
				<div class="hero-cover">
					<BookCover {book} priority />
				</div>
				{#if book.artwork_credit}
					<!-- The painting's credit (see the foot copy below for why it is
					     shown at all): from sm it hangs under the cover it names; a
					     phone's 7rem cover column is too narrow, so there it stays at
					     the foot. -->
					<p class="mt-3 hidden text-eyebrow text-muted sm:block">{book.artwork_credit}</p>
				{/if}
			</div>

			<div class="book-hero-head min-w-0">
				<!-- Each part held whole, so a narrow column breaks BETWEEN them. -->
				<p class="eyebrow mb-1 text-muted">{t('search.typeBook')}</p>
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
				<!-- Where this book sits in its series, and the way on to the next
				     volume in this language. Absent outside a series and where the series
				     has no name in this edition's language (the API's no-fallback rule).
				     Numbers in the edition's digits, as the cover's ring sets them. -->
				{#if book.series}
					<p class="mt-2 text-small text-muted" dir="auto">
						<a
							href={localizeHref(`/series/${book.series.slug}`)}
							class="font-medium hover:text-text hover:underline"
							>{seriesLabel(book.series, contentLang(book.language))}</a
						>{#if book.series.next}<span class="px-1.5 opacity-50">·</span><a
								href={localizeHref(`/books/${book.series.next.slug}`)}
								class="text-accent hover:underline"
								>{t('book.seriesNext')}: {book.series.next.title} <Arrow /></a
							>{/if}
					</p>
				{/if}
				<!-- The space as an expression, not literal text: at an {#if} boundary a
				     literal one gets compiler-trimmed ("Booth· 1829"). And OUTSIDE the
				     nowrap span, so a narrow column breaks between the name and its dates
				     — never inside the name or the dates. -->
				<p class="mt-2 text-body">
					<a href={localizeHref(authorPath(book.author.slug))} class="text-accent hover:underline"
						>{book.author.name}</a
					>{#if years}{' '}<span class="whitespace-nowrap text-muted">{`· ${years}`}</span>{/if}
				</p>

				<!-- The author's memorable lines: a bridge from the book to their quote
				     page. English only, as the quote pages are — mirrors the author
				     page's own Quotes link, gate and all. -->
				{#if book.author_quote_count && getLang() === 'en'}
					<p class="mt-1 text-small">
						<a href={`/quotes/${book.author.slug}/`} class="text-accent hover:underline"
							>Quotes from {book.author.name} <Arrow /></a
						>
					</p>
				{/if}

				{#if siblingEditions.length && !fallback}
					<!-- Not on a fallback page: the notice above lists the editions, and
					     the section this jumps to is hidden there. -->
					<div class="mt-3">
						<a
							href="#languages"
							class="hero-chip hero-chip-link"
							onclick={(e) => spy.jump(e, 'languages', { track: false })}
							><Icon name="globe" size={15} class="shrink-0" /><span class="min-w-0"
								><!-- A hidden prefix, not aria-label: the accessible name must keep
								     the visible language names (label-in-name). --><span
									class="sr-only">{`${t('book.readInLanguage')}: `}</span
								>{#each editionsPill.names as n, i (n.loc)}{#if i}{', '}{/if}<span lang={n.loc}
										>{n.name}</span
									>{/each}{#if editionsPill.more}{` +${editionsPill.more}`}{/if}</span
							></a
						>
					</div>
				{/if}
			</div>

			<!-- The book's measure in one ribbon: its length, the time it takes,
			     how hard it reads and who it's for. Its own grid item, so on a phone
			     it takes the full width under the cover rather than squeezing into
			     the title's column beside it. Read as one line ("9 chapters, 2 hr 55
			     min read, Accessible reading difficulty"). -->
			<ul class="book-stats">
				<li>
					<span class="book-stat-value">{book.chapter_count}</span>
					<span class="book-stat-label"
						>{book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')}</span
					>
				</li>
				{#if totalWords}
					<li><span class="book-stat-value">{readingTime(totalWords)}</span></li>
				{/if}
				{#if book.difficulty}
					<li>
						<span class="book-stat-value">{t(`reader.difficulty_${book.difficulty}`)}</span>
						<span class="book-stat-label">{t('reader.difficulty')}</span>
					</li>
				{/if}
				{#if ages}
					<li><span class="book-stat-value">{ages}</span></li>
				{/if}
			</ul>

			<!-- The action row's container (`.action-host`): it picks strip vs row by
			     this block's width — the full page width on a phone. -->
			<div class="action-host book-hero-actions min-w-0">

				<!-- Design D: the header's one job for a returning reader is to put them
				     back where they were, so the read verb sits in a card that NAMES the
				     chapter they're on, with the book's progress and the time left — a
				     reason to press Continue, not just a number. A first-time reader (and
				     the prerendered HTML, since the saved place is client-only) gets the
				     same card offering chapter 1, carrying the "Free to read · No account
				     needed" reassurance that used to sit on a row of its own. Start over
				     is a quiet link: it discards the place, so it shouldn't look like a
				     second main action. -->
				<div class="read-card mt-4" bind:this={readCard}>
					<div class="read-card-body">
						{#if finishedAt != null}
							<p class="text-small text-muted">
								{t('fav.shelfFinished')} · {new Date(finishedAt).toLocaleDateString(getLang(), {
									day: 'numeric',
									month: 'long',
									year: 'numeric'
								})}
							</p>
							<p class="read-card-title" dir="auto">{book.title}</p>
							<div class="mt-2">
								<ProgressBar percent={100} label="{book.title}: {t('fav.shelfFinished')}" />
							</div>
						{:else if resuming}
							<p class="text-small text-muted">
								{onChapter}{#if minutesLeft}{` · ${bookTimeLeft(minutesLeft)}`}{/if}
							</p>
							<p class="read-card-title" dir="auto">{chapterNameIn(readOrder, resumeChapter?.title, book.title)}</p>
							<div class="mt-2">
								<ProgressBar percent={percentRead} label="{book.title}: {onChapter}" />
							</div>
						{:else}
							<p class="text-small">
								<span class="font-medium text-accent">{t('book.freeToRead')}</span><span
									class="px-1.5 opacity-50">·</span
								><span class="text-muted">{t('book.noAccount')}</span>
							</p>
							{#if book.chapters[0]}
								<p class="read-card-title" dir="auto">
									{chapterNameIn(firstOrder, book.chapters[0].title, book.title)}
								</p>
							{/if}
						{/if}
					</div>
					<div class="read-card-cta">
						<a href={readHref(readOrder)} class="btn btn-primary">{readLabel}</a>
						{#if otherPlace}
							<a href={readHref(otherPlace.order)} class="text-small text-accent hover:underline"
								>{otherPlace.label.replace('%n%', String(otherPlace.order))}</a
							>
						{/if}
						{#if resuming}
							<a href={readHref(firstOrder)} class="text-small text-muted underline hover:text-text"
								>{t('book.startOver')}</a
							>
						{/if}
						{#if book.has_modern_edition}
							<!-- Which text the read verb opens: the same choice as Settings →
							     Default edition (readerPrefs.preferModern), made here where
							     it matters, so the card holds one read button, not two. The
							     reader's own Modern ⇄ Original links and the sitemap's
							     `modern` section are how the crawler finds those pages. -->
							<div class="seg edition-seg" role="group" aria-label={t('settings.defaultEdition')}>
								<button
									type="button"
									class:active={!useModern}
									aria-pressed={!useModern}
									onclick={() => readerPrefs.setPreferModern(false)}>{t('reader.original')}</button
								>
								<button
									type="button"
									class:active={useModern}
									aria-pressed={useModern}
									onclick={() => readerPrefs.setPreferModern(true)}>{t('reader.modernEdition')}</button
								>
							</div>
						{/if}
					</div>
				</div>

				<!-- Everything else is one quiet row of five: keep it (Save, a shelf),
				     take it away (one Download menu for offline / EPUB / PDF), pass it on
				     (Share) and look inside (Search). Share and Search are icon-only on
				     desktop (`.icon-in-row`); when narrow the `.action-strip` becomes design
				     B's labelled icon strip. -->
				<div class="action-strip mt-3">
					<FavoriteButton kind="book" slug={book.slug} showLabel />
					<AddToShelfButton slug={book.slug} shortLabel />
					<BookDownloadMenu {book} />
					<div class="icon-in-row">
						<ShareButton url={canonical} title="{book.title} — {book.author.name}" showLabel />
					</div>
					<!-- Search inside this book: the real search, scoped to the book. -->
					<a
						href={localizeHref(scopedSearchHref('book', book.slug))}
						class="btn btn-sm btn-ghost icon-in-row"
						aria-label={t('search.inBook')}
						title={t('search.inBook')}
					>
						<Icon name="search" size={16} />
						<span class="btn-label">{t('nav.search')}</span>
					</a>
				</div>
				{#if book.has_leader_guide}
					<!-- A printable leader's guide for a group or a homeschool. Its own row
					     under the strip, not a sixth strip button: the strip's phone form
					     is five columns, and this is for the leader, not every reader. -->
					<div class="mt-2">
						<a
							href={localizeHref(`/books/${book.slug}/guide`)}
							class="btn btn-sm btn-ghost"
						>
							<Icon name="users" size={16} />
							{t('guide.label')}
						</a>
					</div>
				{/if}
			</div>
		</header>
	</div>
</div>
<!-- /book-band -->

<div class="page-col px-5 pb-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {subnavOffset(showSubnav, subnavH)}px)">
	<!-- A3: on-page jump navigation. Pinned under the app nav on scroll; its
	     measured height feeds `--pinned-offset` on the page column so anchored
	     sections land clear of both bars (the same contract the author sub-nav
	     uses). Only shown with ≥2 sections to move between, and it keeps the read
	     CTA reachable while scrolling — the book page's own use over the author's. -->
	{#if showSubnav}
		<nav
			bind:clientHeight={subnavH}
			class="book-subnav sticky z-(--z-pinned) mt-6 flex items-center gap-3 border-b border-border bg-bg"
			style="top: var(--appnav-h, 0px)"
			aria-label={t('a11y.pageSections')}
		>
			<ul class="tab-strip flex flex-1 gap-1" use:tabStrip={spy.active}>
				{#each navItems as item (item.id)}
					<li>
						<a
							href="#{item.id}"
							class="subnav-link subnav-link-tight"
							class:is-active={spy.active === item.id}
							aria-current={spy.active === item.id ? 'true' : undefined}
							onclick={(e) => spy.jump(e, item.id)}>{item.label}</a
						>
					</li>
				{/each}
			</ul>
			<!-- The read verb lives in the hero card; repeating it here while that
			     card is on screen put two "Continue" buttons in view. It appears
			     only once the card has scrolled away. -->
			{#if !cardSeen.visible}
				<a href={readHref(readOrder)} class="btn btn-primary subnav-cta shrink-0"
					>{resuming ? `${t('book.continueCh')} ${readOrder}` : readLabel}</a
				>
			{/if}
		</nav>
	{/if}

	<!-- Other audience editions of the SAME work — the "(For Children)" /
	     "(For Teens)" retelling and the full text it retells, cross-linked both
	     ways. Placed first in the body, not down with "More like this": a parent
	     who reached the full text needs the young-reader edition surfaced before
	     they start reading, and a child on the retelling needs the way back to
	     the original. Derived and published-gated server-side (see the API's
	     `editions`), so it renders only for the handful of works that have one.
	     The card titles already carry the "(For …)" suffix, so the grid reads as
	     the editions it is without a per-card badge. -->
	{#if book.editions?.length}
		<section id="editions" class="jump-anchor mt-8">
			<h2 class="section-heading">{t('book.otherEditions')}</h2>
			<div class="book-grid">
				{#each book.editions as ed (ed.slug)}
					<BookCard book={ed} />
				{/each}
			</div>
		</section>
	{/if}

	<!-- Reader's guide. The article(s) that explain this work — the reverse of an
	     article's Read-next funnel (see the API's `guides` / guides_for_book). Placed
	     high in the body, above "About", so a reader new to a hard classic finds the
	     orientation before they start, and so the guide earns an internal link from a
	     high-value page. Per-language: a localized edition shows its OWN translated
	     guide, or none — never the English one. Usually exactly one guide; a list
	     handles the rare extra. -->
	{#if book.guides?.length}
		<section id="guide" class="jump-anchor mt-8">
			<h2 class="section-heading">{t('book.readersGuide')}</h2>
			<ul class="mt-3 flex flex-col gap-3">
				{#each book.guides as guide (guide.slug)}
					<li><ArticleLinkCard article={guide} cta={t('book.readGuide')} /></li>
				{/each}
			</ul>
		</section>
	{/if}

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
		<section id="about" class="jump-anchor about-work mt-8" aria-labelledby="about-work">
			<h2 id="about-work" class="section-heading">{t('book.aboutWork')}</h2>
			<div class="text-body leading-relaxed" dir="auto">
				<!-- eslint-disable-next-line svelte/no-at-html-tags -->
				{@html book.about_html}
			</div>
		</section>
	{:else if book.description}
		<section id="about" class="jump-anchor mt-8" aria-labelledby="about-work">
			<h2 id="about-work" class="section-heading">{t('book.aboutWork')}</h2>
			<p class="text-body leading-relaxed" dir="auto">{book.description}</p>
		</section>
	{/if}

	<!-- The first taste of the prose itself, right under the summary: everything
	     else on this page is ABOUT the book — cover, chapter list, description,
	     the About section — and a reader deciding whether to start a
	     fourth-century treatise wants to know how it reads, before the metadata
	     band and the contents below.

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

	<!-- Explore: one metadata band between the summary and the contents, in place
	     of the two muted rows (Topics + Scripture this book treats) that used to
	     sit apart and clutter the run-up to the chapter list. Topic chips link to
	     their shelves; the scripture chips — derived from the book's own chapters,
	     so no other edition of the same public-domain text carries them — link to
	     the scripture page when one was built, else a search for the reference
	     (the chapter page's exact fallback; trailing slashes are load-bearing,
	     lib/href.test.ts). Scripture is English-only (its citations are), so a
	     localized edition shows just its topics. -->
	{#if book.topics?.length || book.scripture?.length}
		<nav class="mt-8 flex flex-wrap items-center gap-2" aria-label={t('book.explore')}>
			<span class="text-small text-muted">{t('book.explore')}</span>
			{#each book.topics ?? [] as topic (topic.slug)}
				<a href={localizeHref(`/topics/${topic.slug}`)} class="tag">{topic.title}</a>
			{/each}
			{#each book.scripture ?? [] as entry (entry.reference)}
				<a
					href={entry.page
						? `/scripture/${entry.page.book}/${entry.page.chapter}/` +
							(entry.page.verse ? `${entry.page.verse}/` : '')
						: localizeHref(`/search?q=${encodeURIComponent(entry.reference)}`)}
					class="tag"
				>
					{entry.reference}
				</a>
			{/each}
		</nav>
	{/if}

	<!-- Contents. When the reader has a saved place, each chapter shows where they
	     are in it: Continue's chapter (resumeHere) reads in the accent colour
	     (aria-current), and every chapter before the furthest one REACHED
	     (furthestHere — opened in sequence or read to its end, never a peek) carries
	     a trailing check. Both are client-only (null at prerender and for a
	     first-time reader), so the baked HTML and a new reader's view are exactly as
	     before — the markers are progressive enhancement that appears after
	     hydration. There is still no per-chapter completion record, so a check means
	     "before the furthest you got", not a claim the chapter was read end to end. -->
	<section id="contents" class="jump-anchor mt-8">
		<h2 class="section-heading">
			{t('reader.contents')}
			<span class="meta"
				>· <span class="whitespace-nowrap"
					>{book.chapter_count}
					{book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')}</span
				> · <span class="whitespace-nowrap">{readingTime(totalWords)}</span></span
			>
		</h2>
		<ol id="contents-list" class="divide-y divide-border">
			{#each book.chapters as ch (ch.order)}
				{@const read = finishedAt != null || (furthestHere != null && ch.order < furthestHere)}
				{@const current = finishedAt == null && ch.order === resumeHere}
				{@const numCls = current ? 'text-accent' : 'text-muted'}
				{@const titleCls = current ? 'text-accent font-medium' : 'text-text'}
				{@const gap = gapBefore.get(ch.order)}
				{#if gap}
					<li>
						<button
							type="button"
							class="contents-gap"
							aria-controls="contents-list"
							aria-expanded="false"
							onclick={() => (showAllChapters = true)}
						>
							⋯ {gap} {gap === 1 ? t('book.chapterOne') : t('book.chaptersMany')}
						</button>
					</li>
				{/if}
				<li class:hidden={visibleOrders != null && !visibleOrders.has(ch.order)}>
					<a
						href={readHref(ch.order)}
						class="flex items-baseline gap-3 py-2.5 hover:no-underline"
						aria-current={current ? 'step' : undefined}
					>
						<span class="w-6 shrink-0 text-small {numCls}">{ch.order}</span>
						<span class="flex-1 text-body {titleCls}" dir="auto">{chapterName(ch.order, ch.title)}</span>
						<span class="text-small text-muted">{readingMinutes(ch.word_count)} {t('common.min')}</span>
						{#if read}
							<Icon name="check" size={15} label={t('settings.heatmapRead')} class="shrink-0 text-accent" />
						{/if}
					</a>
				</li>
			{/each}
		</ol>
		{#if book.chapters.length > CONTENTS_COLLAPSE_AT}
			<button
				type="button"
				class="btn btn-sm btn-ghost mt-2"
				aria-controls="contents-list"
				aria-expanded={showAllChapters}
				onclick={() => (showAllChapters = !showAllChapters)}
			>
				{showAllChapters
					? t('search.showLess')
					: t('book.contentsShowAll').replace('%n%', String(book.chapters.length))}
			</button>
		{/if}
	</section>

	<!-- Questions and Answers. `qa.items` (editorial if present, else the derived
	     set) also feeds the FAQPage JSON-LD in <Seo> via the same pickQa call, so
	     the visible answers and the structured data stay in lockstep. The shared
	     <QandA> section id is `questions`, which the jump-nav above points at. -->
	<QandA items={qa.items} title={t('qa.sectionTitle')} headingClass="section-heading" />

	<!-- The same work in other languages, made visible to readers — until now it
	     lived only in the page's hreflang metadata. Books are per-language rows
	     sharing one slug with no English fallback, so every pill is a real,
	     published edition; `siblingEditions` is the hreflang alternate set minus
	     the edition being viewed, and localeName() gives each its autonym.
	     hreflang/lang on the link announce the target language to the reader and
	     to assistive tech. data-sveltekit-reload: a full load (the locale is
	     fixed per document — see the root layout's cross-locale guard), and no
	     hover preload, which would run this route's load in the WRONG locale. -->
	<!-- On a fallback page the notice above already lists these. -->
	{#if siblingEditions.length && !fallback}
		<section id="languages" class="jump-anchor mt-12">
			<h2 class="section-heading">{t('book.readInLanguage')}</h2>
			<div class="mt-3 flex flex-wrap items-center gap-2">
				<span class="text-small text-muted">{t('book.availableIn')}</span>
				{#each siblingEditions as ed (ed.loc)}
					<a href={ed.href} class="tag" hreflang={ed.loc} lang={ed.loc} data-sveltekit-reload>{localeName(ed.loc)}</a>
				{/each}
			</div>
		</section>
	{/if}

	<!-- People found IN this work who have a bio of their own — an anthology's
	     subjects, the figures a biography follows. Links to their author pages.
	     Language-gated server-side (a person with no bio in this edition's
	     language is dropped), so every card here is a live link. -->
	{#if book.featured_people?.length}
		<section class="mt-12">
			<h2 class="section-heading">{t('book.peopleInBook')}</h2>
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
				{#each book.featured_people as person (person.slug)}
					<PersonCard {person} />
				{/each}
			</div>
		</section>
	{/if}

	{#if book.related?.length}
		<section id="related" class="jump-anchor mt-12">
			<h2 class="section-heading">{t('book.related')}</h2>
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
		<p class="mt-2 text-eyebrow text-muted sm:hidden">{book.artwork_credit}</p>
	{/if}
</div>

<!-- Phones: once the read card scrolls away, the read verb rides a bar above
     the tab bar (ReadBar, shared with the plan page). From 640px the sticky
     sub-nav carries it instead. -->
<ReadBar
	show={!cardSeen.visible}
	hideFrom="sm"
	eyebrow={book.title}
	title={chapterNameIn(readOrder, readChapter?.title, book.title)}
	href={readHref(readOrder)}
	label={readLabel}
/>

<style>
	/* A1: lift the cover off the page. `filter: drop-shadow` follows the cover's
	   own rounded (and possibly matted, off-3:4) shape — a plain box-shadow would
	   be a rectangle behind it — so it reads for a painting, a plate and a
	   designed raster alike, with no fake spine drawn over the artwork. A slim
	   page-edge on the fore-edge, from theme tokens, implies the book's depth. */
	.hero-cover {
		position: relative;
		filter: drop-shadow(0 1px 1px rgb(0 0 0 / 0.12)) drop-shadow(0 12px 20px rgb(0 0 0 / 0.22));
	}
	.hero-cover::after {
		content: '';
		position: absolute;
		inset-block: 3%;
		inset-inline-end: -4px;
		width: 4px;
		border-radius: 0 2px 2px 0;
		background: repeating-linear-gradient(
			to right,
			var(--surface-2),
			var(--surface-2) 1px,
			var(--border) 1.5px
		);
	}

	/* The painting under everything, blurred and veiled (see --wash-veil),
	   fading out down the band so the sub-nav meets the plain page. */
	.book-band {
		position: relative;
		isolation: isolate;
		overflow: hidden;
	}
	.book-band-art {
		position: absolute;
		inset: 0;
		z-index: -1;
		mask-image: linear-gradient(to bottom, black 45%, transparent);
	}
	.book-band-art::after {
		content: '';
		position: absolute;
		inset: 0;
		background: color-mix(in srgb, var(--bg) var(--wash-veil), transparent);
	}
	.book-band-wash {
		width: 100%;
		height: 100%;
		object-fit: cover;
		filter: blur(20px) saturate(1.8);
		transform: scale(1.25);
	}
	/* Over the wash, secondary text takes a step toward the body ink — the
	   measured margin a veiled painting needs (app.css --muted-mix-on-wash). */
	.washed {
		--muted: color-mix(in srgb, var(--muted) var(--muted-mix-on-wash), var(--text));
	}

	/* The hero's layout is decided by the room the column has (a container),
	   not the viewport: the reader's page-width setting can narrow it. Row gap
	   0: the read card carries its own mt-4, as it did in the title's column.
	   A phone: the cover beside the title, the ribbon and the actions full
	   width beneath. */
	.book-hero-col {
		container: book-hero / inline-size;
	}
	.book-hero {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		column-gap: 1rem;
		align-items: start;
	}
	.book-hero-cover {
		width: 7rem;
	}
	.book-stats,
	.book-hero-actions {
		grid-column: 1 / -1;
	}
	/* From a 640px screen's column (600px inside its gutters). */
	@container book-hero (min-width: 37.5rem) {
		/* A last row takes up the cover's spare height, so the title, the
		   ribbon and the actions stack tight at the top beside it. */
		.book-hero {
			grid-template-rows: auto auto auto 1fr;
			column-gap: 1.25rem;
		}
		.book-hero-cover {
			grid-row: 1 / -1;
			width: 11rem;
		}
		.book-stats,
		.book-hero-actions {
			grid-column: 2;
		}
	}
	/* Wide: three columns — cover, the title and its ribbon, and the read
	   card, its edition toggle and the actions gathered into one raised panel. */
	@container book-hero (min-width: 56rem) {
		.book-hero {
			grid-template-columns: auto minmax(0, 1fr) 21rem;
			grid-template-rows: auto auto 1fr;
			column-gap: 2rem;
		}
		.book-hero-cover {
			width: 12rem;
		}
		.book-hero-actions {
			grid-column: 3;
			grid-row: 1 / -1;
			padding: 1.1rem;
			border: 1px solid var(--border);
			border-radius: var(--radius-card);
			background: var(--surface);
			box-shadow: var(--shadow-card);
		}
		.book-hero-actions .read-card {
			margin-top: 0;
			padding: 0;
			background: none;
		}
	}

	/* The ribbon: a quiet card of cells, each a value over its label, divided
	   by hairlines. On its own solid ground, not the wash. Every cell draws its
	   hairlines on its start and top edges, pulled 1px outside itself, and the
	   card clips them: so in a narrow column, where the cells wrap, each row
	   and column is ruled like a table with no rule along the card's own edge. */
	.book-stats {
		display: flex;
		flex-wrap: wrap;
		justify-self: start;
		max-width: 100%;
		margin: 1rem 0 0;
		padding: 0;
		list-style: none;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		overflow: hidden;
	}
	.book-stats li {
		display: flex;
		flex: 1 0 auto;
		flex-direction: column;
		justify-content: center;
		margin-block-start: -1px;
		margin-inline-start: -1px;
		padding: 0.55rem 1rem;
		border-block-start: 1px solid var(--border);
		border-inline-start: 1px solid var(--border);
	}
	.book-stat-value {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		line-height: 1.2;
	}
	.book-stat-label {
		font-size: var(--fs-eyebrow);
		color: var(--muted);
	}
	/* The edition toggle: full width under the read button, two even halves. */
	.edition-seg button {
		flex: 1 1 0;
	}
	/* The "also in" languages: a quiet chip under the byline. */
	.hero-chip {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		max-width: 100%;
		min-height: 2rem;
		padding: 0.2rem 0.7rem;
		/* Not a pill radius: in the narrow title column a chip may wrap to two
		   lines, and a 999px radius turns that into a lozenge. */
		border-radius: 1rem;
		background: var(--surface-2);
		font-size: var(--fs-small);
		color: var(--muted);
	}
	.hero-chip-link {
		color: var(--text);
		text-decoration: none;
	}
	.hero-chip-link:hover {
		background: var(--accent-soft);
		text-decoration: none;
	}

	/* The "⋯ N chapters" row standing in for a collapsed run: quiet, indented to
	   the title column, and a way to open the full list. */
	.contents-gap {
		display: block;
		width: 100%;
		padding-block: 0.35rem;
		padding-inline: 2.25rem 0;
		border: 0;
		background: transparent;
		text-align: start;
		font-size: var(--fs-small);
		color: var(--muted);
		cursor: pointer;
	}
	.contents-gap:hover {
		color: var(--text);
	}

	/* A3: jump-nav. Anchored sections clear both pinned bars via `--pinned-offset`
	   (app nav + this sticky bar, published on the page column) — the same
	   contract the author sub-nav uses. Links are quiet tabs; the active one wears
	   the accent on the shared bottom border. */
	.jump-anchor {
		scroll-margin-top: calc(var(--pinned-offset, 5rem) + 0.5rem);
	}
	.book-subnav {
		padding-block: 0.35rem 0;
	}
	.book-subnav ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}
	/* Smaller than a body button, to sit in the bar without setting its height. */
	.subnav-cta {
		padding: 0.4rem 0.85rem;
		font-size: var(--fs-small);
	}
	/* On a phone the CTA + a long "About this book" tab squeezed the tab list so
	   "Contents" was clipped to "Conte" against the button. The primary
	   Begin/Continue button lives in the hero above, so drop the sticky duplicate
	   below sm and give the section tabs the full width. */
	@media (max-width: 639.98px) {
		.subnav-cta {
			display: none;
		}
	}
</style>
