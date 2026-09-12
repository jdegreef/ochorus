<script lang="ts">
	/**
	 * The reading machinery every long-form work shares — the prose itself, and
	 * everything that has to know about it.
	 *
	 * Ochorus has three kinds of long prose — book chapters, sermons and author
	 * biographies — and each needs the same things: a resume point that survives a
	 * text-size change, highlights and notes, read-aloud with follow-along, the
	 * dictionary and scripture popovers, and search-hit rendering. That was built
	 * for chapters, copied to sermons, and the copy silently drifted (the sermon
	 * reader never gained bookmarks). This owns it once.
	 *
	 * It deliberately does NOT own the page: no <article>, no sticky top bar, no
	 * time-remaining pill. Those looked shared when only the sermon page existed,
	 * but the three surfaces genuinely differ — a biography's prose is one band in
	 * a wider page (portrait, timeline, book grid) that must not inherit
	 * `--reading-measure`, and the chapter reader's paged layout needs its own
	 * article element, its own bottom scrubber, and a bar that switches to
	 * `fixed`. A component whose extension point is "escape my container" should
	 * not own the container. So each route renders its own shell and reads what it
	 * needs from here: `bind:frac` for a progress bar, `bind:body` for an outline,
	 * `startListening()` for a Listen button.
	 *
	 * `kind` namespaces every stored key — that plumbing already understands
	 * 'book' | 'sermon' | 'bio' end to end (localStorage prefix, API, and the
	 * Django column), so a new surface needs no migration.
	 *
	 * WHAT LIVES WHERE. This component is scroll-position plus a place to put the
	 * prose. Everything attached to the TEXT — marks, notes, the selection bar,
	 * listen follow-along, search hits — lives in `$lib/readerText.svelte.ts`, and
	 * the floating chrome in `ReaderOverlays.svelte`. That split is what lets the
	 * chapter reader share this machinery at all: its page-turn mode transforms
	 * the element the prose sits in, and a `position: fixed` overlay inside a
	 * transformed ancestor is laid out against that ancestor, so the overlays have
	 * to be rendered somewhere the prose is not.
	 */
	import { onMount, tick } from 'svelte';
	import { page } from '$app/stores';
	import { contentLang, HEADER_OFFSET, placeAfterLayout } from '$lib/reading';
	import {
		getScrollAnchor,
		saveScrollAnchor,
		saveProgress,
		getProgressRecord,
		offerFinish
	} from '$lib/progress';
	import { listen } from '$lib/listen.svelte';
	import { type WorkKind } from '$lib/reading-schema';
	import { createReaderText, type Cite } from '$lib/readerText.svelte';
	import ReaderOverlays from '$lib/components/ReaderOverlays.svelte';

	interface Props {
		/** Namespaces every stored key (position, anchors, marks). */
		kind: WorkKind;
		/** Identifies the work within its kind. For a bio, the author's slug. */
		slug: string;
		/** Chapters pass their order; single-document kinds (sermon, bio) get 1. */
		order?: number;
		language: string;
		/** Server-cleaned body HTML. Scripture refs arrive pre-wrapped. */
		html: string;
		/** Attribution for copy/share from the selection bar. */
		cite: Cite;
		/** Shown in the OS media session while reading aloud. */
		listenTitle: string;
		listenArtist: string;
		/** Extra classes on the prose element, for surfaces with their own band width. */
		class?: string;
		/** The rendered prose, for pages that measure it (outlines, bookmarks). */
		body?: HTMLElement;
		/**
		 * How far through the prose the reader is, 0–1. Bind it to drive a progress
		 * bar or a time-remaining estimate in whatever chrome the page renders.
		 */
		frac?: number;
		/**
		 * Height of the page's own sticky chrome, in px — how far down the viewport
		 * "the top" really is. Both halves of the resume cycle use it, so they must
		 * agree: restoring parks a paragraph just below it, and the next save asks
		 * which paragraph is first below it.
		 *
		 * Getting it wrong drifts the resume point BACKWARDS. A page with no sticky
		 * bar that inherits 64 leaves the previous paragraph's last line above the
		 * threshold, so the next scroll saves N-1, and every reopen walks back one
		 * more. Defaults to the readers' bar height; surfaces without one pass 0.
		 */
		headerOffset?: number;
		/**
		 * When true, scrolling to the end of this prose finishes the WORK — it drops
		 * out of "Continue reading" onto the finished shelf. Set it only on a
		 * dedicated reading surface, where reaching the end of the prose really is
		 * the reader finishing the work: the sermon page is the sermon. NOT the
		 * author page, where the bio is one band above a book grid — scrolling past
		 * it to browse the books would be a false completion; a bio is finished
		 * explicitly instead (Settings › Activity). Books don't use this component;
		 * their finish is "reached the end of the LAST chapter", in the chapter route.
		 */
		finishOnEnd?: boolean;
	}

	let {
		kind,
		slug,
		order = 1,
		language,
		html,
		cite,
		listenTitle,
		listenArtist,
		class: className = '',
		body = $bindable(),
		frac = $bindable(0),
		headerOffset = HEADER_OFFSET,
		finishOnEnd = false
	}: Props = $props();

	// --- Position --------------------------------------------------------------
	// Anchored to the top-visible paragraph, not a pixel offset, so a saved spot
	// survives a change of text size or column width.
	let saveTimer: ReturnType<typeof setTimeout> | undefined;

	// When this work was opened, so the restore-scroll settle (which emits scroll
	// events and can land near the end of a work the reader left there) doesn't
	// auto-finish it. Genuine reading reaches the end well after this window —
	// same guard as the chapter reader's markChapterComplete.
	let openedAt = 0;
	// Fire the finish at most once per open (like the book route's
	// `chapterCelebrated`), so lingering in the end region doesn't re-run
	// `offerFinish` — and its localStorage read — on every scroll tick.
	let didFinish = false;
	/** How far through the prose counts as "reached the end" for auto-finish —
	 *  forgiving of trailing attribution / footnotes below the last paragraph. */
	const FINISH_FRAC = 0.95;

	function maybeFinish() {
		if (didFinish || !finishOnEnd || performance.now() - openedAt < 1500 || frac < FINISH_FRAC)
			return;
		didFinish = true;
		offerFinish(slug, kind);
	}

	/** Index of the first block still on screen. Pages need this for bookmarks. */
	export function topVisibleIndex(): number {
		if (!body) return 0;
		const kids = body.children;
		for (let i = 0; i < kids.length; i++) {
			if (kids[i].getBoundingClientRect().bottom > headerOffset) return i;
		}
		return Math.max(0, kids.length - 1);
	}

	function updateFraction() {
		if (!body) return;
		const rect = body.getBoundingClientRect();
		if (rect.height <= 0) return;
		const seen = Math.min(Math.max(window.innerHeight - rect.top, 0), rect.height);
		frac = Math.min(1, Math.max(0, seen / rect.height));
	}

	function handleScroll() {
		clearTimeout(saveTimer);
		saveTimer = setTimeout(() => {
			updateFraction();
			// While actively playing, listen.start's onAdvance owns the resume point
			// (the spoken paragraph); don't overwrite it with the viewport-top one.
			// While PAUSED we do save — the reader may be scrolling ahead to read.
			if (listen.status !== 'playing') saveScrollAnchor(slug, order, topVisibleIndex(), kind);
			// Reaching the end of a single-document work finishes it (no-op for books).
			maybeFinish();
		}, 250);
	}

	// Record the visit (so the work lands in "Continue reading") and restore the
	// saved spot — a `?p=` deep link (notebook highlights) wins over the device
	// anchor. Effect, not onMount: client-side nav between works reuses this
	// component.
	let restoredFor = '';
	$effect(() => {
		const key = `${kind}:${slug}:${order}`;
		if (!body || restoredFor === key) return;
		restoredFor = key;
		openedAt = performance.now();
		didFinish = false;
		// A pending scroll-save from the PREVIOUS work must not fire against this
		// one's body (it would record a bogus synced resume point).
		clearTimeout(saveTimer);
		// Seed a ?p= deep link into the anchor FIRST so the progress record (and
		// the resume point that syncs to the account) starts at the jumped-to
		// paragraph.
		const fromUrl = Number($page.url.searchParams.get('p'));
		if (Number.isFinite(fromUrl) && fromUrl > 0) {
			saveScrollAnchor(slug, order, fromUrl, kind);
		}
		saveProgress(slug, order, language, kind);
		(async () => {
			await tick();
			// Deep link > device anchor > synced resume point (fresh device).
			const idx =
				Number.isFinite(fromUrl) && fromUrl > 0
					? fromUrl
					: (getScrollAnchor(slug, order, kind) ??
						getProgressRecord(slug, kind)?.paragraph_index ??
						0);
			if (idx > 0 && body?.children[idx]) {
				placeAfterLayout(() => {
					const el = body?.children[idx];
					if (!el) return;
					el.scrollIntoView({ block: 'start' });
					window.scrollBy(0, -headerOffset);
					updateFraction();
				});
			}
			updateFraction();
		})();
	});

	// A scroll-save timer must not outlive the page.
	onMount(() => () => clearTimeout(saveTimer));

	// --- Everything attached to the text ---------------------------------------
	const reader = createReaderText({
		kind: () => kind,
		slug: () => slug,
		order: () => order,
		language: () => language,
		body: () => body,
		topIndex: topVisibleIndex,
		listenTitle: () => listenTitle,
		listenArtist: () => listenArtist,
		cite: () => cite,
		searchQuery: () => $page.url.searchParams.get('q') ?? ''
	});

	/** Read aloud, starting from the paragraph you're reading. */
	export function startListening() {
		reader.startListening();
	}
</script>

<svelte:window onscroll={handleScroll} />

<!-- Body HTML is cleaned server-side to a safe tag subset on ingest; Bible
     references are wrapped as tappable spans (scripture popover). -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<!-- eslint-disable-next-line svelte/no-at-html-tags -->
<div class="reading {className}" bind:this={body} onclick={reader.onScriptureClick} dir="auto" lang={contentLang(language)}>{@html html}</div>

<ReaderOverlays {reader} container={body} {language} />

<style>
	/* Paragraph currently being read aloud in Listen mode. */
	:global(.reading > .tts-current) {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
		border-radius: 4px;
		box-shadow: 0 0 0 6px color-mix(in srgb, var(--accent) 10%, transparent);
		transition: background var(--duration-base) ease;
	}

	/* Text-range marks (<mark> spans) are styled globally in app.css. */
</style>
