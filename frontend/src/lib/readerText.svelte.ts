/**
 * Everything attached to a body of read prose, minus where you are in it.
 *
 * `Reader.svelte` already owns this for sermons and biographies. The chapter
 * reader could not use it, for a reason that is structural rather than
 * historical: in page-turn mode the prose lives inside `.pager`, which carries a
 * `translateX`, and a `position: fixed` overlay inside a transformed ancestor is
 * positioned against that ancestor instead of the viewport. Dropping `Reader`
 * into the pager would have slid the selection bar, the popovers and the listen
 * bar sideways with every page turn. So the machinery moves here, where a
 * surface can hold it while rendering the prose in one place and the overlays in
 * another.
 *
 * What it deliberately does NOT own is POSITION — the resume anchor, the
 * fraction read, the scroll restore. Those are meaningful only against a layout,
 * and the two layouts genuinely disagree: a scrolling page measures the top
 * paragraph from viewport rectangles, while a paged one derives it from column
 * geometry (`pageOf`/`firstIndexOnPage`) and has no scroll position at all. Each
 * surface keeps its own.
 *
 * The chapter reader had all of this a second time — the marks-and-search-hits
 * effect, the note dialog, the selection handlers and the follow-along
 * highlighter, comments included. The copies had already drifted: the chapter
 * one toggled `tts-current` over every block on every spoken paragraph, which
 * `Reader` had since replaced with tracking the one marked element, noting that
 * "a long chapter is 76+ blocks and this fires on every paragraph". The longest
 * prose in the app was running the slow version.
 */
import { onMount } from 'svelte';
import { marks, type Segment } from '$lib/marks.svelte';
import { removeMarkUndoable, clearNoteUndoable } from '$lib/undoable';
import { renderMarks } from '$lib/rangeMarks';
import { findQueryHits } from '$lib/searchHits';
import { listen } from '$lib/listen.svelte';
import { define } from '$lib/define.svelte';
import { scripture } from '$lib/scripture.svelte';
import { getLang } from '$lib/lang.svelte';
import { spokenText, blankFootnoteMarkers } from '$lib/listenText';
import { shouldFollow } from '$lib/listenFollow';
import { saveScrollAnchor } from '$lib/progress';
import { HEADER_OFFSET, prefersReducedMotion } from '$lib/reading';
import { DEFAULT_HIGHLIGHT, type WorkKind } from '$lib/reading-schema';

/** How long read-along leaves the page alone after a hand-scroll. */
const FOLLOW_YIELD_MS = 3000;
/** How long to disregard `scroll` events after our own follow scroll (covers the
 *  smooth animation) so it isn't mistaken for the reader scrolling by hand. */
const SELF_SCROLL_MS = 1000;

/** Attribution for copy/share from the selection bar. */
export interface Cite {
	author: string;
	book: string;
	chapter: string;
	url: string;
}

/**
 * Reactive inputs, as getters rather than values: the surface reads them inside
 * effects, so passing a plain object would snapshot them at construction and a
 * client-side navigation to the next chapter would keep painting the old one's
 * highlights.
 */
export interface ReaderTextOptions {
	kind: () => WorkKind;
	slug: () => string;
	order: () => number;
	language: () => string;
	/** The rendered prose element, once the surface has bound it. */
	body: () => HTMLElement | undefined;
	/**
	 * Which paragraph the reader is on, for "read aloud from here". Supplied by
	 * the surface because only it knows its layout — a paged chapter answers from
	 * column geometry, a scrolling one from viewport rectangles.
	 */
	topIndex: () => number;
	listenTitle: () => string;
	listenArtist: () => string;
	cite: () => Cite;
	/**
	 * What the reader searched for to get here, so their match can be marked.
	 * Passed in rather than read off the URL: store auto-subscription (`$page`)
	 * is a .svelte-file compiler feature and this is a rune module, and keeping
	 * the URL out of here leaves the decisions testable without a router.
	 */
	searchQuery?: () => string;
	/**
	 * Brings an element into view. A paged surface supplies it — its article is
	 * `overflow: clip`, so `scrollIntoView` cannot reach a later page and the
	 * surface must turn to it instead. Defaults to `scrollIntoView`.
	 */
	reveal?: (el: Element) => void;
	/**
	 * Called when read-aloud finishes the last paragraph on its own (not on a
	 * user stop). The chapter reader supplies it to roll into the next chapter;
	 * single-document surfaces (sermon, bio) leave it unset.
	 */
	onListenFinish?: () => void;
}

export class ReaderText {
	// --- Note dialog -----------------------------------------------------------
	/** Whether the note editor is up. Surfaces read it to suppress hotkeys. */
	open = $state(false);
	/** The mark being edited, or null when the note will create a fresh one. */
	id = $state<string | null>(null);
	/** Segments awaiting a note — only set when `id` is null. */
	pending = $state<Segment[]>([]);
	draft = $state('');
	color = $state<string>(DEFAULT_HIGHLIGHT);

	readonly #o: ReaderTextOptions;

	constructor(options: ReaderTextOptions) {
		this.#o = options;
	}

	get cite(): Cite {
		return this.#o.cite();
	}

	/** Where the open text is — what a Notebook entry written from it links back to. */
	get where(): { kind: WorkKind; slug: string; order: number; edition: string } {
		return {
			kind: this.#o.kind(),
			slug: this.#o.slug(),
			order: this.#o.order(),
			edition: this.#o.language()
		};
	}

	/**
	 * Read aloud. Starts from the paragraph the surface says you're on, or from
	 * `from` when given — the chapter roll-over passes 0 to begin the next
	 * chapter at its top.
	 */
	startListening = (from?: number): void => {
		const body = this.#o.body();
		if (!body) return;
		// spokenText, not innerText: one entry per child (so the follow-along
		// highlight still lines up), with footnote markers and other eye-only
		// bits removed so the engine doesn't voice "…grace four".
		const paragraphs = [...body.children].map((el) => spokenText(el));
		listen.start(paragraphs, from ?? this.#o.topIndex(), {
			lang: getLang(),
			media: { title: this.#o.listenTitle(), artist: this.#o.listenArtist() },
			onFinish: this.#o.onListenFinish,
			// The spoken paragraph IS the resume point while listening — save it (this
			// also pushes the synced progress paragraph_index), so picking the work
			// back up, here or on another device, lands where the audio reached. The
			// scroll handlers step aside while playing so they don't overwrite it.
			onAdvance: (index) =>
				saveScrollAnchor(this.#o.slug(), this.#o.order(), index, this.#o.kind())
		});
	};

	/**
	 * Tap a server-wrapped Bible reference → open the scripture popover. Returns
	 * whether it handled the event, because the chapter reader's own click
	 * handler has to know not to also treat the tap as a page turn.
	 */
	onScriptureClick = (e: MouseEvent): boolean => {
		const a = (e.target as HTMLElement).closest?.('a.scripture-ref') as HTMLElement | null;
		if (!a?.dataset.ref) return false;
		e.preventDefault();
		const r = a.getBoundingClientRect();
		scripture.show(
			a.dataset.ref,
			r.bottom + window.scrollY,
			r.left + window.scrollX + r.width / 2
		);
		return true;
	};

	// --- Selection bar ---------------------------------------------------------

	/** Highlight, recolour, or un-highlight the selection, in that order. */
	onHighlight = (segments: Segment[], color: string): void => {
		const existing = marks.groupCovering(segments);
		if (!existing) marks.add(segments, undefined, color);
		else if (marks.getColor(existing) === color) removeMarkUndoable(existing);
		else marks.setColor(existing, color);
	};

	highlightColor = (segments: Segment[]): string | null => {
		const id = marks.groupCovering(segments);
		return id ? marks.getColor(id) : null;
	};

	onDefine = (word: string, top: number, left: number): void => {
		void define.show(word, top, left);
	};

	/** Retire a definition once the selection has grown past the word it was for. */
	onDefineClose = (): void => {
		define.close();
	};

	/** Note on a fresh selection: highlight it first, then attach the note. */
	openNoteForSelection = (segments: Segment[]): void => {
		const existing = marks.groupCovering(segments);
		this.id = existing;
		this.pending = existing ? [] : segments;
		this.draft = existing ? marks.getNote(existing) : '';
		this.color = existing ? marks.getColor(existing) : DEFAULT_HIGHLIGHT;
		this.open = true;
	};

	saveNote = (): void => {
		if (this.id) {
			// Emptying the field deletes the note — offer a way back for that one.
			if (!this.draft.trim()) clearNoteUndoable(this.id);
			else marks.setNote(this.id, this.draft);
			marks.setColor(this.id, this.color);
		} else if (this.pending.length && this.draft.trim()) {
			marks.add(this.pending, this.draft, this.color);
		}
		this.open = false;
	};

	removeMark = (): void => {
		if (this.id) removeMarkUndoable(this.id);
		this.open = false;
	};

	close = (): void => {
		this.open = false;
	};

	/** Open the editor for an existing mark — what clicking a `<mark>` does. */
	#editMark = (id: string): void => {
		this.id = id;
		this.pending = [];
		this.draft = marks.getNote(id);
		this.color = marks.getColor(id);
		this.open = true;
	};

	/**
	 * Register the effects. Separate from the constructor so it is obvious that
	 * this needs component-initialisation context; `createReaderText` does both.
	 */
	attach(): void {
		const o = this.#o;

		// Reload when navigating between works.
		$effect(() => {
			marks.load(o.slug(), o.order(), o.language(), o.kind());
		});

		// Follow-along: highlight the paragraph being spoken and keep it in view.
		// Track the marked element rather than toggling the class over every block
		// — a long chapter is 76+ blocks and this fires on every paragraph.
		let spokenEl: Element | null = null;

		// "When did the reader last scroll by hand?" This watches the real `scroll`
		// event, so it catches every way to move the page — wheel, touch (and its
		// momentum glide), keyboard (Space / PageDown), scrollbar drag — not just
		// the pointer subset. The one thing `scroll` can't tell apart is our OWN
		// scrollIntoView below, which also fires it; `ignoreScrollUntil` masks the
		// brief window around that so following the audio isn't read as the reader
		// moving the page and doesn't make us yield to ourselves.
		let lastUserScroll = -Infinity;
		let ignoreScrollUntil = 0;
		$effect(() => {
			const onScroll = () => {
				if (Date.now() < ignoreScrollUntil) return;
				lastUserScroll = Date.now();
			};
			window.addEventListener('scroll', onScroll, { passive: true });
			return () => window.removeEventListener('scroll', onScroll);
		});

		$effect(() => {
			const current = listen.current;
			const body = o.body();
			if (!body) return;
			spokenEl?.classList.remove('tts-current');
			spokenEl = body.children[current] ?? null;
			if (!spokenEl) return;
			spokenEl.classList.add('tts-current');
			// (The resume-point save lives in the `onAdvance` handed to listen.start
			// below — driven by the audio, not this reactive effect, so it can't fire
			// with a stale index against a freshly-navigated chapter.)
			// Only pull it into view when it has drifted off-station and the reader
			// isn't mid-scroll — see `shouldFollow`. Re-centring every block, or
			// fighting a hand-scroll, is what made long chapters lose their place.
			const follow = shouldFollow({
				top: spokenEl.getBoundingClientRect().top,
				viewportHeight: window.innerHeight,
				headerOffset: HEADER_OFFSET,
				msSinceUserScroll: Date.now() - lastUserScroll,
				yieldMs: FOLLOW_YIELD_MS
			});
			if (follow) {
				// Mask the scroll events our own animation is about to emit.
				ignoreScrollUntil = Date.now() + SELF_SCROLL_MS;
				spokenEl.scrollIntoView({
					block: 'center',
					behavior: prefersReducedMotion() ? 'auto' : 'smooth'
				});
			}
		});

		// Stop speech when navigating to another work or leaving the page.
		$effect(() => {
			void o.slug();
			void o.order();
			return () => listen.stop();
		});

		// Paint marks as <mark> spans; clicking one opens its note editor. Arriving
		// from a search result: highlight what matched and scroll to it, rather than
		// dropping the reader at the top to re-find their sentence. Offsets are
		// computed from the rendered blocks and handed to the SAME renderer the
		// highlights use — that function restores each block from `dataset.pristine`,
		// so a separate pass would be wiped whenever a highlight changed, and the two
		// would fight over the same HTML.
		let scrolledToHit = false;
		$effect(() => {
			const list = marks.list;
			const body = o.body();
			if (!body) return;
			const query = (o.searchQuery?.() ?? '').trim();
			// Recomputed here, not once on mount: the marks render restores pristine
			// HTML, so hit offsets have to be handed over on every pass.
			// `blankFootnoteMarkers`, not raw `textContent`: a search must see the
			// same paragraph the listen engine speaks, with footnote markers gone, so
			// a query never matches a `<sup>4</sup>` or an inline `[4]`. It blanks them
			// to spaces rather than deleting them, keeping the string the same length
			// so the offsets still line up with the live text nodes the highlighter
			// walks.
			const hits = query
				? findQueryHits(
						Array.from(body.children).map((el) => blankFootnoteMarkers(el)),
						query
					)
				: [];
			renderMarks(body, list, this.#editMark, hits);

			// Once per arrival: bring the first match into view. Guarded, or every
			// highlight edit would yank the reader back up the page.
			if (hits.length && !scrolledToHit) {
				scrolledToHit = true;
				requestAnimationFrame(() => {
					const hit = body.querySelector('mark.search-hit');
					if (!hit) return;
					if (this.#o.reveal) this.#o.reveal(hit);
					else hit.scrollIntoView({ block: 'center', behavior: 'smooth' });
				});
			}
		});

		// Marks can be replaced underneath us (sign-in merge / sign-out wipe).
		onMount(() => {
			const onSync = () => marks.refresh();
			window.addEventListener('ochorus:sync', onSync);
			return () => window.removeEventListener('ochorus:sync', onSync);
		});
	}
}

/** Build the machinery and register its effects. Call during component init. */
export function createReaderText(options: ReaderTextOptions): ReaderText {
	const reader = new ReaderText(options);
	reader.attach();
	return reader;
}
