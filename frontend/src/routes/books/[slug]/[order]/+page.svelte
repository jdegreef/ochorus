<script lang="ts">
	import { onMount, tick, untrack } from 'svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { goto, invalidateAll } from '$app/navigation';
	import { getBook, getPlan, type BookDetail, type Chapter, type PlanDetail } from '$lib/library';
	import { planProgress } from '$lib/planProgress.svelte';
	import {
		saveProgress,
		getScrollAnchor,
		saveScrollAnchor,
		getProgressRecord
	} from '$lib/progress';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { marks } from '$lib/marks.svelte';
	import { bookmarks } from '$lib/bookmarks.svelte';
	import { renderMarks } from '$lib/rangeMarks';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { readingTime, readingMinutes } from '$lib/reading';
	import { listen } from '$lib/listen.svelte';
	import { define } from '$lib/define.svelte';
	import { scripture } from '$lib/scripture.svelte';
	import { API_BASE_URL, SITE_URL } from '$lib/config';
	import { jsonLd } from '$lib/seo';
	import { localizeHref, locales } from '$lib/paraglide/runtime';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import DefinePopover from '$lib/components/DefinePopover.svelte';
	import ScripturePopover from '$lib/components/ScripturePopover.svelte';
	import TocDrawer from '$lib/components/TocDrawer.svelte';
	import SearchDrawer from '$lib/components/SearchDrawer.svelte';
	import SelectionBar from '$lib/components/SelectionBar.svelte';
	import ListenBar from '$lib/components/ListenBar.svelte';

	let { data } = $props();
	const chapter = $derived(data.chapter as Chapter);
	const slug = $derived(data.slug as string);
	// 'modern' when reading the Modern English edition, else null. Carried in the
	// URL and preserved across every in-reader chapter link.
	const edition = $derived((data.edition as 'modern' | null) ?? null);
	const t = i18n.t;

	// --- SEO head (this page prerenders — see +page.ts) -------------------------
	// Self-referential canonical + hreflang, same convention as books/[slug].
	const seoPath = $derived(`/books/${slug}/${chapter.order}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(seoPath)}`);
	const seoAlternates = $derived(
		locales.map((loc) => ({ loc, href: `${SITE_URL}${localizeHref(seoPath, { locale: loc })}` }))
	);
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
			.replace(/\s+/g, ' ')
			.trim()
			.slice(0, 250)
	);
	const chapterLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Chapter',
			name: chapter.title,
			position: chapter.order,
			isPartOf: {
				'@type': 'Book',
				name: chapter.book_title,
				author: { '@type': 'Person', name: chapter.author_name },
				url: `${SITE_URL}${localizeHref(`/books/${slug}/`)}`
			},
			url: canonical,
			isAccessibleForFree: true,
			inLanguage: getLang()
		})
	);

	let body: HTMLDivElement | undefined = $state();
	let titleEl: HTMLHeadingElement | undefined = $state();
	let titleVisible = $state(true);

	// The prerendered HTML is always the standard edition (query params don't
	// exist at build time — see +page.ts). A direct visit to ?edition=modern
	// hydrates with that standard-edition data, so re-run load client-side once
	// to fetch the Modern English chapter.
	onMount(() => {
		const wantsModern = new URLSearchParams(location.search).get('edition') === 'modern';
		if (wantsModern && edition !== 'modern') invalidateAll();
	});

	// Note editor state — edits the note of an existing mark group, or creates
	// a new mark from pending selection segments when noteId is null.
	let noteOpen = $state(false);
	let noteId = $state<string | null>(null);
	let notePending = $state<{ p: number; s: number; e: number }[]>([]);
	let noteDraft = $state('');

	const HEADER_OFFSET = 72;
	let tocOpen = $state(false);
	let searchOpen = $state(false);

	// --- Reading-progress indicators -------------------------------------------
	// Fraction of the current chapter scrolled past (0..1), updated by the same
	// throttled scroll handler that saves the position anchor.
	let chapterFrac = $state(0);
	let bookForProgress = $state<BookDetail | null>(null);

	// Reset the scroll fraction when the CHAPTER changes — a fresh chapter opens
	// at the top until the per-chapter effect below restores the saved position.
	// This is deliberately separate from the book fetch: the old combined effect
	// also read `bookForProgress`, so that fetch's async write re-ran the effect
	// and snapped `chapterFrac` back to 0 *after* the position had been restored,
	// jumping the progress footer/scrubber to page 1.
	$effect(() => {
		void slug;
		void chapter.order;
		chapterFrac = 0;
	});

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
				if (!cancelled) bookForProgress = b;
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
		const p = topVisibleIndex();
		const el = body.children[p] as HTMLElement | undefined;
		const snippet = (el?.innerText ?? '').trim().replace(/\s+/g, ' ').slice(0, 90);
		bookmarks.toggle(chapter.order, p, snippet, chapter.title);
		topIndex = p;
	}

	const minutesLeft = $derived(
		Math.ceil(readingMinutes(chapter.word_count) * (1 - chapterFrac))
	);
	const bookPercent = $derived.by(() => {
		const b = bookForProgress;
		if (!b || b.slug !== slug || !b.chapters.length) return null;
		const totalWords = b.chapters.reduce((sum, c) => sum + c.word_count, 0);
		if (!totalWords) return null;
		const before = b.chapters
			.filter((c) => c.order < chapter.order)
			.reduce((sum, c) => sum + c.word_count, 0);
		return Math.min(
			100,
			Math.round(((before + chapter.word_count * chapterFrac) / totalWords) * 100)
		);
	});

	// --- Page-turn mode --------------------------------------------------------
	// An opt-in e-reader layout (readerPrefs.paged): the chapter body is laid out
	// in full-width CSS columns inside a fixed viewport and turned one page at a
	// time with a translateX, instead of scrolling. Only active while not
	// listening — Listen mode keeps the scrolling layout it was built against.
	let articleEl = $state<HTMLElement>();
	let pager = $state<HTMLElement>();
	let chromeEl = $state<HTMLElement>();
	let footEl = $state<HTMLElement>();
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

	// A Kindle-style page count. In page-turn mode it's the real column count; in
	// scroll mode it's estimated from word count and the current scroll position.
	const WORDS_PER_PAGE = 280;
	const pageCount = $derived(
		paged ? pageTotal : Math.max(1, Math.ceil(chapter.word_count / WORDS_PER_PAGE))
	);
	const currentPage = $derived(
		paged
			? pageIndex + 1
			: Math.min(pageCount, Math.max(1, Math.round(chapterFrac * pageCount) || 1))
	);

	/** Scroll to a fraction of the chapter — drives the draggable scrubber. */
	function scrubTo(frac: number) {
		if (!body) return;
		const rect = body.getBoundingClientRect();
		const bodyTop = window.scrollY + rect.top;
		window.scrollTo({ top: Math.max(0, bodyTop - window.innerHeight + frac * rect.height) });
	}

	/** Which page a body child (paragraph) sits on — transform-independent. */
	function pageOf(el: HTMLElement): number {
		return pageW > 0 ? Math.max(0, Math.floor(el.offsetLeft / pageW)) : 0;
	}
	/** Index of the first paragraph laid out on a given page (top-left of it). */
	function firstIndexOnPage(p: number): number {
		if (!body) return 0;
		const kids = body.children;
		let best = -1;
		let bestTop = Infinity;
		for (let i = 0; i < kids.length; i++) {
			const el = kids[i] as HTMLElement;
			if (pageOf(el) === p && el.offsetTop < bestTop) {
				bestTop = el.offsetTop;
				best = i;
			}
		}
		return best < 0 ? 0 : best;
	}

	/** Re-measure the page width and count from the current layout. */
	function measurePages() {
		if (!paged || !articleEl || !pager) return;
		applyInsets();
		const w = articleEl.clientWidth;
		pageW = w;
		// Apply the column width + count imperatively so the scrollWidth read below
		// reflows against them synchronously (Svelte's reactive style flush is async).
		pager.style.setProperty('--page-w', `${w}px`);
		pager.style.setProperty('--cols', `${cols}`);
		// Pages are `pageW`-wide windows over the column flow. ceil (with a small
		// epsilon to absorb sub-pixel over-report) counts a trailing partial page —
		// needed for a two-column spread whose last page may hold a single column.
		pageTotal = w > 0 ? Math.max(1, Math.ceil(pager.scrollWidth / w - 0.02)) : 1;
		if (pageIndex > pageTotal - 1) pageIndex = pageTotal - 1;
	}

	/** Turn to page p, persisting the paragraph now at the top of the page. */
	function goToPage(p: number, save = true) {
		pageIndex = Math.min(pageTotal - 1, Math.max(0, p));
		chapterFrac = pageTotal > 1 ? pageIndex / (pageTotal - 1) : 1;
		if (save) {
			topIndex = firstIndexOnPage(pageIndex);
			saveScrollAnchor(slug, chapter.order, topIndex);
		}
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
		}
	}

	onMount(() => {
		readerPrefs.init();
		listen.init();
	});

	// Per-chapter setup: progress, marks, restore scroll, observe title.
	$effect(() => {
		const s = slug;
		const order = chapter.order;
		const language = getLang();

		// Arriving from a bookmark / notebook deep-link (?p=N): seed the scroll
		// anchor to N *before* saveProgress reads it, so the book's resume point
		// records paragraph N. Without this, saveProgress ran with no anchor yet
		// and stored paragraph 0 — leaving the chapter before scrolling threw the
		// bookmarked spot away.
		const pParam = $page.url.searchParams.get('p');
		const jumpTo = pParam !== null ? Number(pParam) : NaN;
		if (Number.isFinite(jumpTo) && jumpTo > 0) saveScrollAnchor(s, order, jumpTo);

		saveProgress(s, order, language);
		marks.load(s, order, language);
		bookmarks.load(s);

		// A backward chapter turn in page mode asks to land on the last page.
		const wantLast = $page.url.searchParams.get('pg') === 'last';

		let cleanup: (() => void) | undefined;
		(async () => {
			await tick();
			if (paged) {
				measurePages();
				let target = 0;
				if (wantLast) target = pageTotal - 1;
				else if (Number.isFinite(jumpTo) && body?.children[jumpTo]) {
					target = pageOf(body.children[jumpTo] as HTMLElement);
				} else {
					const rec = getProgressRecord(s);
					const idx =
						getScrollAnchor(s, order) ??
						(rec && rec.order === order ? rec.paragraph_index : null);
					if (idx && body?.children[idx]) target = pageOf(body.children[idx] as HTMLElement);
				}
				goToPage(target, false);
			} else if (Number.isFinite(jumpTo) && body?.children[jumpTo]) {
				body.children[jumpTo].scrollIntoView({ block: 'start' });
				window.scrollBy(0, -HEADER_OFFSET);
			} else {
				restoreScroll(s, order);
			}
			if (!paged) updateFraction();
			cleanup = observeTitle();
		})();
		return () => cleanup?.();
	});

	// Re-measure the page count when the layout changes under us — text prefs,
	// freshly rendered marks — so the "Page X / Y" total and the scrubber stay
	// honest. Initial positioning is owned by the per-chapter effect above; this
	// only re-counts and clamps, so it never fights that effect.
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
			})();
		});
	});

	// Keep the count correct — and the one/two-column choice current — across
	// viewport resizes / orientation changes.
	$effect(() => {
		if (!browser) return;
		const onResize = () => {
			viewportW = window.innerWidth;
			if (paged) untrack(() => measurePages());
		};
		window.addEventListener('resize', onResize);
		return () => window.removeEventListener('resize', onResize);
	});

	// A first-sign-in sync can replace the local cache underneath us — re-read the
	// current chapter's marks so freshly-pulled highlights/notes appear.
	onMount(() => {
		const onSync = () => marks.refresh();
		window.addEventListener('ochorus:sync', onSync);
		return () => window.removeEventListener('ochorus:sync', onSync);
	});

	// Listen mode: stop speech when the chapter changes or the reader unmounts.
	$effect(() => {
		void slug;
		void chapter.order;
		return () => listen.stop();
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

	/** Keyboard: ←/→ chapters (or paragraph skip while listening), space pages. */
	function onKeydown(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		const el = e.target as HTMLElement;
		if (
			el?.closest?.('input, textarea, select, [contenteditable="true"]') ||
			noteOpen ||
			define.open ||
			tocOpen ||
			searchOpen
		) {
			return;
		}
		if (e.key === 'ArrowRight') {
			e.preventDefault();
			if (listen.status !== 'idle') listen.skip(1);
			else if (paged) turnPage(1);
			else gotoChapter(chapter.next);
		} else if (e.key === 'ArrowLeft') {
			e.preventDefault();
			if (listen.status !== 'idle') listen.skip(-1);
			else if (paged) turnPage(-1);
			else gotoChapter(chapter.prev);
		} else if (e.key === ' ') {
			e.preventDefault();
			if (paged) turnPage(e.shiftKey ? -1 : 1);
			else
				window.scrollBy({
					top: (e.shiftKey ? -1 : 1) * window.innerHeight * 0.85,
					behavior: 'smooth'
				});
		}
	}

	/** Tap a server-wrapped Bible reference → open the scripture popover. */
	function tryScriptureClick(e: MouseEvent): boolean {
		const a = (e.target as HTMLElement).closest?.('a.scripture-ref') as HTMLElement | null;
		if (!a?.dataset.ref) return false;
		e.preventDefault();
		const r = a.getBoundingClientRect();
		scripture.show(a.dataset.ref, r.bottom + window.scrollY, r.left + window.scrollX + r.width / 2);
		return true;
	}

	/** Edge tap zones: outer 15% turns the page (paged) or chapter (scroll, touch). */
	function onArticleClick(e: MouseEvent) {
		if (tryScriptureClick(e)) return;
		if (!paged && !window.matchMedia('(pointer: coarse)').matches) return;
		const el = e.target as HTMLElement;
		if (el.closest('a, button, mark, input, textarea, select, .selbar, .define-pop, .scripture-pop')) return;
		if (window.getSelection()?.toString()) return;
		const x = e.clientX / window.innerWidth;
		if (paged) {
			if (x < 0.15) turnPage(-1);
			else if (x > 0.85) turnPage(1);
		} else if (x < 0.15) gotoChapter(chapter.prev);
		else if (x > 0.85) gotoChapter(chapter.next);
	}

	// Prefetch the next chapter when the browser is idle: the plain GET flows
	// through the service worker's stale-while-revalidate cache, so the next
	// tap is instant and the chapter becomes readable offline too.
	$effect(() => {
		const next = chapter.next;
		const s = slug;
		const language = edition === 'modern' ? 'en-modern' : getLang();
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
		idle(() => {
			fetch(url).catch(() => {});
		});
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

	/** Read the chapter aloud from the topmost visible paragraph. */
	function startListening() {
		if (!body) return;
		const paragraphs = [...body.children].map((el) => (el as HTMLElement).innerText);
		listen.start(paragraphs, topVisibleIndex(), getLang(), {
			title: chapter.title,
			artist: `${chapter.author_name} · ${chapter.book_title}`
		});
	}

	function topVisibleIndex(): number {
		if (!body) return 0;
		const kids = body.children;
		for (let i = 0; i < kids.length; i++) {
			if (kids[i].getBoundingClientRect().bottom > HEADER_OFFSET) return i;
		}
		return 0;
	}

	// Highlight the paragraph being spoken and keep it in view.
	$effect(() => {
		const current = listen.current;
		if (!body) return;
		const kids = body.children;
		for (let i = 0; i < kids.length; i++) {
			kids[i].classList.toggle('tts-current', i === current);
		}
		if (current >= 0 && kids[current]) {
			kids[current].scrollIntoView({ block: 'center', behavior: 'smooth' });
		}
	});

	function restoreScroll(s: string, order: number) {
		// Prefer the device-local anchor; fall back to the synced resume point so
		// "continue reading" lands on the right paragraph on a fresh device too.
		const rec = getProgressRecord(s);
		const idx =
			getScrollAnchor(s, order) ??
			(rec && rec.order === order ? rec.paragraph_index : null);
		if (idx && body && body.children[idx]) {
			body.children[idx].scrollIntoView({ block: 'start' });
			window.scrollBy(0, -HEADER_OFFSET);
		} else {
			window.scrollTo(0, 0);
		}
	}

	// Throttled save of the topmost visible paragraph as the scroll anchor.
	let saveTimer: ReturnType<typeof setTimeout> | undefined;
	function onScroll() {
		clearTimeout(saveTimer);
		saveTimer = setTimeout(() => {
			if (!body) return;
			updateFraction();
			const kids = body.children;
			let topIndex = 0;
			for (let i = 0; i < kids.length; i++) {
				if (kids[i].getBoundingClientRect().top >= HEADER_OFFSET) {
					topIndex = Math.max(0, i - 1);
					break;
				}
			}
			saveScrollAnchor(slug, chapter.order, topIndex);
		}, 250);
	}

	function observeTitle(): () => void {
		if (!titleEl) return () => {};
		const io = new IntersectionObserver(([e]) => (titleVisible = e.isIntersecting), {
			rootMargin: `-${HEADER_OFFSET}px 0px 0px 0px`
		});
		io.observe(titleEl);
		return () => io.disconnect();
	}

	// Render text-range marks as <mark> spans; clicking one opens its note.
	$effect(() => {
		const list = marks.list;
		if (!body) return;
		renderMarks(body, list, (id) => {
			noteId = id;
			notePending = [];
			noteDraft = marks.getNote(id);
			noteOpen = true;
		});
	});

	const cite = $derived({
		author: chapter.author_name,
		book: chapter.book_title,
		chapter: chapter.title,
		url: $page.url.href
	});

	/** Note on a fresh selection: highlight it first, then attach the note. */
	function openNoteForSelection(segments: { p: number; s: number; e: number }[]) {
		const existing = marks.groupCovering(segments);
		noteId = existing;
		notePending = existing ? [] : segments;
		noteDraft = existing ? marks.getNote(existing) : '';
		noteOpen = true;
	}
	function saveNote() {
		if (noteId) {
			marks.setNote(noteId, noteDraft);
		} else if (notePending.length && noteDraft.trim()) {
			marks.add(notePending, noteDraft);
		}
		noteOpen = false;
	}
	function removeMark() {
		if (noteId) marks.remove(noteId);
		noteOpen = false;
	}
</script>

<svelte:head>
	<title>{chapter.title} — {chapter.book_title} — Ochorus</title>
	<meta name="description" content={metaDescription} />
	<link rel="canonical" href={canonical} />
	{#each seoAlternates as a (a.loc)}
		<link rel="alternate" hreflang={a.loc} href={a.href} />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_URL}{localizeHref(seoPath, { locale: 'en' })}" />
	<meta property="og:type" content="article" />
	<meta property="og:title" content="{chapter.title} — {chapter.book_title}" />
	<meta property="og:description" content={metaDescription} />
	<meta property="og:url" content={canonical} />
	{@html chapterLd}
</svelte:head>
<svelte:window onscroll={onScroll} onkeydown={onKeydown} />

<!-- Reader top bar: breadcrumb / context + controls. Hidden in focus mode. -->
{#if !readerUi.focus}
	<!-- Pinned to the top. In scroll mode it's `sticky` (rides the scroll, then
	     sticks); in page mode nothing scrolls, so it's `fixed` — and crucially a
	     `sticky` sibling makes Chromium drop the top line of the reader's later
	     paged columns (a paint bug), which `fixed` avoids. -->
	<div
		bind:this={chromeEl}
		class="top-0 inset-x-0 z-10 border-b border-border bg-bg/90 backdrop-blur"
		class:fixed={paged}
		class:sticky={!paged}
	>
		<div class="mx-auto flex max-w-3xl items-center justify-between gap-3 px-5 py-2.5">
			<div class="min-w-0 flex-1">
				{#if titleVisible}
					<a href={localizeHref(`/books/${slug}`)} class="text-small text-muted hover:text-text">
						← {chapter.book_title}
					</a>
				{:else}
					<!-- Once the heading scrolls away, show where you are. -->
					<div class="truncate text-small text-text">
						<span class="text-muted">{chapter.book_title} · </span>{chapter.title}
					</div>
				{/if}
			</div>
			<div class="flex shrink-0 items-center gap-0.5">
				{#if chapter.prev}
					<a
						href={chapterHref(chapter.prev.order)}
						class="btn btn-ghost !px-2 !py-1.5"
						aria-label={t('reader.previous')}
						title={t('reader.previous')}><Icon name="chevron-left" size={18} /></a
					>
				{/if}
				{#if chapter.next}
					<a
						href={chapterHref(chapter.next.order)}
						class="btn btn-ghost !px-2 !py-1.5"
						aria-label={t('reader.next')}
						title={t('reader.next')}><Icon name="chevron-right" size={18} /></a
					>
				{/if}
				{#if chapter.has_modern_edition}
					<span class="mx-1 h-5 w-px bg-border" aria-hidden="true"></span>
					<a
						href={editionToggleHref()}
						data-sveltekit-noscroll
						class="btn btn-ghost !px-2 !py-1.5 text-small"
						class:!text-accent={edition === 'modern'}
						title={edition === 'modern' ? t('reader.readOriginal') : t('reader.readModern')}
						aria-label={edition === 'modern' ? t('reader.readOriginal') : t('reader.readModern')}
					>
						{edition === 'modern' ? t('reader.original') : t('reader.modern')}
					</a>
				{/if}
				<span class="mx-1 h-5 w-px bg-border" aria-hidden="true"></span>
				<button
					class="btn btn-ghost !px-2 !py-1.5"
					class:!text-accent={currentBookmarked}
					onclick={toggleBookmark}
					aria-label={t('reader.bookmark')}
					title={t('reader.bookmark')}
					aria-pressed={currentBookmarked}><Icon name="bookmark" size={18} /></button
				>
				<button
					class="btn btn-ghost !px-2 !py-1.5"
					onclick={() => (tocOpen = true)}
					aria-label={t('reader.contents')}
					title={t('reader.contents')}><Icon name="list" size={18} /></button
				>
				<button
					class="btn btn-ghost !px-2 !py-1.5"
					onclick={() => (searchOpen = true)}
					aria-label={t('reader.search')}
					title={t('reader.search')}><Icon name="search" size={18} /></button
				>
				{#if listen.supported}
					<button
						class="btn btn-ghost !px-2 !py-1.5"
						class:!text-accent={listen.status !== 'idle'}
						onclick={() => (listen.status === 'idle' ? startListening() : listen.stop())}
						aria-label={t('reader.listen')}
						title={t('reader.listen')}><Icon name="headphones" size={18} /></button
					>
				{/if}
				<ReaderControls />
				<button
					class="btn btn-ghost !px-2 !py-1.5"
					onclick={() => readerUi.toggleFocus()}
					aria-label={t('reader.focus')}
					title={t('reader.focus')}><Icon name="maximize" size={18} /></button
				>
			</div>
		</div>
	</div>
{/if}

{#if readerUi.focus}
	<button
		class="fixed right-4 top-4 z-30 rounded-full border border-border bg-surface/90 px-3 py-1.5 text-small text-muted shadow-md backdrop-blur hover:text-text"
		onclick={() => readerUi.exitFocus()}>✕ {t('reader.exitFocus')}</button
	>
{/if}

<!-- A full-viewport wash behind the paged columns, so the margins beside the
     measure-capped spread are the same shade as the page — no lighter corners. -->
{#if paged}
	<div class="paged-backdrop" aria-hidden="true"></div>
{/if}

<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
<article
	bind:this={articleEl}
	class="mx-auto px-5 py-10"
	class:paged
	class:focus={readerUi.focus}
	class:twocol={cols === 2}
	style="{readerPrefs.style}; max-width: {articleMax}"
	dir="auto"
	onclick={onArticleClick}
>
	<!-- Breadcrumb -->
	<nav class="mb-5 flex flex-wrap items-center gap-1.5 text-small text-muted" aria-label={t('a11y.breadcrumb')}>
		<a href={localizeHref('/books')} class="hover:text-text">{t('nav.books')}</a>
		<span>›</span>
		<a href={localizeHref(`/authors/${chapter.author_slug}`)} class="hover:text-text">{chapter.author_name}</a>
		<span>›</span>
		<a href={localizeHref(`/books/${slug}`)} class="hover:text-text">{chapter.book_title}</a>
	</nav>

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
			{#if planProgress.isDone(plan.slug, planDay)}
				<span class="text-small font-semibold text-accent">✓ {t('plans.dayDone')}</span>
			{:else}
				<button class="btn btn-primary !py-1.5 text-small" onclick={completePlanDay}>
					{t('plans.markDone')}
				</button>
			{/if}
		</div>
	{/if}

	<!-- The pager wraps the chapter's own content (label, title, body). In scroll
	     mode it is display:contents (no effect); in page mode it becomes the
	     translated CSS-column content and the surrounding chrome is hidden. -->
	<div class="pager" bind:this={pager} style="--page-w:{pageW}px; --page-idx:{pageIndex}; --cols:{cols};">
		<p class="mb-1 text-small uppercase tracking-wider text-muted">
			{t('continue.chapter')} {chapter.order} · {readingTime(chapter.word_count)}
			{#if chapter.is_modern_edition}
				<span class="ml-1 text-accent">· {t('reader.modernEdition')}</span>
			{/if}
		</p>
		<h1 bind:this={titleEl} class="text-h1 mb-8">{chapter.title}</h1>

		<!-- Body HTML is cleaned server-side to a safe tag subset on ingest. -->
		<div class="reading" bind:this={body}>{@html chapter.body_html}</div>
	</div>

	<nav class="mt-14 flex items-stretch justify-between gap-3 border-t border-border pt-6">
		{#if chapter.prev}
			<a
				href={chapterHref(chapter.prev.order)}
				class="btn btn-ghost flex-1 !flex-col !items-start gap-0.5 text-left"
			>
				<span class="text-[0.7rem] uppercase tracking-wider text-muted">{t('reader.previous')}</span>
				<span class="text-small">{chapter.prev.title}</span>
			</a>
		{:else}
			<span class="flex-1"></span>
		{/if}
		{#if chapter.next}
			<a
				href={chapterHref(chapter.next.order)}
				class="btn btn-primary flex-1 !flex-col !items-end gap-0.5 text-right"
			>
				<span class="text-[0.7rem] uppercase tracking-wider opacity-75">{t('reader.next')}</span>
				<span class="text-small">{chapter.next.title}</span>
			</a>
		{:else}
			<a href={localizeHref(`/books/${slug}`)} class="btn btn-ghost flex-1 text-center">{t('reader.backToContents')}</a>
		{/if}
	</nav>
</article>

<!-- Kindle-style edge page-turn arrows (page mode only). The outer screen edge
     is already an invisible tap zone; these are the visible affordance for
     pointer users, and roll over to the adjacent chapter at a chapter's ends. -->
{#if paged}
	<button class="pageturn left" onclick={() => turnPage(-1)} aria-label={t('reader.previous')} title={t('reader.previous')}>
		<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
	</button>
	<button class="pageturn right" onclick={() => turnPage(1)} aria-label={t('reader.next')} title={t('reader.next')}>
		<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
	</button>
{/if}

<!-- Reading-progress footer: a draggable scrubber + location, fixed, hidden in
     focus/Listen modes. -->
{#if !readerUi.focus && listen.status === 'idle'}
	<div bind:this={footEl} class="progress-foot">
		<input
			class="scrubber"
			type="range"
			min="0"
			max="1"
			step="0.005"
			value={chapterFrac}
			oninput={(e) => {
				const frac = Number(e.currentTarget.value);
				if (paged) goToPage(Math.round(frac * (pageTotal - 1)));
				else scrubTo(frac);
			}}
			aria-label={t('progress.scrub')}
			aria-valuetext="{t('progress.page')} {currentPage} / {pageCount}"
		/>
		<div class="progress-meta">
			<span>{t('progress.page')} {currentPage} / {pageCount}</span>
			<span class="mx-1.5 opacity-50">·</span>
			<span>{minutesLeft} {t('progress.minLeft')}</span>
			{#if bookPercent !== null}
				<span class="mx-1.5 opacity-50">·</span>
				<span>{bookPercent}% {t('progress.through')}</span>
			{/if}
		</div>
	</div>
{/if}

<SelectionBar
	container={body}
	{cite}
	onHighlight={(segments) => {
		const existing = marks.groupCovering(segments);
		if (existing) marks.remove(existing);
		else marks.add(segments);
	}}
	onNote={openNoteForSelection}
	isHighlighted={(segments) => marks.groupCovering(segments) !== null}
	onDefine={(word, top, left) => define.show(word, top, left)}
/>

<DefinePopover />
<ScripturePopover />

<TocDrawer {slug} currentOrder={chapter.order} {edition} bind:open={tocOpen} />

<SearchDrawer {slug} bind:open={searchOpen} />

<ListenBar />

{#if noteOpen}
	<div class="note-overlay" role="dialog" aria-modal="true" aria-label={t('reader.note')}>
		<div class="note-card">
			<h2 class="mb-2 text-h3">{t('reader.note')}</h2>
			<textarea
				bind:value={noteDraft}
				rows="5"
				class="w-full rounded-sm border border-border bg-bg p-3 text-body text-text"
				placeholder="…"
			></textarea>
			<div class="mt-3 flex items-center gap-2">
				{#if noteId}
					<button class="btn btn-ghost !text-red-700 dark:!text-red-400" onclick={removeMark}>
						{t('reader.removeHighlight')}
					</button>
				{/if}
				<span class="flex-1"></span>
				<button class="btn btn-ghost" onclick={() => (noteOpen = false)}>{t('common.cancel')}</button>
				<button class="btn btn-primary" onclick={saveNote}>{t('common.save')}</button>
			</div>
		</div>
	</div>
{/if}

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
		top: var(--pgtop, 3.4rem);
		bottom: var(--pgbot, 3.1rem);
		left: 0;
		right: 0;
		z-index: 5;
		margin-inline: auto;
		padding: 0 !important;
		overflow: hidden;
		background: var(--bg);
	}
	article.paged.focus {
		top: 0;
		bottom: 0;
	}
	/* Sits below the columns (z 5) and the edge arrows (z 6), above the page, so
	   the whole reading surface is one uniform shade. */
	.paged-backdrop {
		position: fixed;
		inset: 0;
		z-index: 4;
		background: var(--bg);
	}
	/* Hide the surrounding chrome (breadcrumb, plan strip, chapter nav) in page
	   mode — only the pager's content is paginated. */
	article.paged > :not(.pager) {
		display: none;
	}
	.paged .pager {
		--pgpad: 1.25rem;
		--cols: 1;
		display: block;
		height: 100%;
		max-width: none;
		box-sizing: border-box;
		padding: 0.85rem var(--pgpad) 0.5rem;
		/* Each page window (width --page-w) holds --cols columns. With the gap set
		   to twice the side padding, the columns land flush inside the page and the
		   inter-page gutter parks the next column fully off-screen (no sliver). This
		   one formula yields a single column when --cols is 1 and a Kindle-style
		   two-column spread when it's 2. */
		column-width: calc(var(--page-w) / var(--cols) - 2 * var(--pgpad));
		column-gap: calc(2 * var(--pgpad));
		column-fill: auto;
		transform: translateX(calc(-1 * var(--page-idx) * var(--page-w)));
		transition: transform 0.28s ease;
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
	   off the normal-measure spread width; max() keeps it on-screen when the
	   column runs wide, and touch screens hide the arrows entirely (below). */
	.pageturn.left {
		left: max(0.5rem, calc((100vw - 88rem) / 2 - 3.75rem));
	}
	.pageturn.right {
		right: max(0.5rem, calc((100vw - 88rem) / 2 - 3.75rem));
	}
	/* On touch screens the tap zones suffice; keep the edges clean. */
	@media (pointer: coarse) {
		.pageturn {
			display: none;
		}
	}

	.progress-foot {
		position: fixed;
		inset-inline: 0;
		bottom: 0;
		z-index: 30;
		padding: 0.25rem 1rem 0.4rem;
		text-align: center;
		font-size: 0.72rem;
		color: var(--muted);
		background: color-mix(in srgb, var(--bg) 82%, transparent);
		backdrop-filter: blur(6px);
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

	/* Text-range marks: <mark> spans wrapped around the selected text. */
	:global(.reading mark.range-mark) {
		background: color-mix(in srgb, var(--gold) 28%, transparent);
		color: inherit;
		border-radius: 2px;
		padding: 0.08em 0;
		box-decoration-break: clone;
		-webkit-box-decoration-break: clone;
		cursor: pointer;
	}
	:global(.reading mark.range-mark:hover) {
		background: color-mix(in srgb, var(--gold) 42%, transparent);
	}
	/* A mark carrying a note gets a subtle underline cue. */
	:global(.reading mark.range-mark.has-note) {
		border-bottom: 2px solid var(--gold);
	}
	/* Paragraph currently being read aloud in Listen mode. */
	:global(.reading > .tts-current) {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
		border-radius: 4px;
		box-shadow: 0 0 0 6px color-mix(in srgb, var(--accent) 10%, transparent);
		transition: background 0.3s ease;
	}
	.note-overlay {
		position: fixed;
		inset: 0;
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		background: rgb(0 0 0 / 0.4);
	}
	.note-card {
		width: 100%;
		max-width: 32rem;
		border-radius: var(--radius-card);
		border: 1px solid var(--border);
		background: var(--surface);
		padding: 1.25rem;
		box-shadow: 0 10px 40px rgb(0 0 0 / 0.35);
	}
</style>
