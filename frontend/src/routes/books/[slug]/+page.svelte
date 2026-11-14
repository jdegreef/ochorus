<script lang="ts">
	import { assetUrl } from '$lib/assetUrl';
	import ForPromo from '$lib/components/ForPromo.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import ReadBar from '$lib/components/ReadBar.svelte';
	import { coverVariants, isPlateCover, shareCard, shareImage } from '$lib/coverArt';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { authorLdType, authorPath, isImprint } from '$lib/originals';
	import { type BookDetail, formatLifespan, isTranslated } from '$lib/library-public';
	import { getProgressRecord, restartWork } from '$lib/progress';
	import {
		bookChapterPath,
		furthestOf,
		isFinishedNow,
		lastFinishOf,
		resumeOrderOf,
		type ProgressRecord
	} from '$lib/reading-schema';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import {
		bookTimeLeft,
		chapterCount,
		chapterName,
		chapterNameIn,
		contentLang,
		readingMinutes,
		readingTime,
		listenTime,
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
	import { chapterBars, chapterRangeText } from '$lib/chapterLengths';
	import { firstSentence } from '$lib/firstSentence';
	import { partEnds, partGroups, partLine } from '$lib/bookParts';
	import { chapterGridFor, chapterNumber } from '$lib/chapterGrid';
	import BookCard from '$lib/components/BookCard.svelte';
	import { editionFamily, RUNG_LABEL } from '$lib/audienceHub';
	import SeriesSegments from '$lib/components/SeriesSegments.svelte';
	import BibleBookNav from '$lib/components/BibleBookNav.svelte';
	import { BIBLE_SERIES } from '$lib/bible';
	import JourneyMap from '$lib/components/JourneyMap.svelte';
	import { journeyMapFor } from '$lib/journeyMaps';
	import type { BookSummary } from '$lib/library-public';
	import PersonCard from '$lib/components/PersonCard.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import Portrait from '$lib/components/Portrait.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { listen } from '$lib/listen.svelte';
	import { listenBookFor, requestBookListen } from '$lib/listenBook';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import GiftBookButton from '$lib/components/GiftBookButton.svelte';
	import CitePanel from '$lib/components/CitePanel.svelte';
	import AboutThisText from '$lib/components/AboutThisText.svelte';
	import AddToShelfButton from '$lib/components/AddToShelfButton.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import BookDownloadMenu from '$lib/components/BookDownloadMenu.svelte';
	import { distinctTitle, downloadFormats, titleWithFormats } from '$lib/bookSeo';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import { auth } from '$lib/auth.svelte';
	import { adminWorkHref } from '$lib/adminLinks';

	let { data } = $props();
	const t = i18n.t;
	const book = $derived<BookDetail>(data.book);

	let record = $state<ProgressRecord | null>(null);
	$effect(() => {
		record = getProgressRecord(book.slug);
	});
	// A dated devotional's read card names today, not its January chapter —
	// the reader's local date, so only once in the browser (the page is
	// prerendered; the build would bake the day it ran).
	let todayLabel = $state('');
	// Reset for every book: the page instance is reused across client-side
	// navigation, so an ordinary book must not inherit a devotional's date.
	$effect(() => {
		todayLabel = book.daily
			? new Date().toLocaleDateString(contentLang(book.language), { day: 'numeric', month: 'long' })
			: '';
	});
	const inEdition = (order: number) => book.chapters.some((c) => c.order === order);
	const furthest = $derived(record ? furthestOf(record) : null);
	// The other chapter worth a link beside Continue: the one last opened, when
	// Continue took the reader back from a peek; the furthest reached, when
	// they went back to reread.
	const otherPlace = $derived.by(() => {
		if (!record || furthest == null || finishedAt != null) return null;
		if (record.order > furthest && inEdition(record.order))
			return { order: record.order, label: t('book.lastOpened') };
		if (record.order < furthest && inEdition(furthest))
			return { order: furthest, label: t('book.backToFurthest') };
		return null;
	});
	// Finished (the end reached, or marked done): the card says so and offers
	// the book again from the start, not "Continue · chapter N of N". A book
	// being read AGAIN is not finished here — it has a place to continue from
	// (isFinishedNow); the date shown is the latest finish.
	const finishedAt = $derived(record && isFinishedNow(record) ? lastFinishOf(record) : null);
	/** "Read again" starts a new read-through (restartWork) as it opens the
	 *  first chapter, so the book is in progress again everywhere at once —
	 *  not only once the reader goes on to the next chapter. */
	const readAgain = () => {
		if (finishedAt != null) restartWork(book.slug, firstOrder);
	};

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
	// Its smallest webp (the cover's own 1x file): blurred to a colour, the
	// full-size original (up to ~400 KB) would race the cover for nothing.
	// Fetched HIGH, beside the cover, not low as it once was: the band is the
	// largest image on the page, so it is what the browser times as the LCP
	// (measured on phone and desktop alike), and `low` held exactly that paint
	// back. On a 1x screen it is the cover's own file — one request for both.
	let washBroken = $state<string | null>(null);
	const washSrc = $derived(
		book.cover_url && !isPlateCover(book.cover_url) ? (coverVariants(book.cover_url)[0] ?? book.cover_url) : null
	);
	const wash = $derived(washSrc !== washBroken ? washSrc : null);

	const years = $derived(
		formatLifespan(book.author.birth_year, book.author.death_year, t('common.bornPrefix'))
	);

	const totalWords = $derived(book.chapters.reduce((sum, c) => sum + c.word_count, 0));
	// The book's measure — its length and the time it takes — whichever it
	// has. One list for the meta description and the hero's facts line.
	const measureFacts = $derived(
		[book.chapter_count ? chapterCount(book.chapter_count) : '', totalWords ? readingTime(totalWords) : ''].filter(
			Boolean
		)
	);

	// A saved place past chapter 1 in a book not yet finished: the read verb is
	// Continue, not Begin (a finished book is read again from the start).
	// (Or at chapter 1 with a peek further on: that reader has a place.)
	const resuming = $derived(
		finishedAt == null && resumeHere != null && (resumeHere > 1 || otherPlace != null)
	);
	const firstOrder = $derived(book.chapters[0]?.order ?? 1);
	// A book of the Bible offers to be listened to straight through, where this
	// browser can read aloud at all (`listen.offered`: always in the prerender).
	const listenWhole = $derived(listenBookFor(book) && listen.offered);
	const readOrder = $derived(resuming && resumeHere != null ? resumeHere : firstOrder);
	/** A first-time reader (and the prerender): nothing to resume or re-read. */
	const fresh = $derived(finishedAt == null && !resuming);
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
	// A book of the Bible lists its chapters as numbered chips (1 … 150 for
	// Psalms) — its titles are only "<Book> <n>" — with the full list a tap
	// away for a reader who wants each chapter's length ($lib/chapterGrid).
	let contentsAsList = $state(false);
	const chipGrid = $derived(chapterGridFor(book) && !contentsAsList);
	// A book in parts (`Book.parts`, The Pilgrim's Progress) lists each part
	// under its own heading; any other book is one group with no heading. The
	// collapse keeps each part's first and last chapter, so no gap runs across
	// a part boundary and no heading stands over nothing.
	const contentsGroups = $derived(partGroups(book.chapters, book.parts));
	const parted = $derived(contentsGroups.some((g) => g.part));
	const visibleOrders = $derived(
		showAllChapters
			? null
			: contentsWindow(
					book.chapters.map((c) => c.order),
					resumeHere,
					partEnds(contentsGroups)
				)
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
	// A list short enough to show whole (≤ CONTENTS_COLLAPSE_AT) splits into two
	// columns from md (design review #9) — past a handful of rows, where one
	// column of short titles left the page's end side empty. Filled down the
	// first column, then the second (a contents list reads downward), so each
	// column's first and last rows are known here: the path's line stops at them.
	// Not a book in parts: each part's heading would land mid-column.
	const twoColumns = $derived(
		!parted && book.chapters.length >= 6 && book.chapters.length <= CONTENTS_COLLAPSE_AT
	);
	// A part per chapter in the place bar while the parts stay legible.
	const SEGMENTS_MAX = 24;
	const contentsRows = $derived(twoColumns ? Math.ceil(book.chapters.length / 2) : book.chapters.length);

	// Whether the read card has scrolled out of view — the sticky section bar
	// shows its own read verb only then. (The card sits in the hero, so off
	// screen means scrolled past.)
	let readCard = $state<HTMLElement>();
	const cardSeen = elementVisible(() => readCard, { initial: true });

	// "Prefer Modern English" (settings): when it's on and this book has a modern
	// edition, the read CTAs open that edition (its own /modern/ address). The
	// preference is applied at the link (not in the reader) so the reader's own
	// Modern⇄Original toggle still works within a session. The read card's own
	// toggle picks for THIS book only (`modernHere`), over the preference —
	// trying the modern edition of one book shouldn't flip the site default.
	// Keyed by slug: the page component is reused from one book to the next.
	let modernHere = $state<{ slug: string; modern: boolean } | null>(null);
	const useModern = $derived(
		!!book.has_modern_edition &&
			(modernHere?.slug === book.slug ? modernHere.modern : readerPrefs.preferModern)
	);
	const readHref = (order: number) => localizeHref(bookChapterPath(book.slug, order, useModern));

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
		const facts = measureFacts;
		return truncateMeta(lead + (facts.length ? `${base} ${facts.join(' · ')}.` : base));
	});
	// The same work's other-language editions, reused from the hreflang set
	// (already the intersection of available_languages with advertised locales,
	// as absolute URLs) for the Book-level translation links below.
	const enEdition = $derived(hreflang.alternates.find((a) => a.loc === 'en'));
	const siblingEditions = $derived(hreflang.alternates.filter((a) => a.loc !== book.language));
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
	// The hero's one facts line: the measure, then how hard it reads and who
	// it's for — whichever of them the book has. The difficulty word carries
	// its label as a title (as the sermon page's does): "Advanced" alone does
	// not say what is advanced.
	const heroFacts = $derived(
		[
			...measureFacts.map((text) => ({ text, title: undefined })),
			book.difficulty
				? { text: t(`reader.difficulty_${book.difficulty}`), title: t('reader.difficulty') }
				: null,
			ages ? { text: ages, title: undefined } : null
		].filter((f) => f !== null)
	);
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
	// The other-language row renders only off a fallback page (the notice
	// there lists the editions itself).
	const showLanguages = $derived(siblingEditions.length > 0 && !fallback);
	// The young-reader family (full ⇄ teens ⇄ children), youngest first — the
	// API's `editions` (serializers.sibling_editions) plus this edition.
	const family = $derived(book.editions?.length ? editionFamily<BookSummary>(book, book.editions) : []);
	// One Editions section (design review #22): the family's cards, then the
	// "Also in" languages — whichever of the two this edition has.
	const hasEditions = $derived(family.length > 0 || showLanguages);
	// The hero's pointer when there is ONE other language: that language named
	// ("Also in Español", Hindi "Español में भी") — its own message, since the
	// name's place in the phrase differs by locale. Split around %lang% so the
	// name can carry its own lang/dir.
	const alsoInOne = $derived.by(() => {
		if (siblingEditions.length !== 1) return null;
		const loc = siblingEditions[0].loc;
		const [before, after = ''] = t('book.alsoInOne').split('%lang%');
		return { loc, name: localeName(loc), before, after };
	});
	// "At a glance" (top-50 #3): the empty end side of a wide hero holds the
	// book's first line, its chapters as bars and the "Also in" link — all of
	// it from the page's own payload, no further fetch. Only from the hero's
	// wide container step (CSS); below it the panel is hidden, since About's
	// opening aside, Contents and the facts line's link already say the same
	// further down a phone's page.
	const firstLine = $derived(book.opening ? firstSentence(book.opening.text) : '');
	const bars = $derived(
		chapterBars(
			book.chapters.map((c) => c.word_count),
			readingMinutes
		)
	);
	const hasGlance = $derived(!!firstLine || !!bars);
	// No "about the author" band for a byline that is not a person (the house
	// imprint, the Bible's translation): its name links to its own page instead.
	const hasAuthorBand = $derived(!isImprint(book.author));
	// What About's foot carries (the guide link, other titles, topics,
	// scripture) — shown on its own when the book has no prose to sit under.
	const hasAboutFoot = $derived(
		!!(book.guides?.length || otherTitles.length || book.topics?.length || book.scripture?.length)
	);
	// The sections in the order a reader decides (design review #9): About →
	// Contents → Editions → Author → Q&A. Five at most and no counts: a sixth
	// tab and two counts made the bar a second menu, and "More like this" is the
	// page's end, not a place to jump to. A pill shares its section <h2>'s key
	// (the same words) wherever the heading is a label; the author band's
	// heading is the author's name, so its pill is the plain noun "Author".
	const navItems = $derived(
		[
			hasAbout ? { id: 'about', label: t('book.aboutWork') } : null,
			{ id: 'contents', label: t('reader.contents') },
			hasEditions ? { id: 'editions', label: t('book.editions') } : null,
			hasAuthorBand ? { id: 'author', label: t('search.typeAuthor') } : null,
			qa.items.length ? { id: 'questions', label: t('qa.sectionTitle') } : null
		].filter((x): x is { id: string; label: string } => x != null)
	);
	const showSubnav = $derived(navItems.length >= 2);

	const authorHref = $derived(localizeHref(authorPath(book.author.slug)));
	// Where this book fell in its author's life, as a share of the line from
	// birth to death — when all three years are known and in order. Its own
	// small line, not the author page's LifeTimeline: that one's SVG scales to
	// its column, and in this band's narrow one its years drew at ~7px.
	const lifeline = $derived.by(() => {
		const { birth_year: b, death_year: d } = book.author;
		const y = book.publication_year;
		return b && d && y && b < y && y < d ? ((y - b) / (d - b)) * 100 : null;
	});

	// One reading of the reader's place for the contents' bar and its rows.
	// The chapter they're in wins over "read" (a reader who went back to
	// reread is IN that chapter), and only a reader with a place (`resuming`,
	// the read verb's own test) has one.
	// An allegory's road, for the books that have one drawn ($lib/journeyMaps):
	// the reader's place on it is the same saved place the contents mark.
	const journeyMap = $derived(journeyMapFor(book.slug, book.language));
	const journeyPlace = $derived({
		current: resumeHere,
		furthest: furthestHere,
		finished: finishedAt != null
	});

	const isCurrent = (order: number) => resuming && order === resumeHere;
	const isRead = (order: number) =>
		!isCurrent(order) && (finishedAt != null || (furthestHere != null && order < furthestHere));
	/** The place in words — the read card's line, said again over the contents. */
	const placeLine = $derived(
		finishedAt != null ? t('fav.shelfFinished') : `${onChapter}${minutesLeft ? ` · ${bookTimeLeft(minutesLeft)}` : ''}`
	);
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
		{@const src = assetUrl(wash)}
		<div class="book-band-art" aria-hidden="true">
			<img
				{src}
				alt=""
				class="book-band-wash"
				fetchpriority="high"
				decoding="async"
				use:hydrateSrc={{ src }}
				onerror={() => (washBroken = wash)}
			/>
		</div>
	{/if}
	<div class="page-col book-hero-col px-5 pt-10">
		<Breadcrumb items={crumbs} />

		<LanguageFallbackNotice {fallback} alternates={hreflang.alternates} browsePath="/books" />

		<!-- Two columns (design review #6). A grid, so on a phone the cover sits
		     BESIDE the title block (a 9rem cover alone on its row left the right
		     half of the first screen empty) while the read card and actions take
		     the full width straight beneath it. From sm: the cover down the start
		     side, everything else in one column beside it. -->
		<header class="book-hero mt-5">
			<!-- One component decides what a cover is. This page used to branch on
			     cover_url itself and paint its own gradient box in the else, so the
			     same cover-less book looked one way on a shelf and another here — and
			     a cover file that 404s showed a broken image here while every shelf
			     fell back to the plate. `priority`: it is the page's main image, fetched
			     high beside the wash above (which, being larger, is what the browser
			     times as the LCP). -->
			<!-- A1: a larger cover raised off the page. `hero-cover` adds a layered
			     drop-shadow that hugs the cover's rounded shape (via `filter`, so it
			     follows any cover — painting, plate or designed raster — without a fake
			     spine drawn over the artwork) and a slim page-edge on the fore-edge. -->
			<div class="book-hero-cover">
				<!-- data-cover-landing: where a tapped shelf cover flies to ($lib/coverFlight). -->
				<div class="hero-cover" data-cover-landing>
					<BookCover {book} priority />
				</div>
			</div>

			<div class="book-hero-head min-w-0">
				<p class="eyebrow mb-1 text-muted">{t('search.typeBook')}</p>
				<h1 class="text-h1" dir="auto" lang={contentLang(book.language)}>{book.title}</h1>
				{#if book.subtitle}<p class="mt-1 text-h3 text-muted">{book.subtitle}</p>{/if}
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
						>{#if book.series.next}<span class="sep px-1.5">·</span><a
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
					<a href={authorHref} class="text-accent hover:underline"
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

				<!-- The book's measure in one muted line ("13 chapters · 9 hr 22 min ·
				     Accessible"), not a ribbon of boxed cells (design review #6): the
				     facts read in one glance. Each fact nowrap, so a narrow column breaks
				     between them, never inside one.

				     The other languages end it as one quiet link, "Also in 5 languages",
				     that jumps to the Editions section (design review #22) — not the
				     chip of autonyms that repeated that section's row: the languages are
				     listed ONCE, there. The pointer stays so the first screen still says
				     other languages exist, and Editions sits below Contents, screens down
				     on a phone. (A reader browsing in their own locale already lands on
				     their edition; the switcher and the fallback notice serve the rest.)
				     Not on a fallback page:
				     the notice above lists the editions, and the row is hidden there. -->
				<p class="mt-2 text-small text-muted">
					{#each heroFacts as fact, i (fact.text)}{#if i}{' · '}{/if}<span class="whitespace-nowrap" title={fact.title}
							>{fact.text}</span
						>{/each}{#if showLanguages}<span class="facts-also-in" class:in-glance={hasGlance}
							>{#if heroFacts.length}{' · '}{/if}{@render alsoInLink()}</span
						>{/if}
				</p>
			</div>
			<!-- "Also in N languages": ONE link, which the wide hero moves from the
			     facts line into the At-a-glance panel (CSS shows one of the two). -->
			{#snippet alsoInLink()}
				<a
					href="#editions"
					class="also-in-link whitespace-nowrap"
					onclick={(e) => spy.jump(e, 'editions', { track: false })}
					>{#if alsoInOne}{alsoInOne.before}<span lang={alsoInOne.loc} dir="auto">{alsoInOne.name}</span
						>{alsoInOne.after}{:else}{t('book.alsoInCount').replace('%n%', String(siblingEditions.length))}{/if}</a
				>
			{/snippet}

			<!-- At a glance (top-50 #3): the end side of a wide hero, which the
			     title block and the read card leave empty. Shown only from the
			     hero's widest container step; below it every line here is said
			     further down the page (About's opening aside, Contents, the facts
			     line's languages link), so a phone gets no longer for it. The
			     first line is the server's opening excerpt (library/opening.py),
			     cut to its first sentence. -->
			{#if hasGlance}
				<aside class="book-glance" aria-labelledby="glance-heading">
					<h2 id="glance-heading" class="eyebrow text-muted">{t('book.glance')}</h2>
					<dl class="mt-3 text-small">
						{#if firstLine}
							<div>
								<dt>{t('book.firstLine')}</dt>
								<dd class="glance-line font-display" lang={contentLang(book.language)} dir="auto">{firstLine}</dd>
								<!-- Named, because opening.py skips front matter: the line
								     may open chapter 2 or 3, not the book. -->
								<dd class="text-muted" dir="auto">
									{t('book.openingFrom').replace('%chapter%', book.opening?.chapter ?? '')}
								</dd>
							</div>
						{/if}
						{#if bars}
							<div>
								<dt>{t('book.chapterLengths')}</dt>
								<dd>
									<!-- One bar per chapter, as tall as the chapter is long. The
									     caption carries the figures for a screen reader; the
									     bars' tooltips name each chapter for a mouse. -->
									<div class="glance-bars" aria-hidden="true">
										{#each bars.heights as h, i (i)}
											{@const ch = book.chapters[i]}
											<span
												style:height="{h}%"
												title="{chapterNameIn(ch.order, ch.title, book.title)} · {readingMinutes(ch.word_count)} {t(
													'common.min'
												)}"
											></span>
										{/each}
									</div>
									<p class="mt-1 text-muted">
										{chapterRangeText(t('book.chapterRange'), bars)}
									</p>
								</dd>
							</div>
						{/if}
					</dl>
					{#if showLanguages}
						<p class="mt-4 text-small">{@render alsoInLink()}</p>
					{/if}
				</aside>
			{/if}

			<!-- The action row's container (`.action-host`): it picks strip vs row by
			     this block's width — the full page width on a phone. -->
			<div class="action-host book-hero-actions min-w-0">

				<!-- Design D: the header's one job for a returning reader is to put them
				     back where they were, so the read verb sits in a card that NAMES the
				     chapter they're on, with the book's progress and the time left — a
				     reason to press Continue, not just a number. A first-time reader (and
				     the prerendered HTML, since the saved place is client-only) gets the
				     same card as one solid button naming chapter 1 and its length, with
				     the "Free to read · No account needed" reassurance under it. Start over
				     is a quiet link: it discards the place, so it shouldn't look like a
				     second main action. -->
				<div class="read-card mt-4" bind:this={readCard}>
					{#if !fresh}
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
							{:else}
								<p class="text-small text-muted">{placeLine}</p>
								<p class="read-card-title" dir="auto">{chapterNameIn(readOrder, resumeChapter?.title, book.title)}</p>
								<div class="mt-2">
									<ProgressBar percent={percentRead} label="{book.title}: {onChapter}" />
								</div>
							{/if}
						</div>
					{/if}
					<div class="read-card-cta">
						<!-- A first-time reader: the chapter the verb opens rides in the
						     button as its second line, and the reassurance sits under it
						     as small print (design review #2), so the card is one thing
						     to press rather than a label above a pale button. The small print
						     goes under the solid button, whichever one that is. -->
						{#snippet reassurance()}
							{#if fresh}
								<p class="text-small text-muted">
									{t('book.freeToRead')}<span class="sep">{' · '}</span>{t('book.noAccount')}
								</p>
							{/if}
						{/snippet}
						{#if book.daily}
							<!-- A year-long devotional is read by the calendar: today's
							     entry is the main way in, the book from its start the
							     second (library/daily_readings). -->
							<a href={localizeHref(`/today/${book.slug}/`)} class="btn btn-primary btn-solid flex-col gap-0"
								>{t('plans.todaysReading')}{#if fresh && todayLabel}{' '}<span class="btn-sub">{todayLabel}</span
									>{/if}</a
							>
							{@render reassurance()}
						{/if}
						<!-- The space before the sub-line keeps the link's text (and its
						     accessible name) "Begin reading Book I · 35 min"; a flex
						     container drops it visually. -->
						<a
							href={readHref(readOrder)}
							onclick={readAgain}
							class="btn {book.daily ? 'btn-ghost' : 'btn-primary btn-solid'} flex-col gap-0"
							>{readLabel}{#if fresh && readChapter}{' '}<span class="btn-sub" dir="auto"
									>{chapterNameIn(readOrder, readChapter.title, book.title)}{readChapter.word_count
										? ` · ${readingMinutes(readChapter.word_count)} ${t('common.min')}`
										: ''}</span
								>{/if}</a
						>
						{#if !book.daily}{@render reassurance()}{/if}
						{#if listenWhole}
							<!-- A book of the Bible, listened to straight through: its first
							     chapter opens already reading aloud, and the reader's roll-over
							     carries it chapter by chapter ($lib/listenBook). A plain link to
							     that chapter without the script, or opened in a new tab. -->
							<a
								href={readHref(firstOrder)}
								class="btn btn-ghost flex-col gap-0"
								onclick={(e) => {
									if (!e.defaultPrevented && e.button === 0 && !(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey))
										requestBookListen(book.slug, firstOrder);
								}}
								><span class="inline-flex items-center gap-1.5"
									><Icon name="headphones" size={18} />{t('bible.listenBook')}</span
								>{#if totalWords}{' '}<span class="btn-sub">{listenTime(totalWords, listen.rate)}</span>{/if}</a
							>
						{/if}
						{#if book.daily_plan}
							<!-- The self-paced way through: day one is 1 January's
							     reading, whenever the reader begins (plan_seed.DAILY_PLANS). -->
							<a href={localizeHref(`/plans/${book.daily_plan}/`)} class="text-small text-accent hover:underline"
								>{t('daily.followPlan')}</a
							>
						{/if}
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
							<!-- Which text the read verb opens, for this book: it starts at
							     Settings → Default edition and leaves that setting alone. One
							     read button, not two. The reader's own Modern ⇄ Original links
							     and the sitemap's `modern` section lead the crawler there. -->
							<div class="seg edition-seg" role="group" aria-label={t('settings.defaultEdition')}>
								<button
									type="button"
									class:active={!useModern}
									aria-pressed={!useModern}
									onclick={() => (modernHere = { slug: book.slug, modern: false })}>{t('reader.original')}</button
								>
								<button
									type="button"
									class:active={useModern}
									aria-pressed={useModern}
									onclick={() => (modernHere = { slug: book.slug, modern: true })}>{t('reader.modern')}</button
								>
							</div>
							<!-- What Modern changes (top-50 #4), so the choice is an informed
							     one: the careful pass (contemporize-book) updates archaic forms
							     and eases long sentences; meaning, voice and Scripture stay. -->
							<p class="text-small text-muted">{t('book.modernExplainer')}</p>
						{/if}
					</div>
				</div>

				<!-- Everything else is one quiet row of six: keep it (Save, a shelf),
				     take it away (one Download menu for offline / EPUB / PDF), pass it on
				     (Share, Give) and look inside (Search). Share and Search are icon-only on
				     desktop (`.icon-in-row`); when narrow the `.action-strip` becomes design
				     B's labelled icon strip. -->
				<div class="action-strip mt-3">
					<FavoriteButton kind="book" slug={book.slug} showLabel />
					<AddToShelfButton slug={book.slug} shortLabel />
					<BookDownloadMenu {book} />
					<div class="icon-in-row">
						<ShareButton url={canonical} title="{book.title} — {book.author.name}" showLabel />
					</div>
					<!-- Give it to someone, with a note: a link that carries the gift
					     ($lib/gift) to /gift. Icon-only in the row, like Share. -->
					<div class="icon-in-row">
						<GiftBookButton slug={book.slug} language={book.language} title={book.title} />
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
				<!-- Admins only (reporting:view opens the page; the API gates it too).
				     English, like the admin it leads to. Outside the strip, which is
				     the reader's row of five. -->
				{#if auth.can('reporting')}
					<p class="mt-2 text-small">
						<a href={localizeHref(adminWorkHref('book', book.slug))} class="text-muted hover:text-accent"
							>Open in admin <Arrow /></a
						>
					</p>
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
							onclick={(e) => spy.jump(e, item.id)}
							>{item.label}</a
						>
					</li>
				{/each}
			</ul>
			<!-- The read verb lives in the hero card; repeating it here while that
			     card is on screen put two "Continue" buttons in view. It appears
			     only once the card has scrolled away. -->
			{#if !cardSeen.visible}
				<a href={readHref(readOrder)} onclick={readAgain} class="btn btn-primary btn-solid subnav-cta shrink-0"
					>{resuming ? `${t('book.continueCh')} ${readOrder}` : readLabel}</a
				>
			{/if}
		</nav>
	{/if}

	<!-- About this book. The page previously said nothing about the WORK: the
	     book's own `description` fed the meta tag and the JSON-LD and was never
	     rendered, while the AUTHOR's bio was. The author's summary has since been
	     dropped from this page entirely: under this heading it read as a second
	     paragraph of the book's own prose. It belongs on the author page, which
	     the byline links to.

	     The prose is held to a reading measure (`.about-prose`, ~65ch; design
	     review #9): across the full column it ran ~150 characters a line, which
	     people scan rather than read. From lg the opening lines stand beside it
	     as an aside; on a phone they follow it in flow.

	     Falls back to `description` exactly as the author page falls back from
	     bio_html to bio, so a book without a long-form piece still has prose. -->
	{#if hasAbout}
		<section id="about" class="jump-anchor mt-8" aria-labelledby="about-work">
			<h2 id="about-work" class="section-heading no-rule">{t('book.aboutWork')}</h2>
			<div class="about-layout">
				<div class="about-prose text-body">
					{#if book.about_html}
						<div class="about-work has-initial text-body leading-relaxed" dir="auto">
							<!-- Server-sanitised long-form piece. -->
							<!-- eslint-disable-next-line svelte/no-at-html-tags -->
							{@html book.about_html}
						</div>
					{:else if book.description}
						<!-- The initial only for a description long enough to wrap: beside a
						     one-line sentence a three-line cap hangs below the text. -->
						<div class:has-initial={book.description.length > 240} dir="auto">
							<p class="text-body leading-relaxed">{book.description}</p>
						</div>
					{/if}
					{@render aboutFoot()}
				</div>
				{@render openingLines()}
			</div>
		</section>
	{:else if hasAboutFoot}
		<div class="about-layout mt-8">
			<div class="about-prose text-body">{@render aboutFoot()}</div>
			{@render openingLines()}
		</div>
	{:else if book.opening}
		<!-- No prose and no foot: the quote alone, not stranded in the aside's
		     column beside an empty one. -->
		<div class="mt-8 max-w-xl">{@render openingLines()}</div>
	{/if}
	<!-- Under the prose: the way into the reader's guide, then the quiet
	     metadata lines.

	     The guide (the API's `guides`, the reverse of an article's Read-next
	     funnel) is one inline link, not a card section of its own that pushed
	     the description down (design review #9) — still a crawlable link from a
	     high-value page. Per-language: a localized edition shows its OWN guide,
	     or none. Usually exactly one; a rare second is named by its title.

	     The names this work is also published under serve search, not the
	     decision to read (design review #6). Topics and Scripture are lines of
	     links, not a band of chips (#9): topic shelves, and the scripture page
	     when one was built, else a search for the reference (the chapter page's
	     exact fallback; trailing slashes are load-bearing, lib/href.test.ts).
	     Scripture is English-only (its citations are). -->
	{#snippet aboutFoot()}
		{#each book.guides ?? [] as guide, i (guide.slug)}
			<p class="mt-4 text-body" dir="auto">
				<a
					href={localizeHref(`/articles/${guide.slug}/`)}
					title={i === 0 ? guide.h1 : undefined}
					class="font-medium text-accent hover:underline"
					>{i === 0 ? t('book.newToGuide').replace('%title%', book.title) : guide.h1}{'\u00a0'}<Arrow /></a
				>
			</p>
		{/each}
		{#if otherTitles.length}
			<p class="mt-3 text-small text-muted" dir="auto">
				{t('book.otherTitles')}: {otherTitles.join(' · ')}
			</p>
		{/if}
		{#if book.topics?.length}
			<p class="about-meta mt-3 text-small text-muted">
				{t('common.topics')}:
				{#each book.topics as topic, i (topic.slug)}{#if i}{', '}{/if}<a
						href={localizeHref(`/topics/${topic.slug}`)}>{topic.title}</a
					>{/each}
			</p>
		{/if}
		{#if book.scripture?.length}
			<p class="about-meta mt-1 text-small text-muted">
				{t('reader.scripture')}:
				{#each book.scripture as entry, i (entry.reference)}{#if i}{', '}{/if}<a
						class="whitespace-nowrap"
						href={entry.page
							? `/scripture/${entry.page.book}/${entry.page.chapter}/` +
								(entry.page.verse ? `${entry.page.verse}/` : '')
							: localizeHref(`/search?q=${encodeURIComponent(entry.reference)}`)}>{entry.reference}</a
					>{/each}
			</p>
		{/if}
	{/snippet}

	<!-- The first taste of the prose itself: everything else on this page is
	     ABOUT the book, and a reader deciding whether to start a fourth-century
	     treatise wants to know how it reads. Named with its chapter, so the
	     opening is not mistaken for a line plucked from the middle. An aside, not
	     a filled card (design review #9): the gold quotation rule (STYLE_GUIDE §1)
	     and the serif at a generous size — beside the prose from lg, under it on a
	     phone. Absent where the front matter yields no clean prose: the server
	     owns that judgement (library/opening.py). -->
	{#snippet openingLines()}
		{#if book.opening}
			<figure class="about-quote">
				<blockquote class="font-display leading-snug" dir="auto">
					{book.opening.text}
				</blockquote>
				<figcaption class="mt-3 text-small text-muted" dir="auto">
					{t('book.openingFrom').replace('%chapter%', book.opening.chapter)}
				</figcaption>
			</figure>
		{/if}
	{/snippet}
	<!-- Contents. When the reader has a saved place, Continue's chapter
	     (resumeHere, aria-current) is the one they're in, and every chapter before
	     the furthest one REACHED (furthestHere — opened in sequence or read to its
	     end, never a peek) counts as read. Both are client-only (null at prerender and for a
	     first-time reader), so the baked HTML and a new reader's view are exactly as
	     before — the markers are progressive enhancement that appears after
	     hydration. There is still no per-chapter completion record, so a check means
	     "before the furthest you got", not a claim the chapter was read end to end. -->
	<section id="contents" class="jump-anchor mt-8">
		<h2 class="section-heading no-rule">
			{t('reader.contents')}
			<span class="meta"
				>· <span class="whitespace-nowrap">{chapterCount(book.chapter_count)}</span
				> · <span class="whitespace-nowrap">{readingTime(totalWords)}</span></span
			>
		</h2>
		<!-- A reader with a place: the book as one bar in chapter-length parts,
		     those behind them filled, the one they're in half-tinted — the same
		     place the read card names, in the same words. -->
		{#if finishedAt != null || resuming}
			<div class="mb-2 mt-1">
				<!-- A part per chapter while the parts stay legible; a long book
				     (past SEGMENTS_MAX chapters) is one bar. -->
				{#if book.chapters.length <= SEGMENTS_MAX}
					<SeriesSegments
						stages={book.chapters.map((c) => (isCurrent(c.order) ? 'reading' : isRead(c.order) ? 'done' : 'unread'))}
						weights={book.chapters.map((c) => c.word_count)}
						label={placeLine}
					/>
				{:else}
					<ProgressBar percent={finishedAt != null ? 100 : percentRead} label={placeLine} />
				{/if}
				<p class="mt-1.5 text-small text-muted">{placeLine}</p>
			</div>
		{/if}
		{#if chipGrid}
		<!-- A Bible book's chapters as chips, every one linked (the prerendered page
		     still links each chapter): filled behind the reader, ringed where they
		     are — the list's marks, in the list's colours. The introduction and the
		     conclusion keep their names. Each chip's full name and length are its
		     tooltip and its accessible name carries the name. -->
		<ol class="chapter-grid mt-3">
			{#each book.chapters as ch (ch.order)}
				{@const n = chapterNumber(ch.title)}
				{@const read = isRead(ch.order)}
				{@const current = isCurrent(ch.order)}
				<li class:wide={n == null}>
					<a
						href={readHref(ch.order)}
						class="chapter-chip"
						class:read
						class:current
						aria-current={current ? 'step' : undefined}
						aria-label="{chapterName(ch.order, ch.title)}{read ? `, ${t('settings.heatmapRead')}` : ''}"
						title="{chapterName(ch.order, ch.title)} · {readingMinutes(ch.word_count)} {t('common.min')}"
						dir="auto">{n ?? chapterName(ch.order, ch.title)}</a
					>
				</li>
			{/each}
		</ol>
		<button type="button" class="btn btn-sm btn-ghost mt-3" onclick={() => (contentsAsList = true)}>
			<Icon name="list" size={16} />{t('bible.contentsAsList')}
		</button>
		{:else}
		<!-- The chapters as a path: a line down the markers, a filled mark with a
		     tick for each chapter behind the reader, a ring for the one they're in
		     (its row raised, offering to carry on), a number for the rest. -->
		<div id="contents-list">
		{#each contentsGroups as group (group.chapters[0].order)}
		{#if group.part}
			<!-- A part's heading: "Part Two · 1684" and its subtitle. Plain text
			     from the fixture (`Book.parts`). -->
			<h3 class="contents-part" dir="auto">
				<span class="eyebrow text-gold">{partLine(group.part)}</span>
				{#if group.part.subtitle}<span class="text-small text-muted">{group.part.subtitle}</span>{/if}
			</h3>
		{/if}
		<ol
			class="contents-path"
			class:two-col={twoColumns}
			style:--contents-rows={twoColumns ? contentsRows : undefined}
		>
			{#each group.chapters as ch, i (ch.order)}
				{@const read = isRead(ch.order)}
				{@const current = isCurrent(ch.order)}
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
							⋯ {chapterCount(gap)}
						</button>
					</li>
				{/if}
				<!-- The ends of each column: the path's line stops at their marks. -->
				<li
					class:hidden={visibleOrders != null && !visibleOrders.has(ch.order)}
					class:col-start={i === 0}
					class:col-end={i === group.chapters.length - 1}
					class:split-start={twoColumns && i === contentsRows}
					class:split-end={twoColumns && i === contentsRows - 1}
				>
					<a
						href={readHref(ch.order)}
						class="contents-row"
						class:current
						aria-current={current ? 'step' : undefined}
					>
						<span class="contents-mark" class:read class:current
							>{ch.order}{#if read}<span class="sr-only">{`, ${t('settings.heatmapRead')}`}</span>{/if}</span
						>
						<span class="flex-1 text-body" dir="auto">{chapterName(ch.order, ch.title)}</span>
						{#if current}
							<span class="whitespace-nowrap text-small font-semibold text-accent">{t('book.continue')} <Arrow /></span>
						{:else}
							<span class="text-small text-muted">{readingMinutes(ch.word_count)} {t('common.min')}</span>
						{/if}
					</a>
				</li>
			{/each}
		</ol>
		{/each}
		</div>
		{#if chapterGridFor(book)}
			<button type="button" class="btn btn-sm btn-ghost mt-2" onclick={() => (contentsAsList = false)}>
				{t('bible.contentsAsGrid')}
			</button>
		{/if}
		{/if}
		{#if !chipGrid && book.chapters.length > CONTENTS_COLLAPSE_AT}
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
		<!-- A book of the Bible: on to the next book of the canon, or back to the
		     one before, so the contents' end is not a dead end (Genesis → Revelation). -->
		{#if book.series?.slug === BIBLE_SERIES}
			<BibleBookNav series={book.series} lang={contentLang(book.language)} />
		{/if}
	</section>

	<!-- The road (The Pilgrim's Progress, Part One): each place a stop linked
	     to its chapter, the reader's place on it from this device. Only for a
	     book with a map drawn ($lib/journeyMaps), and only in its language. -->
	{#if journeyMap}
		<section id="journey" class="jump-anchor mt-10" aria-labelledby="journey-heading">
			<h2 id="journey-heading" class="section-heading no-rule">{journeyMap.title}</h2>
			<JourneyMap map={journeyMap} place={journeyPlace} chapterHref={readHref} lang={contentLang(book.language)} />
		</section>
	{/if}

	<!-- Editions (design review #22): the other forms this work takes, once.
	     It used to say so three times — a languages chip in the hero, "Grow with
	     the story" and "Read in your language" — so it is one section now: the
	     young-reader family's cards first, then an "Also in" row of languages.
	     Each half renders only where it exists. Straight after the contents
	     (design review #9: readers decide About → Contents → Editions): a parent
	     who reached the full text needs the young-reader edition surfaced before
	     they start reading, and a child on the retelling needs the way back.

	     The family: the "(For Children)" / "(For Teens)" retellings and the full
	     text they retell, from the API's `editions` (sibling_editions, derived
	     from the slug convention and published-gated server-side). The whole
	     family is offered, this edition ringed, youngest first (the ladder's
	     order, as the hubs draw it); each card is its rung's name and length —
	     the titles differ only by the "(For …)" suffix the rung already says.

	     The languages: books are per-language rows sharing one slug with no
	     English fallback, so every link is a real, published edition;
	     `siblingEditions` is the hreflang alternate set minus this edition, and
	     localeName() gives each its autonym, in its own script. hreflang/lang
	     announce the target language to the reader and to assistive tech, and
	     dir="auto" sets each name's own direction on an Arabic page and off one.
	     data-sveltekit-reload: a full load (the locale is fixed per document —
	     see the root layout's cross-locale guard), and no hover preload, which
	     would run this route's load in the WRONG locale. On a fallback page the
	     notice above already lists them, so the row is not drawn there. -->
	{#if hasEditions}
		<section id="editions" class="jump-anchor mt-12" aria-labelledby="editions-heading">
			<h2 id="editions-heading" class="section-heading no-rule">{t('book.editions')}</h2>
			{#if family.length}
				<ul class="edition-picker">
					{#each family as { book: ed, rung } (ed.slug)}
						{@const here = ed.slug === book.slug}
						{@const words = here ? totalWords : ed.word_count}
						<li>
							<a
								href={localizeHref(`/books/${ed.slug}`)}
								class="edition-card"
								class:here
								aria-current={here ? 'page' : undefined}
							>
								<span class="edition-cover" aria-hidden="true"><BookCover book={ed} /></span>
								<span class="min-w-0">
									<span class="edition-rung">{t(RUNG_LABEL[rung])}</span>
									<span class="block text-small text-muted"
										><span class="whitespace-nowrap">{chapterCount(ed.chapter_count)}</span
										>{#if words}{' '}<span class="whitespace-nowrap">· {readingTime(words)}</span>{/if}</span
									>
								</span>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
			{#if showLanguages}
				<!-- id="languages": the old "Read in your language" section's anchor,
				     kept so shared /books/<slug>/#languages links still land here. -->
				<div id="languages" class="jump-anchor" class:mt-6={family.length}>
					<h3 id="editions-langs" class="section-label">{t('book.alsoIn')}</h3>
					<ul class="flex flex-wrap gap-2" aria-labelledby="editions-langs">
						{#each siblingEditions as ed (ed.loc)}
							<li>
								<a href={ed.href} class="tag" hreflang={ed.loc} lang={ed.loc} dir="auto" data-sveltekit-reload
									>{localeName(ed.loc)}</a
								>
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		</section>
	{/if}

	<!-- People found IN this work who have a bio of their own — an anthology's
	     subjects, the figures a biography follows. Links to their author pages.
	     Language-gated server-side (a person with no bio in this edition's
	     language is dropped), so every card here is a live link. -->
	{#if book.featured_people?.length}
		<section class="mt-12">
			<h2 class="section-heading no-rule">{t('book.peopleInBook')}</h2>
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
				{#each book.featured_people as person (person.slug)}
					<PersonCard {person} />
				{/each}
			</div>
		</section>
	{/if}

	<!-- A book of the Bible: the classics written on it — commentaries,
	     catenas, a book on one of its passages (library/bible_companions) —
	     before the sermons on it: the long reading first, then the preached. -->
	{#if book.read_alongside?.length}
		<section id="read-alongside" class="jump-anchor mt-12" aria-labelledby="read-alongside-heading">
			<h2 id="read-alongside-heading" class="section-heading no-rule">{t('bible.readAlongside')}</h2>
			<p class="-mt-2 mb-5 text-small text-muted">{t('bible.readAlongsideLede')}</p>
			<div class="book-grid">
				{#each book.read_alongside as companion (companion.slug)}
					<BookCard book={companion} showAuthor />
				{/each}
			</div>
		</section>
	{/if}

	<!-- A book of the Bible: the library's sermons on it — those whose text is
	     in this book (library/bible_sermons.py), canon order, the first few —
	     and the rest on the sermons shelf, filtered to this book by its facet. -->
	{#if book.bible_sermons?.sermons.length}
		{@const shelf = book.bible_sermons}
		<section id="sermons" class="jump-anchor mt-12" aria-labelledby="bible-sermons-heading">
			<h2 id="bible-sermons-heading" class="section-heading no-rule">{t('bible.sermonsOnBook')}</h2>
			<div class="sermon-list">
				{#each shelf.sermons as sermon (sermon.slug)}
					<SermonCard {sermon} showAuthor />
				{/each}
			</div>
			{#if shelf.count > shelf.sermons.length}
				<p class="mt-3">
					<a
						href={localizeHref(`/sermons?book=${encodeURIComponent(shelf.book)}`)}
						class="text-small font-semibold text-accent hover:underline"
						>{t('bible.sermonsAll').replace('%count%', String(shelf.count)).replace('%book%', shelf.book)}
						<Arrow /></a
					>
				</p>
			{/if}
		</section>
	{/if}

	<!-- The author, after the book: who wrote it and — where the dates are
	     known — where this book fell in their life, a mark on the line from
	     birth to death. No bio: on this page it read as the book's own prose
	     (bookAboutSection.test.ts); the full life is the author page's, and
	     this band is the way there. -->
	{#if hasAuthorBand}
		<section
			id="author"
			class="jump-anchor mt-12 flex items-center gap-5 rounded-card bg-surface-2 p-5 sm:gap-7 sm:p-7"
			aria-labelledby="author-band-name"
		>
			<a href={authorHref} class="shrink-0 hover:no-underline" tabindex="-1" aria-hidden="true">
				<Portrait
					slug={book.author.slug}
					name={book.author.name}
					url={book.author.photo_url}
					px={128}
					class="h-20 w-20 sm:h-32 sm:w-32"
					initialsClass="text-h2"
				/>
			</a>
			<div class="min-w-0 flex-1">
				<p class="eyebrow text-muted">{t('finished.aboutAuthor')}</p>
				<h2 id="author-band-name" class="text-h2">
					<a href={authorHref} class="text-text hover:underline">{book.author.name}</a>
				</h2>
				{#if lifeline != null}
					<div class="mt-4 max-w-md">
						<div class="lifeline">
							<span class="text-small text-muted">{book.author.birth_year}</span>
							<span class="lifeline-track"
								><span class="lifeline-mark" style:inset-inline-start="{lifeline}%"></span></span
							>
							<span class="text-small text-muted">{book.author.death_year}</span>
						</div>
						<!-- In the mark's accent: the legend for the one coloured dot. -->
						<p class="mt-1 text-center text-small text-accent" dir="auto">
							{book.title} · {book.publication_year}
						</p>
					</div>
				{/if}
				<a href={authorHref} class="mt-3 inline-block text-small font-semibold text-accent hover:underline"
					>{t('book.moreBy').replace('%name%', book.author.name)} <Arrow /></a
				>
			</div>
		</section>
	{/if}

	<!-- Questions and Answers. `qa.items` (editorial if present, else the derived
	     set) also feeds the FAQPage JSON-LD in <Seo> via the same pickQa call, so
	     the visible answers and the structured data stay in lockstep. The shared
	     <QandA> section id is `questions`, which the jump-nav above points at. -->
	<QandA items={qa.items} title={t('qa.sectionTitle')} headingClass="section-heading no-rule" openFirst={false} />

	<!-- Where to go from here: one book to read next (the first of "More like
	     this", given room and its pitch) and, for a book with one, the leader's
	     guide for reading it with a group — then the rest of the shelf. The
	     guide's one link on the page: a printable guide for a group or a
	     homeschool, for the leader, not every reader, so it sits with what
	     comes next rather than in the hero's actions. -->
	{#snippet guideCard()}
		<a
			href={localizeHref(`/books/${book.slug}/guide`)}
			class="card-tint flex items-start gap-4 rounded-card border border-border bg-surface p-4 text-text"
		>
			<span class="next-icon" aria-hidden="true"><Icon name="users" size={22} /></span>
			<span class="min-w-0">
				<span class="eyebrow block text-accent">{t('guide.label')}</span>
				<span class="mt-1 block text-small" dir="auto">{t('guide.description').replace('%t%', book.title)}</span>
				<span class="mt-2 block text-small font-semibold text-accent">{t('guide.open')} <Arrow /></span>
			</span>
		</a>
	{/snippet}
	{#if book.related?.length}
		{@const [next, ...rest] = book.related}
		<section id="related" class="jump-anchor mt-12">
			<h2 class="section-heading no-rule">{t('book.related')}</h2>
			<div class="next-pair">
				<a
					href={localizeHref(`/books/${next.slug}`)}
					class="card-tint flex items-start gap-4 rounded-card border border-border bg-surface p-4 text-text"
				>
					<span class="w-20 shrink-0" aria-hidden="true"><BookCover book={next} /></span>
					<span class="min-w-0">
						<span class="eyebrow block text-accent">{t('articles.readNext')}</span>
						<span class="mt-1 block font-display text-h3 leading-snug" dir="auto">{next.title}</span>
						<span class="block text-small text-muted">{next.author.name}</span>
						{#if next.hook}
							<span class="mt-2 line-clamp-3 block text-small" dir="auto">{next.hook}</span>
						{:else}
							<span class="mt-2 block text-small text-muted"
								>{chapterCount(next.chapter_count)}{#if next.word_count}{` · ${readingTime(next.word_count)}`}{/if}</span
							>
						{/if}
					</span>
				</a>
				{#if book.has_leader_guide}{@render guideCard()}{/if}
			</div>
			{#if rest.length}
				<div class="book-grid mt-6">
					{#each rest as rel (rel.slug)}
						<BookCard book={rel} showAuthor />
					{/each}
				</div>
			{/if}
		</section>
	{:else if book.has_leader_guide}
		<!-- No shelf to sit beside: the guide alone, still offered. -->
		<div class="next-pair mt-12">{@render guideCard()}</div>
	{/if}

	<!-- A book with files to take offline: the leaders who carry books where
	     there is no signal. Down here with the page's other onward links, not in
	     the read card, where it sat at the moment of deciding to read. -->
	{#if book.pdf_url || book.epub_url}
		<ForPromo place="book-download" class="mt-8" />
	{/if}

	<!-- Where this edition came from — its source note and link, translation,
	     cover credit, last update and rights — in one panel at the foot, where
	     the source line and cover credit used to sit (AboutThisText). -->
	<AboutThisText {book} />

	<!-- A translated edition did not appear in the original's year, so it is
	     cited without one rather than as a reprint of it. -->
	<CitePanel
		lang={book.language}
		work={{
			kind: 'book',
			author: book.author.name,
			corporate: isImprint(book.author),
			title: book.title,
			year: isTranslated(book.source_type) ? null : book.publication_year,
			url: canonical
		}}
	/>
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
	onread={readAgain}
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
	/* Only the art clips (the scaled, blurred image), and the band makes no
	   stacking context: either would trap the action strip's menus under the
	   sticky sub-nav or cut them off. The column, positioned after the art,
	   paints over it by document order alone. */
	.book-band {
		position: relative;
	}
	.book-band > .page-col {
		position: relative;
	}
	.book-band-art {
		position: absolute;
		inset: 0;
		overflow: hidden;
		-webkit-mask-image: linear-gradient(to bottom, black 45%, transparent);
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
	/* Mixed on the band, applied on its children: --muted defined from itself
	   on one element would be a cycle (invalid), but a child's --muted may read
	   the parent's. */
	.washed {
		--muted-on-wash: color-mix(in srgb, var(--muted) var(--muted-mix-on-wash), var(--text));
	}
	.washed > * {
		--muted: var(--muted-on-wash);
	}

	/* Two columns (design review #6): the cover on the start side, and on the
	   end side the title block, its one facts line, then the read card and the
	   action strip. A phone: the cover beside the title block and the actions
	   full width straight beneath it, so the read button is in the first
	   screen. The wide step is decided by the room the column has (a
	   container), not the viewport: the reader's page-width setting can
	   narrow it. Row gap 0: the read card carries its own mt-4. */
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
	.book-hero-actions {
		grid-column: 1 / -1;
	}
	@media (min-width: 640px) {
		/* A last row takes up the cover's spare height, so the title and the
		   actions stack tight at the top beside it. */
		.book-hero {
			grid-template-rows: auto 1fr;
			column-gap: 1.5rem;
		}
		.book-hero-cover {
			grid-row: 1 / -1;
			width: 11rem;
		}
		.book-hero-actions {
			grid-column: 2;
		}
		/* The read card held to a measure, so the button is not a bar across a
		   wide column. The card only, not the action host: the strip keeps the
		   whole column, so it is still a plain row once that passes 560px. */
		.book-hero-actions .read-card {
			max-width: 32rem;
		}
	}
	/* Wide: a larger cover. */
	@container book-hero (min-width: 56rem) {
		.book-hero {
			column-gap: 2.5rem;
		}
		.book-hero-cover {
			width: 13rem;
		}
	}
	/* At a glance (top-50 #3): a third column only where the hero has room for
	   it — 72rem of container leaves the middle column ~36rem, so the action
	   strip stays a plain row (its 560px step). Narrower, the panel is hidden
	   and its "Also in" link stays in the facts line; wider, the link moves
	   into the panel. */
	.book-glance {
		display: none;
	}
	@container book-hero (min-width: 72rem) {
		.book-hero:has(.book-glance) {
			grid-template-columns: auto minmax(0, 1fr) 18rem;
		}
		.book-glance {
			display: block;
			grid-column: 3;
			grid-row: 1 / -1;
			padding: 1.25rem;
			border: 1px solid var(--border);
			border-radius: var(--radius-card);
			background: color-mix(in srgb, var(--surface) 85%, transparent);
		}
		.facts-also-in.in-glance {
			display: none;
		}
	}
	.book-glance dl > div + div {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--border);
	}
	.book-glance dt {
		font-weight: 600;
		color: var(--text);
	}
	.book-glance dd {
		margin-top: 0.375rem;
	}
	.glance-line {
		font-size: var(--fs-body);
		line-height: 1.45;
		color: var(--text);
	}
	.glance-bars {
		display: flex;
		align-items: flex-end;
		gap: 2px;
		height: 3rem;
	}
	.glance-bars span {
		flex: 1 1 0;
		min-width: 1px;
		border-radius: 2px 2px 0 0;
		background: color-mix(in srgb, var(--accent) 55%, var(--surface));
	}

	/* The edition toggle: full width under the read button, two even halves. */
	.edition-seg button {
		flex: 1 1 0;
	}

	/* About: the prose at a reading measure, and from lg the opening lines as
	   an aside beside it (design review #9). On a phone they follow in flow. */
	.about-prose {
		max-width: 65ch;
	}
	.about-quote {
		margin: 2rem 0 0;
		padding-inline-start: 1.25rem;
		/* The one quotation rule (STYLE_GUIDE §1), not a filled card. */
		border-inline-start: 3px solid var(--gold);
	}
	/* Alone (a book with no prose to follow), the wrapper's mt-8 is the gap. */
	.about-quote:first-child {
		margin-top: 0;
	}
	.about-quote blockquote {
		font-size: var(--fs-h3);
	}
	@media (min-width: 1024px) {
		.about-layout {
			display: grid;
			grid-template-columns: minmax(0, 65ch) minmax(0, 20rem);
			column-gap: 3.5rem;
			align-items: start;
		}
		.about-quote {
			margin-top: 0.25rem;
		}
		.about-quote blockquote {
			font-size: var(--quote-size);
		}
	}
	/* Topics and Scripture: plain links in a muted line. The hero's "Also in 5
	   languages" the same: a quiet link to Editions, ink not accent, so it
	   doesn't compete with the read button. */
	.about-meta a,
	.also-in-link {
		color: var(--text);
		text-decoration: underline;
		text-decoration-color: var(--border-strong);
		text-underline-offset: 0.2em;
	}
	.about-meta a:hover,
	.also-in-link:hover {
		color: var(--accent);
		text-decoration-color: currentColor;
	}

	/* The author's lifeline: birth and death at its ends, this book a dot. */
	.lifeline {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.lifeline-track {
		position: relative;
		flex: 1;
		height: 2px;
		background: var(--border-strong);
	}
	.lifeline-mark {
		position: absolute;
		top: 50%;
		width: 0.85rem;
		height: 0.85rem;
		margin-inline-start: -0.425rem;
		border: 2px solid var(--surface-2);
		border-radius: 50%;
		background: var(--accent);
		transform: translateY(-50%);
	}

	/* Read next, and the group guide beside it. */
	.next-pair {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 28rem), 1fr));
		gap: 1rem;
	}
	.next-icon {
		display: inline-flex;
		flex-shrink: 0;
		align-items: center;
		justify-content: center;
		width: 3rem;
		height: 3rem;
		border-radius: var(--radius-card);
		background: var(--accent-soft);
		color: var(--accent);
	}

	/* The edition picker: a card per rung, the one in hand ringed in the
	   accent (the .seg selected-edge rule: an edge, never the fill alone). */
	.edition-picker {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr));
		gap: 0.75rem;
		margin: 0.75rem 0 0;
		padding: 0;
		list-style: none;
	}
	.edition-card {
		display: flex;
		align-items: center;
		gap: 0.9rem;
		height: 100%;
		padding: 0.75rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		color: var(--text);
		text-decoration: none;
	}
	.edition-card:hover {
		border-color: var(--accent-soft-border);
		text-decoration: none;
	}
	.edition-card.here {
		border-color: var(--accent);
		box-shadow: inset 0 0 0 1px var(--accent);
	}
	.edition-cover {
		flex-shrink: 0;
		width: 3.5rem;
	}
	.edition-rung {
		display: block;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		line-height: 1.25;
	}
	.here .edition-rung {
		color: var(--accent);
	}

	/* The path: a hairline down the markers' centre, behind them — drawn per
	   row, so it stops at each column's first and last mark. A grid, so a row's
	   own margins (the current one's) stay inside it and the line runs on. */
	.contents-path {
		display: grid;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	/* A flex row, so the link fills the <li> even when the grid row is taller
	   (the neighbouring column's title wraps): the line's 50% caps then meet
	   the marker's centre. */
	.contents-path > li {
		position: relative;
		display: flex;
	}
	/* The collapsed rows. Tailwind's `hidden` lives in @layer utilities, which
	   the unlayered `display: flex` just above out-ranks — so a "collapsed"
	   list used to show EVERY chapter and the "⋯ 16 chapters" marker as well
	   (chapters 1–21, the marker, then 22). Hidden here, at this rule's rank. */
	.contents-path > li.hidden {
		display: none;
	}
	/* A part's heading over its run of chapters, set in the title column. */
	.contents-part {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.25rem 0.6rem;
		margin: 1.25rem 0 0.35rem;
		padding-inline-start: 0.75rem;
		font-size: inherit;
		font-weight: inherit;
	}
	.contents-part:first-child {
		margin-top: 0.5rem;
	}
	.contents-path > li > * {
		flex: 1 1 auto;
		min-width: 0;
	}
	.contents-path > li::before {
		content: '';
		position: absolute;
		inset-block: 0;
		inset-inline-start: calc(0.75rem + 0.75rem - 1px);
		width: 2px;
		background: var(--border);
	}
	.contents-path > li.col-start::before {
		top: 50%;
	}
	.contents-path > li.col-end::before {
		bottom: 50%;
	}
	/* A short book, whole, in two columns from md: down the first, then the
	   second. */
	@media (min-width: 768px) {
		.contents-path.two-col {
			grid-template-rows: repeat(var(--contents-rows), auto);
			grid-auto-flow: column;
			grid-auto-columns: minmax(0, 1fr);
			column-gap: 2rem;
		}
		.contents-path.two-col > li.split-start::before {
			top: 50%;
		}
		.contents-path.two-col > li.split-end::before {
			bottom: 50%;
		}
	}
	.contents-row {
		position: relative;
		display: flex;
		align-items: center;
		gap: 0.85rem;
		padding: 0.5rem 0.75rem;
		border-radius: var(--radius-card);
		color: var(--text);
		text-decoration: none;
	}
	.contents-row:hover {
		background: var(--surface-2);
		text-decoration: none;
	}
	.contents-row.current {
		margin-block: 0.25rem;
		padding-block: 0.75rem;
		background: var(--accent-soft);
		box-shadow: inset 0 0 0 1px var(--accent-soft-border);
	}
	.contents-mark {
		display: inline-flex;
		flex-shrink: 0;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		border: 1.5px solid var(--border-strong);
		border-radius: 50%;
		background: var(--bg);
		font-size: var(--fs-micro);
		font-variant-numeric: tabular-nums;
		color: var(--muted);
	}
	.contents-mark.read {
		border-color: var(--accent);
		background: var(--accent);
		color: var(--accent-contrast);
	}
	.contents-mark.current {
		border: 2px solid var(--accent);
		background: var(--surface);
		font-weight: 600;
		color: var(--accent);
	}

	/* The "⋯ N chapters" row standing in for a collapsed run: quiet, indented to
	   the title column, and a way to open the full list. */
	.contents-gap {
		display: block;
		width: 100%;
		padding-block: 0.35rem;
		padding-inline: 3.1rem 0;
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
