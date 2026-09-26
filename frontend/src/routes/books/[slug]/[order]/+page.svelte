<script lang="ts">
	import { onMount, onDestroy, tick, untrack } from 'svelte';
	import { authorLdType, authorPath } from '$lib/originals';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { goto, invalidateAll } from '$app/navigation';
	import { getBook, getPlan, type BookDetail, type Chapter, type PlanDetail } from '$lib/library-public';
	import { planProgress } from '$lib/planProgress.svelte';
	import { reflectPrompt } from '$lib/journal';
	import {
		saveProgress,
		getScrollAnchor,
		saveScrollAnchor,
		getProgressRecord,
		offerFinish
	} from '$lib/progress';
	import { readerPrefs, MARGIN } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { nextBarHidden } from '$lib/readerAutohide';
	import FocusExit from '$lib/components/FocusExit.svelte';
	import { marks } from '$lib/marks.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import { bookmarks } from '$lib/bookmarks.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { rememberResumeBook } from '$lib/resumeBooks';
	import {
		chapterName,
		contentLang,
		editionLang,
		readingTime,
		readingMinutes,
		listenTime,
		bookTimeLeft,
		minutesLeft as minutesLeftOf,
		HEADER_OFFSET,
		placeAfterLayout
	} from '$lib/reading';
	import { pageOfOffset } from '$lib/pageMath';
	import { tapTurn, swipeTurn, dampDrag } from '$lib/pageGestures';
	import { fetchSyncedProgress } from '$lib/progress';
	import { auth } from '$lib/auth.svelte';
	import { syncedAhead, type Position } from '$lib/resumeSync';
	import { paceDelta, paragraphWordCounts, type PaceSample } from '$lib/pace';
	import { readingPace } from '$lib/readingPace.svelte';
	import { readingTimer } from '$lib/readingTime.svelte';
	import { listen } from '$lib/listen.svelte';
	import { define } from '$lib/define.svelte';
	import { scripture } from '$lib/scripture.svelte';
	import { createReaderText } from '$lib/readerText.svelte';
	import { elementVisible } from '$lib/scrollSpy.svelte';
	import ReaderOverlays from '$lib/components/ReaderOverlays.svelte';
	import { API_BASE_URL, SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, truncateMeta } from '$lib/seo';
	import { localizeHref } from '$lib/href';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import { dismissable } from '$lib/actions/dismissable';
	import Seo from '$lib/components/Seo.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import TocDrawer from '$lib/components/TocDrawer.svelte';
	import SearchDrawer from '$lib/components/SearchDrawer.svelte';
	import NotesDrawer from '$lib/components/NotesDrawer.svelte';
	import LanguageFallbackNotice from '$lib/components/LanguageFallbackNotice.svelte';
	import { editionSeo, languageFallback } from '$lib/languageFallback';

	let { data } = $props();
	const chapter = $derived(data.chapter as Chapter);
	const slug = $derived(data.slug as string);
	const language = $derived(data.language as string);
	// 'modern' when reading the Modern English edition, else null. Carried in the
	// URL and preserved across every in-reader chapter link.
	const edition = $derived((data.edition as 'modern' | null) ?? null);
	const t = i18n.t;

	// --- SEO head (this page prerenders — see +page.ts) -------------------------
	// Self-referential canonical + hreflang, same convention as books/[slug]:
	// only the locales this book actually exists in (chapter counts match across
	// a book's translations, so the same order URL resolves in each).
	const seoPath = $derived(`/books/${slug}/${chapter.order}/`);
	// A missing edition renders the English one (see languageFallback) — except
	// under ?edition=modern, where English is what the reader asked for.
	const fallback = $derived(edition ? null : languageFallback(getLang(), language));
	const seo = $derived(editionSeo(seoPath, chapter.available_languages, fallback));
	const hreflang = $derived(seo.hreflang);
	const canonical = $derived(seo.canonical);

	// One trail feeds both the visible <Breadcrumb> and the JSON-LD (the reader
	// had a hand-rolled nav Books › Author › Book and no BreadcrumbList at all).
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.books'), href: '/books' },
		{ name: chapter.book_title, href: `/books/${slug}` },
		{ name: chapterName(chapter.order, chapter.title), href: `/books/${slug}/${chapter.order}` }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
	const metaDescription = $derived(
		chapter.body_html
			.replace(/<[^>]+>/g, ' ')
			// Decode the entities the sanitized body uses, else they double-escape
			// into the meta text ("&quot;Then he said..." in search snippets).
			.replace(/&quot;/g, '"')
			.replace(/&#x27;|&#39;/g, "'")
			.replace(/&lt;/g, '<')
			.replace(/&gt;/g, '>')
			.replace(/&nbsp;/g, ' ')
			.replace(/&amp;/g, '&')
	);
	// Trimmed to a SERP-sized slice at a sentence/word boundary — the raw 250
	// char cut fed search snippets a mid-word truncation.
	const metaText = $derived(truncateMeta(metaDescription));
	// The <title> names the chapter, then the book AND its author — people search
	// "<author> <book> chapter 1", and the author was missing. Localized via
	// chapter_title_tag (mirrors book_title_tag), so each locale's "by" is right.
	const titleTag = $derived(
		t('chapter.titleTag')
			.replace('%chapter%', chapterName(chapter.order, chapter.title))
			.replace('%title%', chapter.book_title)
			.replace('%name%', chapter.author_name)
	);
	const chapterLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Chapter',
			name: chapterName(chapter.order, chapter.title),
			position: chapter.order,
			isPartOf: {
				'@type': 'Book',
				name: chapter.book_title,
				author: { '@type': 'Person', name: chapter.author_name },
				url: `${SITE_URL}${localizeHref(`/books/${slug}/`)}`
			},
			url: canonical,
			isAccessibleForFree: true,
			inLanguage: contentLang(language),
			// The chapter's own measure and its author as an entity (not just a name
			// buried in isPartOf), plus the publisher — so the chapter node stands on
			// its own in the graph rather than being an unsized fragment of the book.
			wordCount: chapter.word_count || undefined,
			author: {
				'@type': authorLdType(chapter.author_slug),
				name: chapter.author_name,
				url: `${SITE_URL}${localizeHref(authorPath(chapter.author_slug))}`
			},
			publisher: { '@type': 'Organization', name: 'Ochorus' }
		})
	);

	let body: HTMLDivElement | undefined = $state();
	let titleEl: HTMLHeadingElement | undefined = $state();
	// Is the chapter title still on screen? Once it scrolls under the header the
	// top bar swaps the "← Book" link for a "you are here" label. Shared single-
	// element observer; the header-height inset matches the old inline IO. Starts
	// true — the title is at the top of the page on load.
	const titleSpy = elementVisible(() => titleEl, {
		rootMargin: `-${HEADER_OFFSET}px 0px 0px 0px`,
		initial: true
	});

	// The chapter order read-aloud rolled over INTO, so the per-chapter effect
	// picks playback up from its top on arrival (audiobook roll-over). Scoped to
	// the specific target order — not a bare flag — so that if the reader
	// manually navigates somewhere else mid-roll-over, the arriving chapter won't
	// match and won't surprise-play. A plain var, not $state: the page component
	// is reused across chapter navigations, so it survives the goto.
	let autoContinueOrder: number | null = null;

	// The prerendered HTML is always the standard edition (query params don't
	// exist at build time — see +page.ts). A direct visit to ?edition=modern
	// hydrates with that standard-edition data, so re-run load client-side once
	// to fetch the Modern English chapter.
	onMount(() => {
		const wantsModern = new URLSearchParams(location.search).get('edition') === 'modern';
		if (wantsModern && edition !== 'modern') invalidateAll();
	});

	let tocOpen = $state(false);
	let searchOpen = $state(false);
	let notesOpen = $state(false);

	// The next chapter's opening line, for the "up next" card at the chapter's
	// end. Captured from the idle prefetch below (which already fetches that
	// chapter to warm the cache), so it costs no extra request.
	let nextPreview = $state('');

	/** The first paragraph's text, cheaply: one regex over the head of the HTML,
	 *  no DOM parse of a whole chapter for a single line. Entities that the
	 *  sanitizer leaves in prose are unescaped; anything else is rare enough. */
	function openingLine(html: string): string {
		const m = /<p\b[^>]*>([\s\S]*?)<\/p>/i.exec(html.slice(0, 8000));
		return (m?.[1] ?? '')
			.replace(/<[^>]+>/g, '')
			.replace(/&amp;/g, '&')
			.replace(/&quot;/g, '"')
			.replace(/&#39;/g, "'")
			.replace(/&nbsp;/g, ' ')
			.replace(/\s+/g, ' ')
			.trim()
			.slice(0, 120);
	}

	// "Back to where you were": the resume point a ?p= deep-link (a bookmark,
	// search hit or note) jumped AWAY from. Captured before the jump overwrites
	// the book's resume record, offered as a pill for a short while, then let go.
	let returnTo = $state<{ order: number; p: number } | null>(null);
	let returnTimer: ReturnType<typeof setTimeout> | undefined;
	// The one arrival that must NOT offer a way back: a jump this page made
	// itself (the pill, or the synced-position offer). That arrival carries a
	// ?p= too, and would otherwise read the spot just left as "prior" and offer
	// the reverse jump — a pill that never goes away. Keyed by target rather
	// than a boolean because the chapter effect can run more than once while a
	// navigation settles; only the run that actually lands there consumes it.
	let ownJumpTarget = '';
	function jumpTo(to: { order: number; p: number }) {
		ownJumpTarget = `${to.order}:${to.p}`;
		const href = chapterHref(to.order);
		goto(`${href}${href.includes('?') ? '&' : '?'}p=${to.p}`);
	}
	function offerReturn(to: { order: number; p: number }) {
		returnTo = to;
		clearTimeout(returnTimer);
		returnTimer = setTimeout(() => (returnTo = null), 12000);
	}
	function goBackToPrior() {
		const to = returnTo;
		returnTo = null;
		if (to) jumpTo(to);
	}

	// "Continue where you left off on your other device": the account's synced
	// position when it is newer than, and meaningfully ahead of, where this
	// device is opening (see $lib/resumeSync). One ask per book per page-life:
	// taken, dismissed, or left alone for a while, it is not asked again — a
	// fresh pill on every chapter turn would be a nag, and once taken the
	// reader is where the other device was.
	let syncOffer = $state<Position | null>(null);
	let syncTimer: ReturnType<typeof setTimeout> | undefined;
	const syncDismissed = new Set<string>();
	// What the chapter effect asks for, answered by the effect below once the
	// session has settled: on a cold load (a deep link, the PWA icon) the
	// session resolves AFTER the first chapter opens, and an ask made before
	// that is answered "signed out". `local` is this device's record as read
	// before the open touched it.
	let syncAsk = $state<{
		slug: string;
		order: number;
		language: string;
		local: ReturnType<typeof getProgressRecord>;
	} | null>(null);
	$effect(() => {
		const ask = syncAsk;
		if (!ask || !auth.initialized) return;
		let cancelled = false;
		fetchSyncedProgress(ask.slug).then((remote) => {
			if (cancelled) return;
			const offer = syncedAhead(
				ask.local && { order: ask.local.order, p: ask.local.paragraph_index, at: ask.local.at },
				remote && { order: remote.order, p: remote.paragraph_index, at: remote.at },
				ask.order
			);
			if (!offer) return;
			// One row serves every edition and outlives a re-import: never offer a
			// chapter this book (as loaded) does not have, and trust the paragraph
			// only when it was measured in the edition being read here.
			const chapters = bookForProgress?.chapters;
			if (chapters && !chapters.some((c) => c.order === offer.order)) return;
			syncOffer = { ...offer, p: remote?.language === ask.language ? offer.p : 0 };
			clearTimeout(syncTimer);
			syncTimer = setTimeout(dismissSyncOffer, 15000);
		});
		return () => {
			cancelled = true;
		};
	});
	function takeSyncOffer() {
		const to = syncOffer;
		dismissSyncOffer();
		if (to) jumpTo(to);
	}
	function dismissSyncOffer() {
		clearTimeout(syncTimer);
		syncOffer = null;
		syncDismissed.add(slug);
	}

	// --- Reading-progress indicators -------------------------------------------
	// Fraction of the current chapter scrolled past (0..1), updated by the same
	// throttled scroll handler that saves the position anchor.
	let chapterFrac = $state(0);
	let bookForProgress = $state<BookDetail | null>(null);
	/** On the last chapter, the series' next volume in this language, if any.
	 *  Rides the book fetch above, so it appears once that lands (the button
	 *  falls back to "Back to contents" until then, and for good offline). */
	const nextInSeries = $derived(chapter.next ? null : (bookForProgress?.series?.next ?? null));

	// Reset the scroll fraction when the CHAPTER changes — a fresh chapter opens
	// at the top until the per-chapter effect below restores the saved position.
	// This is deliberately separate from the book fetch: the old combined effect
	// also read `bookForProgress`, so that fetch's async write re-ran the effect
	// and snapped `chapterFrac` back to 0 *after* the position had been restored,
	// jumping the progress footer/scrubber to page 1.
	// --- Finishing a chapter ---------------------------------------------------
	// Reaching the end of a chapter is a small milestone; mark it once, with a
	// brief haptic and a gentle pulse of the "Next chapter" button, so finishing
	// feels like an arrival rather than passing silently. Respects
	// prefers-reduced-motion (no motion, no buzz). Gated once per chapter, and
	// only after a settling window (below) so it fires on READING to the end, not
	// on the restore-scroll that reopening lands at the saved position.
	let chapterCelebrated = false;
	let chapterOpenedAt = 0;
	let celebrate = $state(false);
	const reduceMotion = browser ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;

	$effect(() => {
		void slug;
		void chapter.order;
		chapterFrac = 0;
		chapterCelebrated = false;
		celebrate = false;
		chapterOpenedAt = performance.now();
	});

	function markChapterComplete() {
		if (chapterCelebrated) return;
		// The restore-scroll settles to the saved position — possibly the chapter's
		// end — shortly after open, and (via scrollIntoView/scrollBy) it emits the
		// scroll events onScroll listens to. This window ignores that settle, so
		// reopening a chapter you'd read to the bottom of doesn't re-congratulate
		// you; genuine reading reaches the end well after it.
		if (performance.now() - chapterOpenedAt < 1500) return;
		chapterCelebrated = true;
		// Reaching the end of the LAST chapter finishes the book — it drops out of
		// "Continue reading" and onto the finished shelf, with a quiet Undo (auto-
		// detection can misfire on a reader who skimmed to the end). `!chapter.next`
		// is the last-chapter signal used throughout this route.
		if (!chapter.next) offerFinish(slug, 'book');
		if (reduceMotion?.matches) return;
		navigator.vibrate?.(12);
		celebrate = true;
	}

	// Fetch the book once per (slug, language) for the book-level progress
	// figures. It must NOT read `bookForProgress` — setting it would otherwise
	// re-trigger this effect. Only slug/language are tracked, so chapter turns
	// (same book) don't refetch and don't disturb the restored position.
	$effect(() => {
		const s2 = slug;
		const lang = getLang();
		bookForProgress = null;
		let cancelled = false;
		getBook(s2, lang)
			.then((b) => {
				if (cancelled) return;
				bookForProgress = b;
				// So the next visit to home can draw this book in "Continue
				// reading" at once — a reader who arrived here from search may
				// never have opened home this visit (see `$lib/resumeBooks`).
				rememberResumeBook(lang, b);
			})
			.catch(() => {});
		return () => {
			cancelled = true;
		};
	});

	// Paragraph at the top of the viewport — tracked on the throttled scroll pass
	// so the bookmark toggle can reflect whether the current spot is bookmarked.
	let topIndex = $state(0);
	const currentBookmarked = $derived(bookmarks.has(chapter.order, topIndex));

	function updateFraction() {
		if (!body) return;
		const rect = body.getBoundingClientRect();
		const total = rect.height;
		if (total <= 0) return;
		const seen = Math.min(Math.max(window.innerHeight - rect.top, 0), total);
		chapterFrac = Math.min(1, Math.max(0, seen / total));
		topIndex = topVisibleIndex();
	}

	/** Bookmark (or un-bookmark) the paragraph at the top of the viewport. */
	function toggleBookmark() {
		if (!body) return;
		const p = currentIndex();
		const el = body.children[p] as HTMLElement | undefined;
		const snippet = (el?.innerText ?? '').trim().replace(/\s+/g, ' ').slice(0, 90);
		bookmarks.toggle(chapter.order, p, snippet, chapter.title);
		topIndex = p;
	}

	const minsLeft = $derived(minutesLeftOf(chapter.word_count, chapterFrac));
	const editionLabel = $derived(
		edition === 'modern' ? t('reader.readOriginal') : t('reader.readModern')
	);
	// The phone bar's second line. A single-work volume names its only chapter
	// after the book ("Absolute Surrender" / "Absolute Surrender"), so say which
	// chapter instead of repeating the title.
	const phoneChapterLine = $derived.by(() => {
		const chap = chapterName(chapter.order, chapter.title);
		return chap === chapter.book_title ? `${t('settings.chapterN')} ${chapter.order}` : chap;
	});
	// One clamped read-fraction for the whole-book figures below, so "% through"
	// and "time left in book" always agree on how far into the open chapter the
	// reader is (chapterFrac is already [0,1] at every writer, but sharing the
	// clamp keeps the two from ever diverging if that changes).
	const readFrac = $derived(Math.min(1, Math.max(0, chapterFrac)));
	// The book's word counts split around the open chapter — the words before it,
	// the words after it, and the total. Computed once per (book, chapter), NOT on
	// the scroll path, then shared by both the "% through" figure and the "time
	// left in book" estimate so the two readings can never drift apart.
	const bookWords = $derived.by(() => {
		const b = bookForProgress;
		if (!b || b.slug !== slug || !b.chapters.length) return null;
		let before = 0;
		let later = 0;
		let total = 0;
		for (const c of b.chapters) {
			total += c.word_count;
			if (c.order < chapter.order) before += c.word_count;
			else if (c.order > chapter.order) later += c.word_count;
		}
		return { before, later, total };
	});
	const bookPercent = $derived.by(() => {
		const w = bookWords;
		if (!w || !w.total) return null;
		return Math.min(100, Math.round(((w.before + chapter.word_count * readFrac) / w.total) * 100));
	});
	// Whole minutes of reading left in the book: the tail of the open chapter plus
	// every chapter after it, at the reader's pace. Kept as an integer so the
	// localized label below reformats only when the minute count changes — not on
	// every throttled scroll tick.
	const bookMinsLeft = $derived.by(() => {
		const w = bookWords;
		if (!w) return null;
		const remainingHere = chapter.word_count * (1 - readFrac);
		return readingMinutes(remainingHere + w.later);
	});
	// "3 hr 12 min left in book" — the whole-book companion to the chapter's "N
	// min left" (Kindle shows both).
	const bookTimeLeftLabel = $derived(bookMinsLeft === null ? null : bookTimeLeft(bookMinsLeft));

	// --- Page-turn mode --------------------------------------------------------
	// An opt-in e-reader layout (readerPrefs.paged): the chapter body is laid out
	// in full-width CSS columns inside a fixed viewport and turned one page at a
	// time with a translateX, instead of scrolling. Only active while not
	// listening — Listen mode keeps the scrolling layout it was built against.
	let articleEl = $state<HTMLElement>();
	let pager = $state<HTMLElement>();
	let chromeEl = $state<HTMLElement>();
	let footEl = $state<HTMLElement>();
	let leadEl = $state<HTMLElement>();
	let chapterEndEl = $state<HTMLElement>();
	// The footer's UNFOLDED height, published as --foot-h for the article's
	// bottom clearance and the return pill (hand-kept per-breakpoint constants
	// had drifted three times). It varies with the touch scrubber and the phone
	// action row — but deliberately NOT with that row folding: folding changes
	// no layout, because shrinking the article's padding at the end of a
	// chapter clamped scrollY upward, which read as a scroll-up and unfolded it
	// again — a flicker loop. measureScrollPages reads the same number so the
	// page total doesn't shift with the fold. Removed while no footer is shown.
	let footH = 0;
	$effect(() => {
		const el = footEl;
		if (!el) return;
		const root = document.documentElement;
		const ro = new ResizeObserver(() => {
			if (el.querySelector('.foot-actions.folded')) return;
			footH = el.offsetHeight;
			root.style.setProperty('--foot-h', `${footH}px`);
		});
		ro.observe(el);
		return () => {
			ro.disconnect();
			footH = 0;
			root.style.removeProperty('--foot-h');
		};
	});

	// --- Phone chrome (below `sm`) ---------------------------------------------
	// The bar layouts switch in CSS (`sm:hidden` / `hidden sm:flex`), so the
	// prerendered page paints right. This only picks WHICH text-settings panel
	// to mount: popover and sheet share `readerUi.panelOpen`, and a hidden
	// popover's click-away handler would shut the sheet on every tap inside it.
	// A $state flipped in an effect, NOT svelte/reactivity's MediaQuery: that
	// reads matchMedia during hydration, so on a phone both `{#if}`s below
	// would disagree with the prerendered (desktop) markup.
	let isPhone = $state(false);
	$effect(() => {
		const mq = window.matchMedia('(max-width: 639.98px)');
		const sync = () => (isPhone = mq.matches);
		sync();
		mq.addEventListener('change', sync);
		return () => mq.removeEventListener('change', sync);
	});
	// The phone bar's "⋯" group (bookmark, search, notebook, edition, focus).
	let moreOpen = $state(false);
	/** Close the "⋯" group, then run the chosen action. */
	const fromMore = (action: () => void) => () => {
		moreOpen = false;
		action();
	};
	let pageIndex = $state(0);
	let pageTotal = $state(1);
	let pageW = $state(0);
	const paged = $derived(readerPrefs.paged && listen.status === 'idle');

	// Kindle-style two-column spread: when the viewport is wide enough for two
	// comfortable columns, page mode lays the text out as an open book (two
	// columns per page) rather than one narrow centred column that wastes the
	// sides. Below the threshold it stays single-column. Tracked reactively so a
	// resize (or entering/leaving page mode) re-lays out immediately.
	const TWO_COL_MIN = 1024;
	let viewportW = $state(browser ? window.innerWidth : 0);
	const cols = $derived(paged && viewportW >= TWO_COL_MIN ? 2 : 1);
	// Single column keeps the reader's chosen measure; a two-column spread sizes
	// to two of that measure plus a centre gutter (capped to the viewport), so
	// each column stays near the comfort width the reader picked.
	const articleMax = $derived(
		cols === 2
			? 'min(calc(2 * var(--reading-measure) + 4rem), calc(100vw - 2rem))'
			: 'var(--reading-measure)'
	);

	/**
	 * The chrome bar tracks the text it belongs to.
	 *
	 * It was a flat `max-w-3xl` (48rem) while the article ranges from 27rem to
	 * 83rem — measure (34/42/52rem) times scale (0.8–1.6) — and 88rem as a
	 * two-column spread. So the bar was up to 333px WIDER than the text at the
	 * small end and 640px NARROWER at the large end, matching it at no setting a
	 * reader can actually pick. Sharing `articleMax` puts its edges on the text's
	 * edges, and `chromeGutter` puts its padding on the text's gutter: in page
	 * mode that is the pager's own `--pgpad`, in scroll mode the reader's
	 * Margins pref (the article's `--reading-margin`) — so the controls line up
	 * with the column at every setting, not merely with the box.
	 *
	 * The floor is for the bar's sake — seven controls plus a title in 435px
	 * (narrow at 0.8x) is a crush, and unlike the prose the bar doesn't get to
	 * reflow. The min() then keeps that floor inside a phone, where 32rem is
	 * wider than the viewport.
	 */
	const chromeMax = $derived(`min(max(${articleMax}, 32rem), 100%)`);
	// The bar's side padding tracks the text's gutter (see the comment above).
	// Page mode zeroes the article padding and uses --pgpad (1.25rem); scroll
	// mode uses whatever Margins the reader chose.
	const chromeGutter = $derived(paged ? '1.25rem' : MARGIN[readerPrefs.margin]);

	// The paged viewport is fixed between the reader chrome and the progress
	// footer; measure their real heights (the chrome wraps to several rows on
	// narrow screens) so the columns never sit under either bar.
	function applyInsets() {
		if (!articleEl) return;
		const top = readerUi.focus ? 0 : (chromeEl?.offsetHeight ?? 54);
		const bot = readerUi.focus ? 0 : (footEl?.offsetHeight ?? 50);
		articleEl.style.setProperty('--pgtop', `${top}px`);
		articleEl.style.setProperty('--pgbot', `${bot}px`);
	}

	/**
	 * A Kindle-style page count. In page-turn mode it's the real column count.
	 *
	 * In scroll mode it used to be word_count / 280 — a fixed guess that ignored
	 * text size, measure and viewport, so the SAME chapter reported a different
	 * number of pages depending on the layout toggle, and "page 4 of 9" meant two
	 * unrelated things. A page is now one screenful of this chapter at the
	 * reader's current settings in either mode, which is what a paged column is
	 * too — so the figure survives the toggle and responds to the text-size and
	 * width controls the way the reader expects.
	 */
	let scrollPages = $state(1);
	const pageCount = $derived(paged ? pageTotal : scrollPages);
	const currentPage = $derived(
		paged
			? pageIndex + 1
			: Math.min(pageCount, Math.max(1, Math.round(chapterFrac * pageCount) || 1))
	);

	/** Scroll to a fraction of the chapter — drives the draggable scrubber. */
	function scrubTo(frac: number) {
		if (!body) return;
		breakPace(); // a seek, not reading — the settle after it must not be paced
		const rect = body.getBoundingClientRect();
		const bodyTop = window.scrollY + rect.top;
		window.scrollTo({ top: Math.max(0, bodyTop - window.innerHeight + frac * rect.height) });
	}

	// Paging follows the CONTENT's direction, not the UI's: an English book pages
	// left-to-right even under an Arabic shell, and an Arabic book pages
	// right-to-left even under an English one. The browser's own bidi resolution
	// of the body's dir="auto" is the source of truth — no API field to add, and
	// it stays correct through localized()'s silent English fallback.
	let contentRtl = $state(false);
	// offsetLeft of the first element in the column flow. In LTR it is the left
	// padding; in RTL the columns overflow LEFT, so offsetLeft counts DOWN from
	// here (measured: 656 → 32 → -592 at pageW 1248). Distance from this origin is
	// direction-agnostic, and in LTR gives byte-identical results to the old
	// `offsetLeft / pageW`.
	let flowOrigin = 0;

	/** Which page a body child (paragraph) sits on — transform-independent. */
	function pageOf(el: HTMLElement): number {
		return pageOfOffset(el.offsetLeft, flowOrigin, pageW);
	}
	/**
	 * Index of the paragraph a reader on page p is reading: the first one, in
	 * flow order, that starts on it — or, when one long paragraph fills the whole
	 * page, the one carried onto it from an earlier page (not 0, the top of the
	 * chapter). Flow order, not the smallest offsetTop: on a two-column spread
	 * the top of the right column is higher than a paragraph starting midway
	 * down the left one, but comes after it.
	 */
	function firstIndexOnPage(p: number): number {
		if (!body) return 0;
		const kids = body.children;
		let carried = 0;
		for (let i = 0; i < kids.length; i++) {
			const at = pageOf(kids[i] as HTMLElement);
			if (at === p) return i;
			if (at > p) break;
			carried = i;
		}
		return carried;
	}

	/** The paragraph the reader is on, in either layout. topVisibleIndex asks a
	 *  vertical question with no meaning in page mode, where every column shares
	 *  one top — it answered 0 on every page. */
	function currentIndex(): number {
		return paged ? firstIndexOnPage(pageIndex) : topVisibleIndex();
	}

	/**
	 * Re-measure the page width and count from the current layout, keeping the
	 * reader's place — on the paragraph they were reading, in the chapter's
	 * ending, or on the last page — rather than the same page NUMBER with other
	 * text on it after a re-flow (text settings, resize, a late font, the plan
	 * strip or reflection box arriving). `keep` is false only for the
	 * chapter-open placement, which positions the reader itself.
	 */
	function measurePages(keep = true) {
		if (!paged || !articleEl || !pager) return;
		const before = pageTotal;
		const measured = keep && !!body && (before > 1 || stickToLast);
		const wasLast = measured && (stickToLast || pageIndex >= before - 1);
		const endStart = chapterEndEl?.firstElementChild;
		const endWas = measured && endStart ? pageOfNode(endStart) : -1;
		const inEnd = endWas >= 0 && pageIndex >= endWas;
		const at = measured ? firstIndexOnPage(pageIndex) : -1;
		applyInsets();
		const w = articleEl.clientWidth;
		pageW = w;
		// Hand the fixed edge page-turn arrows the REAL column width, in px. They're
		// siblings of the <article>, not descendants, so they can't inherit its
		// --reading-measure to work it out themselves — and the article's own
		// max-width is a `var(--reading-measure)` expression that resolves to nothing
		// outside it. With this they park just outside the actual column instead of
		// guessing a fixed spread (which ran a wide measure's text under them).
		document.documentElement.style.setProperty('--reader-col-w', `${w}px`);
		// Apply the column width + count imperatively so the scrollWidth read below
		// reflows against them synchronously (Svelte's reactive style flush is async).
		pager.style.setProperty('--page-w', `${w}px`);
		pager.style.setProperty('--cols', `${cols}`);
		// Resolve the content direction, then drive the column flow from it. Setting
		// it on the pager (rather than letting it inherit the locale) is what makes
		// the column geometry match the text.
		contentRtl = body ? getComputedStyle(body).direction === 'rtl' : false;
		pager.style.direction = contentRtl ? 'rtl' : 'ltr';
		// Sign for the page transform: RTL pages advance to the right.
		pager.style.setProperty('--page-dir', contentRtl ? '-1' : '1');
		flowOrigin = titleEl ? titleEl.offsetLeft : 0;
		// Pages are `pageW`-wide windows over the column flow. ceil (with a small
		// epsilon to absorb sub-pixel over-report) counts a trailing partial page —
		// needed for a two-column spread whose last page may hold a single column.
		pageTotal = w > 0 ? Math.max(1, Math.ceil(pager.scrollWidth / w - 0.02)) : 1;
		if (pageIndex > pageTotal - 1) pageIndex = pageTotal - 1;
		if (!measured) return;
		const el = body!.children[at] as HTMLElement | undefined;
		const target = wasLast
			? pageTotal - 1
			: inEnd && endStart
				? pageOfNode(endStart) + (pageIndex - endWas)
				: el
					? pageOf(el)
					: pageIndex;
		if (target !== pageIndex) goToPage(target, false);
	}

	/** Screenfuls of prose in scroll mode — the same unit paged mode counts. */
	function measureScrollPages() {
		if (!body) return;
		const usable = window.innerHeight - (chromeEl?.offsetHeight ?? 0) - (footH || (footEl?.offsetHeight ?? 0));
		scrollPages = usable > 0 ? Math.max(1, Math.ceil(body.scrollHeight / usable)) : 1;
	}

	// Opened with ?pg=last (a backward turn from the next chapter): stay on the
	// last page while late content grows the count, until the reader turns.
	let stickToLast = false;

	/** Turn to page p, persisting the paragraph now at the top of the page. */
	function goToPage(p: number, save = true) {
		if (save) stickToLast = false;
		pageIndex = Math.min(pageTotal - 1, Math.max(0, p));
		chapterFrac = pageTotal > 1 ? pageIndex / (pageTotal - 1) : 1;
		if (save) {
			topIndex = firstIndexOnPage(pageIndex);
			// Not gated on listen.status like the scroll handlers: paged mode is
			// force-disabled while listening (`paged` derives on listen.status ===
			// 'idle'), so a page turn can't happen mid-listen to clobber the resume.
			saveScrollAnchor(slug, chapter.order, topIndex);
			samplePace(topIndex);
			// Paging to the last page = reached the end. `save` is false on the
			// initial restore, so opening mid-chapter at the last page doesn't fire.
			if (pageIndex >= pageTotal - 1) markChapterComplete();
		}
	}

	/** Which page any element in the pager sits on. From rects, not offsetLeft:
	 *  it can be any descendant, and it shares the pager's transform with the
	 *  title. The 1px nudge absorbs sub-pixel rects that land just short of a
	 *  page boundary. */
	function pageOfNode(el: Element): number {
		if (!titleEl) return 0;
		const r = el.getBoundingClientRect();
		const o = titleEl.getBoundingClientRect();
		return contentRtl
			? pageOfOffset(r.right - 1, o.right, pageW)
			: pageOfOffset(r.left + 1, o.left, pageW);
	}
	/** Keyboard focus landing on another page (Tab onto the plan strip, a
	 *  scripture link, the chapter's ending) turns to that page. The paged
	 *  article is `overflow: clip`, so the browser has no scroller to reveal
	 *  the element with and cannot shift the columns under the translate. */
	function onArticleFocusIn(e: FocusEvent) {
		if (!paged || !(pageW > 0)) return;
		const p = pageOfNode(e.target as Element);
		// Not saved: passing through links on the way elsewhere is not reading
		// there, and must not move the resume point or finish the chapter.
		if (p !== pageIndex) goToPage(p, false);
	}

	/** A faint fade played on each discrete page turn — the incoming page eases up
	 *  from slightly dim as it slides in, a gentler transition than the bare
	 *  translateX. Imperative (Web Animations) so it fires ONLY on a real turn, not
	 *  on every scrubber step (which calls goToPage directly), and self-restarts
	 *  cleanly turn after turn. Silent under prefers-reduced-motion. */
	function playTurnFade() {
		if (!pager || reduceMotion?.matches) return;
		pager.animate?.(
			[{ opacity: 0.6 }, { opacity: 1 }],
			{ duration: 300, easing: 'cubic-bezier(0.22, 0.61, 0.36, 1)' }
		);
	}

	/** Turn forward/back a page, rolling over to the adjacent chapter at the ends. */
	function turnPage(dir: 1 | -1) {
		const next = pageIndex + dir;
		if (next < 0) {
			if (chapter.prev) goto(chapterHref(chapter.prev.order, 'last'));
		} else if (next > pageTotal - 1) {
			gotoChapter(chapter.next);
		} else {
			goToPage(next);
			playTurnFade();
		}
	}

	// Elements a tap or swipe must leave alone — the reader's own interactive
	// affordances. One list, shared by the touch-start guard and the click guard.
	const INTERACTIVE =
		'a, button, summary, [role="button"], mark, input, textarea, select, .selbar, .define-pop, .scripture-pop';

	// Pointer type is stable for a session — query it once, not per click.
	const coarsePointer = browser ? window.matchMedia('(pointer: coarse)') : null;

	// --- Touch swipe-to-turn (paged mode) --------------------------------------
	// A one-finger horizontal drag follows the page with the finger and snaps on
	// release. Touch only (mouse/desktop keeps the click zones + edge arrows), and
	// only once the drag is clearly horizontal, so a vertical touch is left to do
	// nothing in this fixed, non-scrolling viewport. The live offset is a `--drag`
	// px added to the pager transform; the raw travel (not the rubber-banded one)
	// decides the turn, so a firm swipe still rolls over to the next chapter.
	let dragStartX = 0;
	let dragStartY = 0;
	let dragRawDx = 0;
	let dragRawDy = 0;
	let dragActive = false;
	let dragging = $state(false);
	// A tap that only just crossed the drag threshold can still emit a synthetic
	// click; ignore any click within this window of a swipe so the tap-turn
	// doesn't fire on top of it. A timestamp, not a latched flag — a real swipe
	// emits no click at all, and a stale flag would then eat the next honest tap.
	let lastSwipeEnd = 0;

	function onTouchStart(e: TouchEvent) {
		if (!paged || e.touches.length !== 1) return;
		const el = e.target as HTMLElement;
		if (el.closest(INTERACTIVE)) return;
		dragActive = true;
		dragging = false;
		dragStartX = e.touches[0].clientX;
		dragStartY = e.touches[0].clientY;
	}
	function onTouchMove(e: TouchEvent) {
		if (!dragActive) return;
		const dx = e.touches[0].clientX - dragStartX;
		const dy = e.touches[0].clientY - dragStartY;
		if (!dragging) {
			if (Math.abs(dx) < 12 || Math.abs(dx) <= Math.abs(dy)) return; // not yet a page drag
			dragging = true;
		}
		e.preventDefault(); // the gesture is ours now — don't also bounce the page
		dragRawDx = dx;
		dragRawDy = dy;
		const damped = dampDrag(dx, pageIndex === 0, pageIndex >= pageTotal - 1, contentRtl);
		pager?.style.setProperty('--drag', `${damped}px`);
	}
	function onTouchEnd() {
		if (!dragActive) return;
		dragActive = false;
		if (!dragging) return;
		const turn = swipeTurn(dragRawDx, dragRawDy, pageW, contentRtl);
		pager?.style.setProperty('--drag', '0px'); // settle back / animate the snap
		if (turn === 'next') turnPage(1);
		else if (turn === 'prev') turnPage(-1);
		dragging = false;
		// Only a drag short enough to still register as a tap emits a synthetic
		// click; a real (long) swipe emits none, so arming the guard for it would
		// only eat a deliberate tap that lands within the window right after.
		if (Math.abs(dragRawDx) < 24) lastSwipeEnd = performance.now();
	}
	function onTouchCancel() {
		if (!dragActive) return;
		dragActive = false;
		dragging = false;
		pager?.style.setProperty('--drag', '0px');
	}

	// touchmove has to be NON-passive so it can preventDefault — a horizontal page
	// swipe near the screen edge would otherwise trigger the browser's own
	// back/forward gesture. Svelte registers `ontouchmove={...}` as passive, so
	// bind it by hand instead.
	function swipeMove(node: HTMLElement) {
		node.addEventListener('touchmove', onTouchMove, { passive: false });
		return {
			destroy() {
				node.removeEventListener('touchmove', onTouchMove);
			}
		};
	}

	// --- Peek the chrome in focus mode -----------------------------------------
	// Focus mode hides the reader chrome; a keyboard has Esc, but a phone doesn't.
	// A swipe DOWN from the top edge briefly summons the chrome (Aa, Contents,
	// Listen, the focus toggle) so the reader can reach a control without leaving
	// immersive reading. It re-hides after a few seconds — but not while a panel
	// it opened is still up.
	let peeking = $state(false);
	let peekTimer: ReturnType<typeof setTimeout> | undefined;
	let peekTrackY = false;
	let peekStartY = 0;
	// Derive the visible peek from focus rather than resetting `peeking` in an
	// effect: leaving focus hides the chrome for free, no stale-state cleanup.
	const showPeek = $derived(readerUi.focus && peeking);
	function schedulePeekHide() {
		clearTimeout(peekTimer);
		peekTimer = setTimeout(() => {
			// Hold the chrome up while a panel it opened is still in use; otherwise
			// hide. Bounded — once focus ends or the panel closes, it stops.
			if (readerUi.focus && readerUi.panelOpen) return schedulePeekHide();
			peeking = false;
		}, 4000);
	}
	function onWinTouchStart(e: TouchEvent) {
		// Intentional pull-from-top affordance: a gesture STARTING in the top-edge
		// band and dragging down summons the chrome. The listener is passive, so it
		// never blocks a scroll — at worst a rare top-edge scroll-up also peeks.
		peekTrackY = readerUi.focus && e.touches.length === 1 && e.touches[0].clientY <= 48;
		if (peekTrackY) peekStartY = e.touches[0].clientY;
	}
	function onWinTouchMove(e: TouchEvent) {
		if (!peekTrackY) return;
		if (e.touches[0].clientY - peekStartY > 40) {
			peekTrackY = false;
			peeking = true;
			schedulePeekHide();
		}
	}
	onDestroy(() => {
		clearTimeout(peekTimer);
		clearTimeout(returnTimer);
		clearTimeout(syncTimer);
		// Leaving the reader: drop the paged-column width so it can't skew another
		// page's :root (only this route's edge arrows read it).
		if (browser) document.documentElement.style.removeProperty('--reader-col-w');
	});

	onMount(() => {
		readerPrefs.init();
		listen.init();
	});

	// Per-chapter setup: progress, marks, restore scroll, observe title.
	$effect(() => {
		const s = slug;
		const order = chapter.order;
		const language = getLang();

		// Consume any audiobook roll-over intent up front (synchronously, so a
		// throw later in setup can't strand it): we roll into playback only if
		// THIS is the chapter read-aloud asked to continue into, not one the
		// reader picked by hand in the meantime.
		const rollInto = autoContinueOrder === order;
		autoContinueOrder = null;

		// Arriving from a bookmark / notebook deep-link (?p=N): seed the scroll
		// anchor to N *before* saveProgress reads it, so the book's resume point
		// records paragraph N. Without this, saveProgress ran with no anchor yet
		// and stored paragraph 0 — leaving the chapter before scrolling threw the
		// bookmarked spot away.
		const pParam = $page.url.searchParams.get('p');
		const jumpP = pParam !== null ? Number(pParam) : NaN;
		// A deep-link jump strands the reader: saveProgress below moves the book's
		// resume point to the target, so the spot they left is gone. Read it FIRST
		// and offer a way back (only when it really is somewhere else).
		clearTimeout(returnTimer);
		returnTo = null;
		// (A bare `?p=` is Number('') === 0 — finite, but not a jump.)
		const deliberateJump = Number.isFinite(jumpP) && pParam !== '';
		const ownJump = deliberateJump && ownJumpTarget === `${order}:${jumpP}`;
		// Consumed by its own arrival — or dropped by any plain navigation, so a
		// jump that never landed (cancelled, redirected) cannot linger to mute a
		// later genuine deep link to the same spot.
		if (ownJump || !deliberateJump) ownJumpTarget = '';
		if (deliberateJump && !ownJump) {
			const prior = getProgressRecord(s);
			if (prior && (prior.order !== order || prior.paragraph_index !== jumpP)) {
				offerReturn({ order: prior.order, p: prior.paragraph_index });
			}
		}
		if (Number.isFinite(jumpP) && jumpP > 0) saveScrollAnchor(s, order, jumpP);

		// Ask the account where it last was (answered by its own effect, once
		// the session has settled). This device's record is read HERE, before
		// saveProgress: that keeps `at` when the position is unchanged, but a
		// deep link moves it. Not after a deliberate jump (a bookmark, a search
		// hit): the reader chose that spot.
		clearTimeout(syncTimer);
		syncOffer = null;
		syncAsk =
			!deliberateJump && !syncDismissed.has(s)
				? { slug: s, order, language, local: getProgressRecord(s) }
				: null;

		saveProgress(s, order, language);
		bookmarks.load('book', s);
		// A new chapter: its paragraph lengths are counted at the first pace
		// sample (not here — see samplePace), and that sample starts a fresh
		// pair: the open itself is not reading.
		paraWords = [];
		breakPace();

		// A backward chapter turn in page mode asks to land on the last page.
		const wantLast = $page.url.searchParams.get('pg') === 'last';

		(async () => {
			await tick();
			if (paged) {
				measurePages(false);
				let target = 0;
				stickToLast = wantLast;
				if (wantLast) target = pageTotal - 1;
				else if (Number.isFinite(jumpP) && body?.children[jumpP]) {
					target = pageOf(body.children[jumpP] as HTMLElement);
				} else {
					const rec = getProgressRecord(s);
					const idx =
						getScrollAnchor(s, order) ??
						(rec && rec.order === order ? rec.paragraph_index : null);
					if (idx && body?.children[idx]) target = pageOf(body.children[idx] as HTMLElement);
				}
				goToPage(target, false);
			} else if (Number.isFinite(jumpP) && body?.children[jumpP]) {
				placeAfterLayout(() => {
					const el = body?.children[jumpP];
					if (!el) return;
					el.scrollIntoView({ block: 'start' });
					window.scrollBy(0, -HEADER_OFFSET);
				});
			} else {
				restoreScroll(s, order);
			}
			if (!paged) updateFraction();
			// Rolled over from the previous chapter's read-aloud: pick playback up
			// at the top of this one (intent already consumed synchronously above).
			if (rollInto) reader.startListening(0);
		})();
	});

	// Re-measure the page count when the layout changes under us — text prefs,
	// freshly rendered marks — so the "Page X / Y" total and the scrubber stay
	// honest. Initial positioning is owned by the per-chapter effect above; this
	// only re-counts and clamps, so it never fights that effect.
	$effect(() => {
		if (paged) return;
		void chapter.order;
		void readerPrefs.scale;
		void readerPrefs.leading;
		void readerPrefs.measure;
		void readerPrefs.font;
		void readerUi.focus;
		untrack(() => {
			(async () => {
				await tick();
				measureScrollPages();
				// A newly chosen face is still downloading at this point: the
				// measure above ran on fallback metrics and triggered the fetch.
				// Count again once it lands, or the total stays stale.
				await document.fonts?.ready;
				measureScrollPages();
			})();
		});
	});

	$effect(() => {
		if (!paged) return;
		void readerPrefs.scale;
		void readerPrefs.leading;
		void readerPrefs.measure;
		void readerPrefs.font;
		void marks.list;
		void readerUi.focus;
		void cols; // one- vs two-column spread changes the page width and count
		untrack(() => {
			(async () => {
				await tick();
				measurePages();
				// Again once a newly chosen face has loaded (see the scroll effect).
				await document.fonts?.ready;
				measurePages();
			})();
		});
	});

	// One re-measure per frame, however many triggers fire in it.
	let measureQueued = false;
	function scheduleMeasure() {
		if (measureQueued) return;
		measureQueued = true;
		requestAnimationFrame(() => {
			measureQueued = false;
			untrack(() => measurePages());
		});
	}

	// The blocks above the chapter (the plan strip, fetched after the chapter
	// renders; the language notice, which can be dismissed) and the
	// chapter's ending (its reflection box is imported on demand) change size
	// after the pages were first counted — `?pg=last` then landed a page short.
	// The ending's own box is fragmented across columns and does not report its
	// contents growing, so watch its blocks (each kept whole by break-inside).
	// Only a HEIGHT change can move the page count past the other triggers; the
	// first report of each block and width-only reports are ignored.
	$effect(() => {
		if (!paged || typeof ResizeObserver === 'undefined' || !chapterEndEl) return;
		const end = chapterEndEl;
		const lead = leadEl;
		const heights = new WeakMap<Element, number>();
		const ro = new ResizeObserver((entries) => {
			let grew = false;
			for (const e of entries) {
				const h = e.contentRect.height;
				const was = heights.get(e.target);
				heights.set(e.target, h);
				if (was !== undefined && Math.abs(was - h) > 0.5) grew = true;
			}
			if (grew) scheduleMeasure();
		});
		if (lead) ro.observe(lead);
		for (const el of end.children) ro.observe(el);
		// A block appearing or leaving (the plan's reflection) re-flows too.
		const mo = new MutationObserver((records) => {
			for (const r of records) for (const n of r.addedNodes) if (n instanceof Element) ro.observe(n);
			scheduleMeasure();
		});
		mo.observe(end, { childList: true });
		return () => {
			ro.disconnect();
			mo.disconnect();
		};
	});

	// Keep the count correct — and the one/two-column choice current — across
	// viewport resizes / orientation changes.
	$effect(() => {
		if (!browser) return;
		const onResize = () => {
			viewportW = window.innerWidth;
			if (paged) scheduleMeasure();
			else untrack(measureScrollPages);
		};
		window.addEventListener('resize', onResize);
		return () => window.removeEventListener('resize', onResize);
	});

	/** The plan day covering a chapter of THIS book, when following a plan. */
	function planDayFor(order: number): number | null {
		const d = plan?.days.find((x) => x.book_slug === slug && x.chapter_order === order);
		return d?.day ?? null;
	}

	/**
	 * A chapter link that carries the reader's plan context (?plan=&day=) when the
	 * target chapter is itself a day of the plan they're following — recomputing
	 * the day rather than passing the old one through. Plain link otherwise, since
	 * a chapter outside the plan means they've stepped off its path.
	 */
	function chapterHref(order: number, pg?: 'last'): string {
		const qs = new URLSearchParams();
		if (pg) qs.set('pg', pg); // land on the last page when paging backwards
		const day = planDayFor(order);
		if (plan && day) {
			qs.set('plan', plan.slug);
			qs.set('day', String(day));
		}
		if (edition === 'modern') qs.set('edition', 'modern');
		const q = qs.toString();
		return localizeHref(`/books/${slug}/${order}${q ? `?${q}` : ''}`);
	}

	/** The current chapter in the opposite edition — drives the Modern ⇄ Original
	 *  toggle. Keeps the reader's plan context on the same chapter. */
	function editionToggleHref(): string {
		const qs = new URLSearchParams();
		if (edition !== 'modern') qs.set('edition', 'modern'); // flip to modern
		const day = planDayFor(chapter.order);
		if (plan && day) {
			qs.set('plan', plan.slug);
			qs.set('day', String(day));
		}
		const q = qs.toString();
		return localizeHref(`/books/${slug}/${chapter.order}${q ? `?${q}` : ''}`);
	}

	function gotoChapter(target: { order: number } | null) {
		if (target) goto(chapterHref(target.order));
	}

	/** Scroll a screenful (0.85 of the viewport) — shared by the space key and the
	 *  opt-in tap-to-page-down, so "a page" is one number in one place. */
	function pageScroll(dir: 1 | -1) {
		window.scrollBy({ top: dir * window.innerHeight * 0.85, behavior: 'smooth' });
	}

	/** Keyboard: ←/→ chapters (or paragraph skip while listening), space pages. */
	function onKeydown(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		const el = e.target as HTMLElement;
		if (
			el?.closest?.('input, textarea, select, [contenteditable="true"]') ||
			reader.open ||
			define.open ||
			// These two were missing, so a page turned underneath an open scripture
			// popover or text-settings panel while the reader was using it.
			scripture.open ||
			readerUi.panelOpen ||
			tocOpen ||
			searchOpen ||
			notesOpen
		) {
			// Escape still has to work from inside a panel — it is how you leave.
			if (e.key === 'Escape' && readerUi.focus && !reader.open) readerUi.exitFocus();
			return;
		}
		// Focus mode had no keyboard exit at all: exitFocus() existed and nothing
		// called it, so the only way out was finding the floating pill.
		if (e.key === 'Escape' && readerUi.focus) {
			e.preventDefault();
			readerUi.exitFocus();
			return;
		}
		if (e.key === 'ArrowRight') {
			e.preventDefault();
			// Physical key → logical direction: in RTL, right is BACKWARDS.
			if (listen.status !== 'idle') listen.skip(1);
			else if (paged) turnPage(contentRtl ? -1 : 1);
			else gotoChapter(chapter.next);
		} else if (e.key === 'ArrowLeft') {
			e.preventDefault();
			if (listen.status !== 'idle') listen.skip(-1);
			else if (paged) turnPage(contentRtl ? 1 : -1);
			else gotoChapter(chapter.prev);
		} else if (e.key === ' ') {
			// Space on a focused control IN THE TEXT presses it — "Mark day done",
			// Next chapter and the reflection's Save live inside the pages. A
			// toolbar button keeps focus after a click, and Space there still pages.
			if (el?.closest?.('.pager') && el.closest(INTERACTIVE)) return;
			e.preventDefault();
			if (paged) turnPage(e.shiftKey ? -1 : 1);
			else pageScroll(e.shiftKey ? -1 : 1);
		}
	}

	/**
	 * Tapping the page. In PAGED mode this is how you turn: on TOUCH the screen is
	 * split into thirds (Kindle's model) — the right third goes forward, the left
	 * third back, and the centre third toggles the chrome (immersive focus mode).
	 * The split is physical; RTL content flips which side is "next" (handled in
	 * tapTurn). On a fine pointer only the outer 15% stays live (deadZone 0.7):
	 * there a click in the body is for selecting, and the edge arrows are the
	 * affordance, so a half-screen click zone would fight normal clicking — and
	 * the centre does nothing rather than stealing a text-selection click.
	 *
	 * In SCROLL mode a tap turns nothing unless the reader opted into
	 * `tapToScroll`, and then only in the lower part of the screen, on touch —
	 * scrolls down a screenful. This is deliberately NOT the old removed
	 * behaviour, where an implicit edge tap in scroll mode threw a phone reader
	 * into the previous/next CHAPTER off ~34px of live body text, unmarked and
	 * hard to undo. Changing which page you're on is fine and reversible;
	 * changing which chapter you're in off a stray tap is not.
	 */
	function onArticleClick(e: MouseEvent) {
		// A click right on the heels of a swipe is that swipe's synthetic tap.
		if (performance.now() - lastSwipeEnd < 400) return;
		if (reader.onScriptureClick(e)) return;
		const el = e.target as HTMLElement;
		if (el.closest(INTERACTIVE)) return;
		if (window.getSelection()?.toString()) return;
		const coarse = coarsePointer?.matches ?? false;
		if (paged) {
			// Touch: Kindle-style thirds — outer thirds turn, the centre third
			// toggles the chrome (deadZone 0.34). Fine pointer keeps the outer-15%
			// live zone (deadZone 0.7) and does NOTHING in the centre, so a click in
			// the body is still for selecting text, not summoning toolbars.
			const turn = tapTurn(e.clientX, window.innerWidth, contentRtl, coarse ? 0.34 : 0.7);
			if (turn === 'next') turnPage(1);
			else if (turn === 'prev') turnPage(-1);
			else if (coarse) readerUi.toggleFocus();
			return;
		}
		if (readerPrefs.tapToScroll && coarse && e.clientY / window.innerHeight > 0.66) {
			pageScroll(1);
		}
	}

	// Prefetch the next chapter when the browser is idle: the plain GET flows
	// through the service worker's stale-while-revalidate cache, so the next
	// tap is instant and the chapter becomes readable offline too.
	$effect(() => {
		const next = chapter.next;
		const s = slug;
		const language = editionLang(edition);
		if (!next) return;
		const url = `${API_BASE_URL}/api/library/books/${s}/chapters/${next.order}/?language=${language}`;
		// timeout guarantees the prefetch even when idle never comes (busy or
		// backgrounded tab); setTimeout covers browsers without rIC (Safari).
		const idle =
			'requestIdleCallback' in window
				? (fn: () => void) =>
						(window as Window & {
							requestIdleCallback: (cb: () => void, opts?: { timeout: number }) => number;
						}).requestIdleCallback(fn, { timeout: 3000 })
				: (fn: () => void) => setTimeout(fn, 1500);
		nextPreview = '';
		// A slow fetch for THIS chapter's successor must not land after the reader
		// has turned the page — it would put the chapter they are now reading under
		// "Next". Same cancel-flag shape as the book fetch above.
		let cancelled = false;
		idle(() => {
			if (cancelled) return;
			// The response used to be thrown away; now its opening line feeds the
			// "up next" card, so this is a read as well as a cache warm. It stays a
			// raw fetch of the same URL on purpose — that is what makes the service
			// worker's cache entry the one the navigation will hit; routing it
			// through apiFetch would change the key and warm nothing.
			fetch(url)
				.then((r) => (r.ok ? r.json() : null))
				.then((ch: { body_html?: string } | null) => {
					if (!cancelled) nextPreview = openingLine(ch?.body_html ?? '');
				})
				.catch(() => {});
		});
		return () => {
			cancelled = true;
		};
	});

	// Reading-plan context (?plan=<slug>&day=<n>): show the Day N of M strip and
	// a mark-done action. The plan is fetched lazily — only when the params are
	// present — and cached across day navigations within the same plan.
	const planSlug = $derived($page.url.searchParams.get('plan'));
	const planDay = $derived(Number($page.url.searchParams.get('day')) || 0);
	let plan = $state<PlanDetail | null>(null);
	$effect(() => {
		const s = planSlug;
		if (!s) {
			plan = null;
			return;
		}
		if (plan?.slug === s) return;
		getPlan(s, getLang())
			.then((p) => (plan = p))
			.catch(() => (plan = null));
	});

	/** Mark today done, then continue: next day's chapter, or back to the plan. */
	function completePlanDay() {
		if (!plan || !planDay) return;
		planProgress.markDone(plan.slug, planDay);
		const next = planProgress.nextDay(plan.slug, plan.day_count);
		const nextEntry = next && plan.days.find((d) => d.day === next);
		if (nextEntry) {
			goto(
				localizeHref(
					`/books/${nextEntry.book_slug}/${nextEntry.chapter_order}?plan=${plan.slug}&day=${nextEntry.day}`
				)
			);
		} else {
			goto(localizeHref(`/plans/${plan.slug}`));
		}
	}

	function topVisibleIndex(): number {
		if (!body) return 0;
		const kids = body.children;
		for (let i = 0; i < kids.length; i++) {
			if (kids[i].getBoundingClientRect().bottom > HEADER_OFFSET) return i;
		}
		return 0;
	}

	function restoreScroll(s: string, order: number) {
		// Prefer the device-local anchor; fall back to the synced resume point so
		// "continue reading" lands on the right paragraph on a fresh device too.
		const rec = getProgressRecord(s);
		const idx =
			getScrollAnchor(s, order) ??
			(rec && rec.order === order ? rec.paragraph_index : null);
		if (idx && body && body.children[idx]) {
			placeAfterLayout(() => {
				const el = body?.children[idx];
				if (!el) return;
				el.scrollIntoView({ block: 'start' });
				window.scrollBy(0, -HEADER_OFFSET);
			});
		} else {
			window.scrollTo(0, 0);
		}
	}

	// The reader's pace, fed from the same samples the resume point already
	// produces — "the top paragraph moved from 4 to 7 in 51 s" (see $lib/pace).
	// A pair must be two rest points in one stretch of READING, so it is broken
	// (`lastSample = null`) by anything else that moves the top: a chapter
	// open, a scrub, read-aloud's playback, the tab going away — a backgrounded
	// tab's clock keeps running but nobody is reading.
	let paraWords: number[] = [];
	let lastSample: PaceSample | null = null;
	const breakPace = () => {
		lastSample = null;
	};
	function samplePace(p: number) {
		if (document.visibilityState !== 'visible') {
			breakPace();
			return;
		}
		// Counted lazily, at the first sample of a chapter: this runs from event
		// handlers, where reading `body` tracks nothing. In the chapter effect it
		// made the whole setup re-run on mount, once `bind:this` landed — which
		// re-read this device's record AFTER the open had touched it and killed
		// the cross-device offer on exactly the cold load it exists for.
		if (!paraWords.length && body) paraWords = paragraphWordCounts(body.children);
		const now = Date.now();
		if (lastSample) {
			const d = paceDelta(lastSample, { p, at: now }, paraWords);
			if (d) {
				readingPace.record(d.words, d.ms);
				// Same validated active-reading time feeds "time on site".
				readingTimer.record(d.ms, { kind: 'book', slug, language });
			}
		}
		lastSample = { p, at: now };
	}
	$effect(() => {
		document.addEventListener('visibilitychange', breakPace);
		return () => document.removeEventListener('visibilitychange', breakPace);
	});
	$effect(() => {
		// Read-aloud moves the top at the voice's pace, not the reader's: a pair
		// straddling a listen would write the TTS speed into the reading pace.
		void listen.status;
		breakPace();
	});

	// Throttled save of the topmost visible paragraph as the scroll anchor.
	//
	// Through `topVisibleIndex()` — the same question the restore's contract is
	// written against. This used to ask its own: the first paragraph whose TOP
	// had passed the header line, minus one. Restore parks paragraph N just
	// below that line, and that rule answers N-1 for the same screen, so a
	// chapter reopened where it was left recorded one paragraph earlier each
	// time. Two rules for one contract is precisely the drift the shared
	// HEADER_OFFSET was introduced to end.
	let saveTimer: ReturnType<typeof setTimeout> | undefined;
	function onScroll() {
		trackChrome();
		clearTimeout(saveTimer);
		saveTimer = setTimeout(() => {
			if (!body) return;
			updateFraction();
			// While actively playing, listen.start's onAdvance owns the resume point
			// (the spoken paragraph); don't overwrite it with the viewport-top one.
			// While PAUSED we do save — the reader may be scrolling ahead to read.
			if (listen.status !== 'playing') {
				const top = topVisibleIndex();
				saveScrollAnchor(slug, chapter.order, top);
				samplePace(top);
			}
			// Scrolled to the bottom of the chapter. markChapterComplete ignores the
			// post-open settle window, so the restore-scroll landing at a saved
			// end-of-chapter position doesn't count as finishing.
			if (chapterFrac >= 0.999) markChapterComplete();
		}, 250);
	}

	const cite = $derived({
		author: chapter.author_name,
		book: chapter.book_title,
		chapter: chapterName(chapter.order, chapter.title),
		url: $page.url.href
	});

	// Everything attached to the TEXT — highlights, notes, the selection bar,
	// listen follow-along, search hits — is shared with the sermon and biography
	// readers. Position is not: page-turn mode has no scroll offset, so the
	// paging code above stays here and hands the machinery its own answer for
	// "which paragraph am I on".
	const reader = createReaderText({
		kind: () => 'book',
		slug: () => slug,
		order: () => chapter.order,
		// The RESOLVED edition (`data.language`), not the requested one. Marks
		// index the characters of the text actually on the page, and +page.ts
		// falls back to English on a 404 — so a book with no Arabic copy read
		// under /ar shows English prose, and tagging those marks `ar` would
		// mispaint them the day an Arabic translation ships. Same for
		// ?edition=modern on a book that has no modern edition.
		language: () => language,
		body: () => body,
		topIndex: currentIndex,
		reveal: (el) => (paged ? goToPage(pageOfNode(el), false) : el.scrollIntoView({ block: 'center', behavior: 'smooth' })),
		listenTitle: () => chapterName(chapter.order, chapter.title),
		listenArtist: () => `${chapter.author_name} · ${chapter.book_title}`,
		cite: () => cite,
		searchQuery: () => $page.url.searchParams.get('q') ?? '',
		// Audiobook roll-over: when a chapter finishes reading itself, continue
		// into the next one. Only when there is a next chapter — the last chapter
		// simply stops. gotoChapter navigates; the per-chapter effect resumes.
		onListenFinish: () => {
			if (chapter.next) {
				autoContinueOrder = chapter.next.order;
				gotoChapter(chapter.next);
			}
		}
	});

	// Shared by both <ReaderControls> mounts (popover, phone sheet). `layout`
	// and `margins` stay literal on each tag — readerSurfaces.test.ts reads them.
	const rcProps = $derived({
		align: readerPrefs.effectiveAlign(paged),
		sample: metaDescription.slice(0, 90)
	});

	// --- Auto-hide the top bar on scroll-down (scroll mode) --------------------
	// More reading area without a mode to discover: the top bar slides away as you
	// read on and returns the moment you scroll back up (or reach the top). The
	// bottom progress bar and the 2px progress hairline stay. `barHidden` is the
	// raw scroll-direction intent; `hideChrome` gates it so the bar is only ever
	// hidden in plain scroll reading — never in page-turn or focus mode, and never
	// while a drawer, the text-settings panel, or a focus-peek owns the screen.
	let barHidden = $state(false);
	let lastScrollY = 0;
	function trackChrome() {
		const y = window.scrollY;
		barHidden = nextBarHidden(barHidden, y, lastScrollY, window.innerHeight);
		lastScrollY = y;
	}
	const hideChrome = $derived(
		barHidden &&
			!paged &&
			!readerUi.focus &&
			!readerUi.panelOpen &&
			!moreOpen &&
			!reader.open &&
			!showPeek
	);
	// A fresh chapter — or leaving focus mode — opens with the bar visible; the
	// reader's own scrolling re-hides it.
	$effect(() => {
		void chapter.order;
		void readerUi.focus;
		barHidden = false;
	});
</script>

<Seo
	title={titleTag}
	description={metaText}
	{canonical}
	{hreflang}
	ogType="article"
	structuredData={[chapterLd, crumbsLd]}
/>
<svelte:window
	onscroll={onScroll}
	onkeydown={onKeydown}
	ontouchstart={onWinTouchStart}
	ontouchmove={onWinTouchMove}
/>

<!-- Compact "where you are" — book · chapter. One definition, rendered both as
     the inline label (≥sm) and the phone location line below the controls.
     When the chapter's name is just the book's title (a single-work volume like
     "Absolute Surrender"), drop the redundant "Book · " prefix. -->
{#snippet locationLabel()}{@const chap = chapterName(chapter.order, chapter.title)}{#if chapter.book_title !== chap}<span class="text-muted">{chapter.book_title} · </span>{/if}{chap}{/snippet}

<!-- Reader top bar: breadcrumb / context + controls. Hidden in focus mode,
     except a transient peek summoned by a swipe-down from the top (see above). -->
{#if !readerUi.focus || showPeek}
	<!-- Pinned to the top. In scroll mode it's `sticky` (rides the scroll, then
	     sticks); in page mode nothing scrolls, so it's `fixed` — and crucially a
	     `sticky` sibling makes Chromium drop the top line of the reader's later
	     paged columns (a paint bug), which `fixed` avoids.

	     `fixed` measures from the VIEWPORT, though, and the global nav is
	     `.appnav-static` here — in flow, at the top, and (since nothing scrolls
	     in page mode) never going anywhere. So `top-0` parked this whole bar
	     underneath it at z-10 vs the nav's z-40: every control in it, Contents
	     and Text settings and Focus included, was invisible and unclickable at
	     every viewport width. `.reader-chrome.fixed` below starts it beneath the
	     nav instead. Scroll mode is untouched — there the nav really does ride
	     away, and 0 is right. -->
	<div
		bind:this={chromeEl}
		class="reader-chrome top-0 inset-x-0 z-10 border-b border-border bg-bg/90 backdrop-blur"
		class:fixed={paged || showPeek}
		class:sticky={!paged && !showPeek}
		class:peeking={showPeek}
		class:autohidden={hideChrome}
	>
		<div
			class="mx-auto flex items-center justify-between gap-3 py-1.5 sm:py-2.5"
			style="max-width: {chromeMax}; padding-inline: {chromeGutter}"
		>
			<!-- Phone bar: Back · where you are · Contents · "⋯". Chapter turning,
			     Listen and Text settings move to the bottom bar, in thumb reach;
			     the rest folds into "⋯". Eight icons in one row overflowed a 320px
			     phone and left no room to say where you are. -->
			<div class="flex min-w-0 flex-1 items-center gap-0.5 sm:hidden">
				<a
					href={localizeHref(`/books/${slug}`)}
					class="btn btn-icon btn-ghost min-w-11 shrink-0"
					aria-label={t('reader.backToContents')}
					title={t('reader.backToContents')}
					><Icon name="chevron-left" size={20} class="dir-flip" /></a
				>
				<div class="min-w-0 flex-1 text-center">
					<div class="truncate text-small font-semibold text-text">{chapter.book_title}</div>
					<div class="truncate text-small text-muted">{phoneChapterLine}</div>
				</div>
				<button
					class="btn btn-icon btn-ghost min-w-11 shrink-0"
					onclick={() => (tocOpen = true)}
					aria-label={t('reader.contents')}
					title={t('reader.contents')}><Icon name="list" size={20} /></button
				>
				<div
					class="relative shrink-0"
					use:dismissable={{ open: moreOpen, onDismiss: () => (moreOpen = false) }}
				>
					<button
						class="btn btn-icon btn-ghost min-w-11"
						onclick={() => (moreOpen = !moreOpen)}
						aria-expanded={moreOpen}
						aria-controls={moreOpen ? 'reader-more' : undefined}
						aria-label={t('reader.moreTools')}
						title={t('reader.moreTools')}><Icon name="more" size={20} /></button
					>
					{#if moreOpen}
						<!-- A labelled group, not role="menu" (no arrow-key roving) — the
						     same treatment as AccountMenu. -->
						<div id="reader-more" class="account-menu more-group" role="group" aria-label={t('reader.moreTools')}>
							<button
								class="account-item more-item"
								class:text-accent={currentBookmarked}
								onclick={fromMore(toggleBookmark)}
								aria-pressed={currentBookmarked}
								><Icon name="bookmark" size={20} />{currentBookmarked
									? t('reader.removeBookmark')
									: t('reader.bookmark')}</button
							>
							<button class="account-item more-item" onclick={fromMore(() => (searchOpen = true))}
								><Icon name="search" size={20} />{t('reader.search')}</button
							>
							<button class="account-item more-item" onclick={fromMore(() => (notesOpen = true))}
								><Icon name="book" size={20} />{t('notebook.title')}</button
							>
							{#if chapter.has_modern_edition}
								<a
									class="account-item more-item"
									href={editionToggleHref()}
									data-sveltekit-noscroll
									onclick={() => (moreOpen = false)}
									><Icon name="layers" size={20} />{editionLabel}</a
								>
							{/if}
							<button class="account-item more-item" onclick={fromMore(() => readerUi.toggleFocus())}
								><Icon name="maximize" size={20} />{readerUi.focus
									? t('reader.exitFocus')
									: t('reader.focus')}</button
							>
						</div>
					{/if}
				</div>
			</div>
			<!--
				Hidden below `sm`. The controls alone need ~303px of a 360px phone, so
				with this block in the row the bar wrapped to THREE rows — 141px of an
				780px viewport — and squeezed this text to five pixels wide, which is
				not a label, just a thing pushing everything else out of line. The
				article's own breadcrumb sits directly beneath and says the same, so
				nothing is lost by standing this down where there is no room for it.
			-->
			<div class="hidden min-w-0 flex-1 sm:block">
				{#if titleSpy.visible}
					<a href={localizeHref(`/books/${slug}`)} class="text-small text-muted hover:text-text">
						← {chapter.book_title}
					</a>
				{:else}
					<!-- Once the heading scrolls away, show where you are. -->
					<div class="truncate text-small text-text">{@render locationLabel()}</div>
				{/if}
			</div>
			<div class="hidden shrink-0 items-center gap-0.5 sm:flex">
				{#if chapter.prev}
					<a
						href={chapterHref(chapter.prev.order)}
						class="btn btn-icon btn-ghost"
						aria-label={t('reader.previous')}
						title={t('reader.previous')}><Icon name="chevron-left" size={18} /></a
					>
				{/if}
				{#if chapter.next}
					<a
						href={chapterHref(chapter.next.order)}
						class="btn btn-icon btn-ghost"
						aria-label={t('reader.next')}
						title={t('reader.next')}><Icon name="chevron-right" size={18} /></a
					>
				{/if}
				{#if chapter.has_modern_edition}
					<span class="mx-1 h-5 w-px bg-border" aria-hidden="true"></span>
					<a
						href={editionToggleHref()}
						data-sveltekit-noscroll
						class="btn btn-sm btn-ghost px-2"
						class:text-accent={edition === 'modern'}
						title={editionLabel}
						aria-label={editionLabel}
					>
						{edition === 'modern' ? t('reader.original') : t('reader.modern')}
					</a>
				{/if}
				<span class="mx-1 h-5 w-px bg-border" aria-hidden="true"></span>
				<button
					class="btn btn-icon btn-ghost"
					class:text-accent={currentBookmarked}
					onclick={toggleBookmark}
					aria-label={t('reader.bookmark')}
					title={t('reader.bookmark')}
					aria-pressed={currentBookmarked}><Icon name="bookmark" size={18} /></button
				>
				<button
					class="btn btn-icon btn-ghost"
					onclick={() => (tocOpen = true)}
					aria-label={t('reader.contents')}
					title={t('reader.contents')}><Icon name="list" size={18} /></button
				>
				<button
					class="btn btn-icon btn-ghost"
					onclick={() => (searchOpen = true)}
					aria-label={t('reader.search')}
					title={t('reader.search')}><Icon name="search" size={18} /></button
				>
				<button
					class="btn btn-icon btn-ghost"
					onclick={() => (notesOpen = true)}
					aria-label={t('notebook.title')}
					title={t('notebook.title')}><Icon name="book" size={18} /></button
				>
				{#if listen.supported}
					<button
						class="btn btn-icon btn-ghost"
						class:text-accent={listen.status !== 'idle'}
						onclick={() => (listen.status === 'idle' ? reader.startListening() : listen.stop())}
						aria-label={t('reader.listen')}
						title="{t('reader.listen')} · {listenTime(chapter.word_count, listen.rate)}"
						><Icon name="headphones" size={18} /></button
					>
				{/if}
				<!-- `layout`: the chapter reader is the one surface that implements
				     paged mode, so it is the one that offers the switch. -->
				<!-- `sample`: the chapter's opening line, so the panel's live preview
				     restyles the reader's own prose. metaDescription is already the
				     body's plain text. -->
				<!-- Not mounted on phones, where the bottom sheet takes over. -->
				{#if !isPhone}
					<ReaderControls layout margins {...rcProps} />
				{/if}
				<button
					class="btn btn-icon btn-ghost"
					onclick={() => readerUi.toggleFocus()}
					aria-label={t('reader.focus')}
					title={t('reader.focus')}><Icon name="maximize" size={18} /></button
				>
			</div>
		</div>
	</div>
{/if}

<!-- Hidden during a peek: the peeked chrome carries its own focus toggle, and
     the full-width bar would otherwise sit on top of this pill. -->
{#if readerUi.focus && !showPeek}
	<FocusExit />
{/if}

<!-- A full-viewport wash behind the paged columns, so the margins beside the
     measure-capped spread are the same shade as the page — no lighter corners. -->
{#if paged}
	<div class="paged-backdrop" aria-hidden="true"></div>
{/if}

<!-- On the plan strip at the top and under the reflection at the end: in page
     mode those are pages apart, and the end is where a day is finished. -->
{#snippet markDayDone(planSlug: string, day: number)}
	{#if planProgress.isDone(planSlug, day)}
		<span class="text-small font-semibold text-accent">✓ {t('plans.dayDone')}</span>
	{:else}
		<button class="btn btn-sm btn-primary" onclick={completePlanDay}>{t('plans.markDone')}</button>
	{/if}
{/snippet}

<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
<article
	bind:this={articleEl}
	class="mx-auto reading-article pt-12 pb-10"
	class:paged
	class:focus={readerUi.focus}
	class:twocol={cols === 2}
	style="{readerPrefs.styleFor(paged)}; --article-max: {articleMax}"
	onclick={onArticleClick}
	onfocusin={onArticleFocusIn}
	ontouchstart={onTouchStart}
	ontouchend={onTouchEnd}
	ontouchcancel={onTouchCancel}
	use:swipeMove
>
	<Breadcrumb items={crumbs} />

	<!-- The pager wraps everything the reader acts on: the plan strip, the
	     chapter, and its ending. In scroll mode it is display:contents (no
	     effect); in page mode it becomes the translated CSS-column content and
	     anything outside it — only the breadcrumb — is hidden. Keep it that way:
	     readerPagedEnding.test.ts. -->
	<div class="pager" class:dragging bind:this={pager} style="--page-w:{pageW}px; --page-idx:{pageIndex}; --cols:{cols};">
		<div bind:this={leadEl}>
			<LanguageFallbackNotice {fallback} alternates={hreflang.alternates} browsePath="/books" class="mb-6" />
			{#if plan && planDay}
				<div
					class="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface-2 px-4 py-3"
				>
					<div class="min-w-0">
						<a href={localizeHref(`/plans/${plan.slug}`)} class="block truncate text-small font-semibold text-text hover:text-accent">
							{plan.title}
						</a>
						<span class="text-small text-muted">
							{t('plans.day')} {planDay} {t('plans.of')} {plan.day_count}
						</span>
					</div>
					{@render markDayDone(plan.slug, planDay)}
				</div>
			{/if}
		</div>

		<p class="eyebrow chapter-kicker mb-1 text-muted">
			{t('continue.chapter')} {chapter.order} · {readingTime(chapter.word_count)}
			{#if listen.supported}
				· {listenTime(chapter.word_count, listen.rate)}
			{/if}
			{#if chapter.is_modern_edition}
				<span class="ms-1 text-accent">· {t('reader.modernEdition')}</span>
			{/if}
		</p>
		<h1 bind:this={titleEl} class="text-h1 mb-8" dir="auto" lang={contentLang(language)}>{chapterName(chapter.order, chapter.title)}</h1>

		<!-- Body HTML is cleaned server-side to a safe tag subset on ingest. -->
		<!-- eslint-disable-next-line svelte/no-at-html-tags -->
		<div class="reading" bind:this={body} dir="auto" lang={contentLang(language)}>{@html chapter.body_html}</div>

		<!-- The chapter's ending. In page mode it starts on a fresh column, so the
		     last page of every chapter is where to go next (see .chapter-end). -->
		<div class="chapter-end" bind:this={chapterEndEl}>
			<!-- A plan day's reflection: what the reader takes from today's reading,
			     written straight into their Notebook — filed in a collection named for
			     the plan, so a whole plan's reflections gather in one place. Loaded on
			     demand: it brings the journal store, which a plain chapter never needs. -->
			{#if plan && planDay}
				<section class="plan-reflect mt-12 border-t border-border pt-6" aria-labelledby="reflect-heading">
					<h2 id="reflect-heading" class="section-heading">{t('notebook.reflectHeading')}</h2>
					{#await import('$lib/components/notebook/ReflectBox.svelte') then { default: ReflectBox }}
						<ReflectBox
							prompt={t(`notebook.reflectPrompt${reflectPrompt(planDay)}`)}
							title={`${t('plans.day')} ${planDay}: ${chapterName(chapter.order, chapter.title)}`}
							collection={plan.title}
							source={{
								kind: 'book',
								slug,
								order: chapter.order,
								p: 0,
								edition: language,
								title: `${chapter.book_title} · ${chapterName(chapter.order, chapter.title)}`,
								quote: ''
							}}
						/>
					{/await}
					<div class="mt-4">{@render markDayDone(plan.slug, planDay)}</div>
				</section>
			{/if}

			<!-- Scripture index: the passages this chapter treats. Placed here — after
			     the text, before the next-chapter nav — to match the sermon page, which
			     has carried the same row since citations were indexed. The reading comes
			     first and the apparatus sits under it, so a reader in flow scrolls past
			     it to the next chapter and never has to read around it.

			     This is also what makes the scripture graph reciprocal: those pages are
			     linked from /scripture and the sitemap, and now from the 904 English
			     chapters that actually cite something.

			     A chip links to its scripture page when one exists, and to a search for
			     the reference when the citation floor withheld one — never to a page
			     that was not built. English chapters only; `scripture_refs` is empty
			     elsewhere, because the citations behind it are English. -->
			{#if chapter.scripture_refs?.length}
				<div class="mt-10 flex flex-wrap items-center gap-2 border-t border-border pt-5">
					<span class="eyebrow text-muted">{t('reader.scripture')}</span>
					{#each chapter.scripture_refs as entry (entry.ref)}
						<a
							href={entry.page
								? `/scripture/${entry.page.book}/${entry.page.chapter}/` +
									(entry.page.verse ? `${entry.page.verse}/` : '')
								: localizeHref(`/search?q=${encodeURIComponent(entry.ref)}`)}
							class="tag"
						>
							{entry.ref}
						</a>
					{/each}
				</div>
			{/if}

			<!-- One block, so in page mode the way on never splits from its links:
			     the last page always holds Previous/Next. -->
			<div class="end-nav">
				<nav class="mt-14 flex items-stretch justify-between gap-3 border-t border-border pt-6">
					{#if chapter.prev}
						<a
							href={chapterHref(chapter.prev.order)}
							class="btn btn-ghost flex-1 flex-col items-start gap-0.5 text-start"
						>
							<span class="eyebrow text-muted">{t('reader.previous')}</span>
							<span class="text-small">{chapterName(chapter.prev.order, chapter.prev.title)}</span>
						</a>
					{:else}
						<span class="flex-1"></span>
					{/if}
					{#if chapter.next}
						{@const nextWords = bookForProgress?.chapters.find((c) => c.order === chapter.next?.order)?.word_count}
						<a
							href={chapterHref(chapter.next.order)}
							class="btn btn-primary flex-1 flex-col items-end gap-0.5 text-end"
							class:celebrate
							aria-label="{t('reader.next')}: {chapterName(chapter.next.order, chapter.next.title)}"
						>
							<span class="eyebrow opacity-75">{t('reader.next')}</span>
							<span class="text-small">{chapterName(chapter.next.order, chapter.next.title)}</span>
							<!-- The moment of highest intent: say how long it is, and let its
							     opening line do the inviting. Both are optional — the time needs
							     the book fetched, the line needs the prefetch to have landed — so
							     the line's height is reserved: the button must not grow under a
							     thumb that is already aiming at it. -->
							<span class="up-next-meta mt-0.5 block text-micro opacity-75" dir="auto">
								{#if nextWords}{readingTime(nextWords)}{/if}{#if nextWords && nextPreview}
									·
								{/if}{#if nextPreview}<span class="italic">{nextPreview}…</span>{/if}
							</span>
						</a>
					{:else if nextInSeries}
						<!-- The end of a volume is where a series loses its reader: point at the
						     next one (in this language — the API skips a volume not translated
						     yet) instead of back at the contents of a book just finished. To its
						     page, not its first chapter: a devotional opens with an introduction
						     and a reader deciding to go on wants to see what they are starting. -->
						<a
							href={localizeHref(`/books/${nextInSeries.slug}`)}
							class="btn btn-primary flex-1 flex-col items-end gap-0.5 text-end"
							class:celebrate
							aria-label="{t('book.seriesNext')}: {nextInSeries.title}"
						>
							<span class="eyebrow opacity-75">{t('book.seriesNext')}</span>
							<span class="text-small" dir="auto">{nextInSeries.title}</span>
						</a>
					{:else}
						<a href={localizeHref(`/books/${slug}`)} class="btn btn-ghost flex-1 text-center" class:celebrate>{t('reader.backToContents')}</a>
					{/if}
				</nav>
				<!-- A way to the contents whenever the button above points somewhere else:
				     mid-book, and at the end of a volume that has a next one. -->
				{#if chapter.next || nextInSeries}
					<p class="mt-3 text-center">
						<a href={localizeHref(`/books/${slug}`)} class="text-small text-muted hover:text-text">{t('reader.contents')}</a>
					</p>
				{/if}
				<!-- Colophon: a crawlable link out to the book and its author from every
				     chapter — the site's largest page type, which otherwise linked only to
				     its own contents and the next chapter (a dead end for the author graph).
				     A middot, not a localized "by", so no message-catalogue key is needed. -->
				<p class="mt-8 text-center text-small text-muted">
					<a href={localizeHref(`/books/${slug}`)} class="hover:text-text">{chapter.book_title}</a>
					<span aria-hidden="true"> · </span>
					<a href={localizeHref(authorPath(chapter.author_slug))} class="hover:text-text"
						>{chapter.author_name}</a
					>
				</p>
			</div>
		</div>
	</div>
</article>

<!-- Kindle-style edge page-turn arrows (page mode only). The outer screen edge
     is already an invisible tap zone; these are the visible affordance for
     pointer users, and roll over to the adjacent chapter at a chapter's ends. -->
{#if paged}
	<button
		class="pageturn left"
		onclick={() => turnPage(contentRtl ? 1 : -1)}
		aria-label={contentRtl ? t('reader.next') : t('reader.previous')}
		title={contentRtl ? t('reader.next') : t('reader.previous')}
	>
		<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
	</button>
	<button
		class="pageturn right"
		onclick={() => turnPage(contentRtl ? -1 : 1)}
		aria-label={contentRtl ? t('reader.previous') : t('reader.next')}
		title={contentRtl ? t('reader.previous') : t('reader.next')}
	>
		<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
	</button>
{/if}

<!-- A hairline of progress along the top. It began as focus mode's stand-in
     for the hidden scrubber; it now stays on in scroll mode too, so a glance
     tells you where you are without looking down at the footer. Page mode
     keeps it to focus only — the fixed chrome bar sits where it would go, and
     "Page 3 / 9" already says it. -->
{#if readerUi.focus || !paged}
	<div class="read-progress" style="transform: scaleX({chapterFrac})" aria-hidden="true"></div>
{/if}

<!-- Focus mode hides the footer, and with it the scrubber's aria-valuetext —
     so announce the page here instead (only there: elsewhere it would be said
     twice). The text re-renders only when currentPage does, so a screen reader
     hears "Page 4 / 9", not every pixel. -->
{#if readerUi.focus}
	<div class="sr-only" role="status" aria-live="polite">
		{t('progress.page')} {currentPage} / {pageCount}
	</div>
{/if}

<!-- Offered after a deep-link jump (bookmark, search hit, note): the spot the
     reader left, which the jump would otherwise have thrown away. -->
{#if returnTo}
	<button class="return-pill" onclick={goBackToPrior}>
		<Icon name="chevron-left" size={14} />
		{t('reader.returnPrior')}
	</button>
{:else if syncOffer}
	<!-- The account is further along than this device (another device read on).
	     Same slot as the return pill; the two never coincide — a deliberate jump
	     skips the sync ask — but the pill wins if they somehow did. -->
	<div class="return-pill sync-pill" role="status">
		<span>{t('reader.syncedAhead')}</span>
		<button class="sync-cta" onclick={takeSyncOffer}>
			{#if syncOffer.order !== chapter.order}
				{t('book.continueCh')} {syncOffer.order}
			{:else}
				{t('reader.continueThere')}
			{/if}
		</button>
		<button class="sync-dismiss" onclick={dismissSyncOffer} aria-label={t('pwa.dismiss')}>
			<Icon name="close" size={14} />
		</button>
	</div>
{/if}

<!-- Reading-progress footer: a draggable scrubber + location, fixed, hidden in
     focus/Listen modes. -->
{#if !readerUi.focus && listen.status === 'idle'}
	<div bind:this={footEl} class="progress-foot">
		<!-- Scroll mode: the footer is a translucent bar the text scrolls under, so
		     a line landing at its hard top edge is sliced into unreadable letter-tops.
		     This scrim fades the last line into the bar instead of chopping it. Page
		     mode clips at the column edge by design, so it is excluded. -->
		{#if !paged}
			<div class="foot-fade" aria-hidden="true"></div>
		{/if}
		<input
			class="scrubber"
			type="range"
			min="0"
			max="1"
			step="0.005"
			value={chapterFrac}
			oninput={(e) => {
				const frac = Number(e.currentTarget.value);
				if (paged) {
					breakPace(); // a seek: goToPage samples, and this pair must not count
					goToPage(Math.round(frac * (pageTotal - 1)));
				} else scrubTo(frac);
			}}
			aria-label={t('progress.scrub')}
			aria-valuetext="{t('progress.page')} {currentPage} / {pageCount}"
		/>
		<div class="progress-meta">
			<span>{t('progress.page')} {currentPage} / {pageCount}</span>
			<span class="mx-1.5 opacity-50">·</span>
			<span>
				{minsLeft}
				{t('progress.minLeft')}{#if readingPace.personalized}<span class="hidden sm:inline"
						><span class="mx-1.5 opacity-50">·</span>{t('progress.yourPace')}</span
					>{/if}
			</span>
			{#if bookPercent !== null}
				<span class="mx-1.5 opacity-50">·</span>
				<span>{bookPercent}% {t('progress.through')}</span>
			{/if}
			{#if bookTimeLeftLabel}
				<!-- Whole-book time, hidden on the narrowest screens (like "your
				     pace") so the phone footer stays a single tidy line. -->
				<span class="hidden sm:inline"
					><span class="mx-1.5 opacity-50">·</span>{bookTimeLeftLabel}</span
				>
			{/if}
		</div>
		<!-- Phone action row, in thumb reach. Folds away with the top bar while
		     reading on (hideChrome: scroll mode only) and returns with it. -->
		<div class="foot-actions" class:folded={hideChrome}>
			{#if chapter.prev}
				<a href={chapterHref(chapter.prev.order)} class="foot-btn"
					><Icon name="chevron-left" size={22} class="dir-flip" /><span>{t('reader.previous')}</span></a
				>
			{:else}
				<span class="foot-btn" aria-hidden="true"></span>
			{/if}
			{#if listen.supported}
				<button
					class="foot-btn"
					onclick={() => reader.startListening()}
					title="{t('reader.listen')} · {listenTime(chapter.word_count, listen.rate)}"
					><Icon name="headphones" size={22} /><span>{t('reader.listen')}</span></button
				>
			{/if}
			<button
				class="foot-btn"
				onclick={() => (readerUi.panelOpen = true)}
				aria-haspopup="dialog"
				aria-expanded={readerUi.panelOpen}
				aria-label={t('reader.textSettings')}
				title={t('reader.textSettings')}><span class="foot-aa" aria-hidden="true">Aa</span></button
			>
			{#if chapter.next}
				<a href={chapterHref(chapter.next.order)} class="foot-btn foot-next"
					><Icon name="chevron-right" size={22} class="dir-flip" /><span>{t('reader.next')}</span></a
				>
			{:else}
				<span class="foot-btn" aria-hidden="true"></span>
			{/if}
		</div>
	</div>
{/if}

<!-- The phone text-settings sheet. Out here, not in the top bar: the bar's
     backdrop-filter would make it the containing block for this fixed sheet. -->
{#if isPhone}
	<ReaderControls sheet layout margins {...rcProps} />
{/if}

<!-- Outside the <article>: in page-turn mode it carries a translateX, and a
     fixed-position overlay inside a transformed ancestor is laid out against
     that ancestor — every one of these would slide with the page turn. -->
<ReaderOverlays {reader} container={body} {language} />

<TocDrawer {slug} currentOrder={chapter.order} {edition} bind:open={tocOpen} />

<SearchDrawer {slug} bind:open={searchOpen} />

<NotesDrawer {slug} {edition} bind:open={notesOpen} />

<style>
	/* --- Page-turn mode --------------------------------------------------------
	   The pager is transparent (display:contents) in scroll mode; in page mode
	   the <article> becomes a fixed, measure-capped viewport and the pager its
	   CSS-column content, turned a page at a time via translateX. Each page is
	   one full-width column; the gap between columns is twice the side gutter so
	   the next column parks fully off-screen (no sliver in the gutter). */
	.pager {
		display: contents;
	}
	article.paged {
		position: fixed;
		/* --pgtop is the chrome's measured height; the nav sits above that again
		   (see the bar's comment). Both are viewport-relative because this is
		   `fixed`, so they add. */
		top: calc(var(--appnav-h, 0px) + var(--pgtop, 3.4rem));
		bottom: var(--pgbot, 3.1rem);
		inset-inline: 0;
		z-index: 5;
		margin-inline: auto;
		padding: 0 !important;
		/* clip, not hidden: a hidden box is still a scroll container, and the
		   browser scrolled it to reveal a focused link on another page — shifting
		   the columns under the translate. */
		overflow: hidden;
		overflow: clip;
		background: var(--bg);
	}
	article.paged.focus {
		top: 0;
		bottom: 0;
	}
	/* Sits below the columns (z 5) and the edge arrows (z 6), above the page, so
	   the whole reading surface is one uniform shade. */
	/* Page mode only: `sticky` already sits below the nav in flow. */
	.reader-chrome.fixed {
		top: var(--appnav-h, 0px);
	}
	/* A peek in focus mode floats at the very top over the reading surface,
	   regardless of where the (possibly hidden) global nav sits, and slides in. */
	.reader-chrome.peeking {
		top: 0;
		z-index: 40;
		animation: chrome-peek var(--duration-base) ease;
	}
	@keyframes chrome-peek {
		from {
			transform: translateY(-100%);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.reader-chrome.peeking {
			animation: none;
		}
	}
	/* Auto-hide on scroll-down (scroll mode). The sticky bar slides up off-screen
	   and back; only a transform, so nothing reflows and the prose stays put. The
	   bottom progress bar and the top hairline are left pinned. (The global
	   reduced-motion block near the top of app.css snaps the transition.) */
	.reader-chrome {
		transition: transform var(--duration-base) ease;
	}
	.reader-chrome.autohidden {
		transform: translateY(-100%);
	}
	/* Touch: give the chrome's icon buttons a full-height tap target (≥44px on
	   the axis that fits — nine controls can't also be 44px WIDE on a 360px
	   phone without moving some off the bar, a larger redesign left for later). */
	@media (pointer: coarse) {
		.reader-chrome :global(.btn-icon) {
			min-height: 44px;
		}
	}
	.paged-backdrop {
		position: fixed;
		inset: 0;
		z-index: 4;
		background: var(--bg);
	}
	/* Hide what sits outside the pager — today only the breadcrumb — in page
	   mode: only the pager's content is paginated. Screen only: on paper the
	   title and breadcrumb are the first thing you want, not the first thing to
	   blank.

	   :global because the breadcrumb is a child component, and a scoped
	   `:not(.pager)` only matches elements carrying THIS component's class. It
	   never hid the breadcrumb, which then pushed the full-height pager down by
	   its own height and ate the line of slack reserved at the foot of every
	   page (see the padding note below). */
	@media screen {
		article.paged > :global(:not(.pager)) {
			display: none;
		}
	}
	/* The chapter's ending opens a fresh column, so in a single-column layout
	   it is a page of its own and in a two-column spread it takes the facing
	   column when there is one. Each block keeps whole: a Next-chapter button
	   split across a page turn is two half-buttons. */
	.paged .chapter-end {
		break-before: column;
	}
	.paged .chapter-end > :global(*) {
		break-inside: avoid;
	}
	/* Scroll mode spaces these blocks to set the ending apart from the prose
	   above it; a page of its own needs no such gap, and at that spacing the
	   last two lines (contents link, colophon) spilled onto a page of their
	   own. The first block needs no rule either — it opens the page. */
	.paged .chapter-end > :global(* + *) {
		margin-top: 1.5rem;
	}
	.paged .end-nav > :first-child {
		margin-top: 0;
	}
	.paged .chapter-end > :global(:first-child) {
		margin-top: 0;
		border-top: 0;
		padding-top: 0;
	}
	.paged .pager {
		--pgpad: 1.25rem;
		--cols: 1;
		display: block;
		height: 100%;
		max-width: none;
		box-sizing: border-box;
		/* The bottom padding is a full line of slack, not a cosmetic gap. With
		   `column-fill: auto` the browser starts the last line of a column if its
		   TOP fits, then lets its bottom spill past the content box — and
		   `article.paged`'s `overflow: hidden` sliced that spill into unreadable
		   letter-tops at the foot of every page. Reserving one prose line-height
		   below the fill area keeps that spilled line whole (it lands in the padding,
		   which the clip does not reach) or reflows it to the next page. The value is
		   the reading line-height itself — `1.18rem` base size (see app.css `.reading`)
		   × the reader's Size (`--reading-scale`) × Spacing (`--reading-leading`) —
		   so the slack tracks the text at every setting, plus a small margin. */
		padding: 0.85rem var(--pgpad)
			calc(1.18rem * var(--reading-scale, 1) * var(--reading-leading, 1.85) + 0.4rem);
		/* Each page window (width --page-w) holds --cols columns. With the gap set
		   to twice the side padding, the columns land flush inside the page and the
		   inter-page gutter parks the next column fully off-screen (no sliver). This
		   one formula yields a single column when --cols is 1 and a Kindle-style
		   two-column spread when it's 2. */
		column-width: calc(var(--page-w) / var(--cols) - 2 * var(--pgpad));
		column-gap: calc(2 * var(--pgpad));
		column-fill: auto;
		/* --page-dir is 1 (LTR) or -1 (RTL): RTL pages advance rightwards. --drag is
		   the live touch offset (physical px, added straight so it follows the
		   finger in either direction); it's 0 except mid-swipe. */
		transform: translateX(
			calc(var(--page-dir, 1) * -1 * var(--page-idx) * var(--page-w) + var(--drag, 0px))
		);
		/* A softer glide than a flat `ease`: a longer ease-out curve so the page
		   arrives gently instead of snapping, closer to an e-reader's turn. The
		   faint opacity fade on each turn is played imperatively (see playTurnFade)
		   so it fires only on a discrete turn, never while scrubbing. */
		transition: transform 300ms cubic-bezier(0.22, 0.61, 0.36, 1);
	}
	/* While the finger is down the page tracks it 1:1 — no easing to lag behind. */
	.paged .pager.dragging {
		transition: none;
	}
	/* A touch more breathing room around a two-column spread. */
	.paged.twocol .pager {
		--pgpad: 2rem;
	}
	@media (prefers-reduced-motion: reduce) {
		.paged .pager {
			transition: none;
		}
	}

	/* Paged mode is a fixed, column-swept viewport with the page offset applied
	   as a translate on .pager — so printing it produced whichever single
	   screenful was showing, shifted off the sheet by however many pages the
	   reader had turned. Unwind the whole mechanism back to normal flow. */
	@media print {
		article.paged {
			position: static !important;
			inset: auto !important;
			overflow: visible !important;
			background: none !important;
			z-index: auto !important;
		}
		.paged .pager {
			display: block !important;
			height: auto !important;
			padding: 0 !important;
			column-width: auto !important;
			column-gap: normal !important;
			columns: auto !important;
			transform: none !important;
			transition: none !important;
		}
	}

	/* Large, unobtrusive edge page-turn buttons — the visible twin of the outer
	   tap zones, vertically centred like a Kindle spread. */
	.pageturn {
		position: fixed;
		top: 50%;
		transform: translateY(-50%);
		z-index: 6;
		display: grid;
		place-items: center;
		width: 3rem;
		height: 3rem;
		border-radius: 9999px;
		border: 1px solid var(--border);
		color: var(--muted);
		background: color-mix(in srgb, var(--bg) 70%, transparent);
		backdrop-filter: blur(4px);
		opacity: 0.55;
		transition:
			opacity 0.15s ease,
			color 0.15s ease,
			border-color 0.15s ease;
	}
	.pageturn:hover {
		opacity: 1;
		color: var(--text);
		border-color: var(--accent);
	}
	/* Park each arrow just outside the (centred) reading column. The offset keys
	   off the REAL column width (--reader-col-w, measured and published from the
	   reader's chosen measure) rather than a fixed guess, so a wide measure no
	   longer runs the text under the arrow; max() keeps it on-screen, and the cap
	   below reserves the lane it sits in. Touch screens hide the arrows (below). */
	/* Physical on purpose: these two are a mirrored PAIR of screen-edge arrows,
	   and which one means "next" already flips on `contentRtl` in the markup.
	   Making the positions logical would move both to the same edge. */
	.pageturn.left {
		left: max(0.5rem, calc((100vw - var(--reader-col-w, 88rem)) / 2 - 3.5rem)); /* rtl-ok: mirrored pair, direction handled in markup */
	}
	.pageturn.right {
		right: max(0.5rem, calc((100vw - var(--reader-col-w, 88rem)) / 2 - 3.5rem)); /* rtl-ok: mirrored pair, direction handled in markup */
	}
	/* On pointer devices (where the arrows show) hold a margin lane open on each
	   side, so however wide the reader's measure, the column stops short of the
	   arrows — the Kindle look, with clear margins and the arrows off the text.
	   --article-max lives on the <article>, where its `var(--reading-measure)`
	   resolves; the cap only ever narrows it, never widens a measure the reader
	   picked. `article.paged` outweighs the base `.reading-article` max-width by
	   specificity, so no !important is needed. */
	@media (not (pointer: coarse)) {
		article.paged {
			max-width: min(var(--article-max), calc(100vw - 9rem));
		}
	}
	/* On touch screens the tap zones suffice; keep the edges clean. */
	@media (pointer: coarse) {
		.pageturn {
			display: none;
		}
	}

	/* Finishing a chapter: one gentle pulse of the onward button so the arrival
	   registers. Set only when the chapter is completed (and never under
	   prefers-reduced-motion — the flag isn't set there). */
	.celebrate {
		animation: chapter-done 1.1s ease;
	}
	@keyframes chapter-done {
		30% {
			transform: scale(1.035);
			border-color: var(--accent);
		}
	}

	/* Room for the fixed progress bar (and the home-indicator strip beneath it),
	   so the chapter's last line and its "Next chapter" CTA are not underneath
	   the scrubber. */
	.reading-article {
		/* The article's width comes from --article-max (set inline: the reader's
		   measure, or the two-column spread). Owning it in CSS rather than an inline
		   max-width lets the pointer-device cap below win by specificity — no
		   !important. In scroll mode --article-max resolves to the plain measure.
		   The fallback keeps the column bounded if --article-max is ever absent
		   rather than letting it render full-bleed. */
		max-width: var(--article-max, var(--reading-measure));
		/* Side gutters come from the reader's Margins pref (readerPrefs emits
		   --reading-margin on this element); page mode zeroes padding and keeps
		   its own --pgpad, so this is scroll mode only. */
		padding-inline: var(--reading-margin, 1.25rem);
		/* Clear the fixed progress footer by its measured height (--foot-h, set
		   from a ResizeObserver) — it changes with the touch scrubber, the phone
		   action row. In Listen mode there is no footer, so clear the ListenBar
		   (--listenbar-h); the last fallback is the desktop footer before the
		   first measurement. */
		padding-bottom: calc(
			var(--foot-h, var(--listenbar-h, calc(3.1rem + env(safe-area-inset-bottom)))) + 1.4rem
		);
	}
	/* Scroll mode only: give the chapter title cluster room to breathe under the
	   breadcrumb, so it reads as the start of the chapter rather than a fourth
	   header line. Page mode zeroes the article padding and paginates from the
	   top, so the kicker stays flush there. */
	article:not(.paged) .chapter-kicker {
		margin-top: 2.5rem;
	}
	.progress-foot {
		position: fixed;
		inset-inline: 0;
		bottom: 0;
		z-index: 30;
		/* The extra bottom padding clears the iPhone home-indicator strip, which
		   this bar sat inside. env() is 0 everywhere it doesn't apply. */
		padding: 0.25rem 1rem calc(0.4rem + env(safe-area-inset-bottom));
		text-align: center;
		font-size: var(--fs-micro);
		color: var(--muted);
		background: color-mix(in srgb, var(--bg) 82%, transparent);
		backdrop-filter: blur(6px);
	}
	/* A short fade above the bar so a line of body text scrolling under it
	   dissolves into the page instead of being sliced at the bar's hard top edge.
	   Anchored to the footer's top (bottom: 100%), so it tracks the bar's measured
	   height. Scroll mode only (rendered under {#if !paged}). */
	.foot-fade {
		position: absolute;
		inset-inline: 0;
		bottom: 100%;
		height: 2.25rem;
		background: linear-gradient(to top, var(--bg), transparent);
		pointer-events: none;
	}
	.progress-meta {
		margin-top: 0.1rem;
	}
	.scrubber {
		display: block;
		width: min(42rem, 100%);
		max-width: 100%;
		margin: 0 auto;
		height: 1.1rem;
		cursor: pointer;
		accent-color: var(--accent);
		background: transparent;
	}
	/* Touch: a range input's whole height is its hit area, so growing it gives
	   the thumb a ≥44px target without restyling the native thumb (which
	   `accent-color` would lose under `appearance: none`). */
	@media (pointer: coarse) {
		.scrubber {
			height: 2.75rem;
		}
	}

	/* --- Phone chrome (below `sm`) -------------------------------------------- */
	/* The "⋯" group: `.account-menu` chrome, with icon rows at thumb size. */
	.more-group {
		top: calc(100% + 0.25rem);
	}
	.more-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		min-height: 2.75rem;
		font-size: var(--fs-body);
	}
	.more-item.text-accent {
		color: var(--accent);
	}
	/* Previous · Listen · Aa · Next. Phones only — via the media query, not a
	   `sm:hidden` utility, which a scoped `display` here would out-rank. */
	.foot-actions {
		display: none;
		margin-top: 0.15rem;
	}
	@media (max-width: 639.98px) {
		.foot-actions {
			display: flex;
		}
		.foot-actions.folded {
			display: none;
		}
	}
	.foot-btn {
		flex: 1 1 0;
		min-height: 2.9rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.1rem;
		border-radius: var(--radius-sm);
		font-size: var(--fs-small);
		font-weight: 600;
		color: var(--text);
	}
	.foot-next {
		color: var(--accent);
	}
	.foot-aa {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		line-height: 1;
	}
	/* Reserve the "Next" card's meta line before its content arrives. */
	.up-next-meta {
		min-height: 1.4em;
	}

	/* "Back to where you were" — a small pill parked above the progress footer,
	   centred, that a deep-link jump leaves behind for a few seconds. */
	.return-pill {
		position: fixed;
		inset-inline: 0;
		bottom: calc(var(--foot-h, calc(3.1rem + env(safe-area-inset-bottom))) + 0.5rem);
		z-index: 31;
		margin-inline: auto;
		width: max-content;
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding-block: 0.45rem;
		padding-inline: 0.7rem 0.9rem; /* tighter on the icon side, whichever side that is */
		border-radius: 9999px;
		border: 1px solid var(--border);
		background: color-mix(in srgb, var(--surface) 92%, transparent);
		color: var(--text);
		font-size: var(--fs-small);
		box-shadow: var(--shadow-popover);
		backdrop-filter: blur(6px);
		animation: return-in var(--duration-base) ease;
	}
	.return-pill:not(.sync-pill):hover {
		border-color: var(--accent);
	}
	/* The synced-position offer wears the pill's chrome with two actions inside. */
	.sync-pill {
		gap: 0.6rem;
		padding-inline: 0.9rem 0.4rem;
		max-width: calc(100vw - 2rem);
	}
	.sync-cta {
		white-space: nowrap;
		border-radius: 999px;
		background: var(--accent);
		color: var(--accent-contrast);
		padding: 0.25rem 0.75rem;
		font-weight: 600;
		font-size: var(--fs-small);
	}
	.sync-cta:hover {
		filter: brightness(1.05);
	}
	.sync-dismiss {
		display: inline-flex;
		padding: 0.55rem; /* ~32px beside the CTA: a thumb target, not a mouse one */
		border-radius: 999px;
		color: var(--muted);
	}
	.sync-dismiss:hover {
		color: var(--text);
		background: var(--surface-2);
	}
	/* "Back" points the other way in Arabic. */
	:global([dir='rtl']) .return-pill :global(svg) {
		transform: scaleX(-1);
	}
	@keyframes return-in {
		from {
			opacity: 0;
			transform: translateY(6px);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.return-pill {
			animation: none;
		}
	}

	/* Text-range marks (<mark> spans) are styled globally in app.css. */
	/* Paragraph currently being read aloud in Listen mode. */
	:global(.reading > .tts-current) {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
		border-radius: 4px;
		box-shadow: 0 0 0 6px color-mix(in srgb, var(--accent) 10%, transparent);
		transition: background var(--duration-base) ease;
	}
</style>
