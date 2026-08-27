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
import { renderMarks } from '$lib/rangeMarks';
import { findQueryHits } from '$lib/searchHits';
import { listen } from '$lib/listen.svelte';
import { define } from '$lib/define.svelte';
import { scripture } from '$lib/scripture.svelte';
import { getLang } from '$lib/lang.svelte';
import { DEFAULT_HIGHLIGHT, type WorkKind } from '$lib/reading-schema';

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

	/** Read aloud, starting from the paragraph the surface says you're on. */
	startListening = (): void => {
		const body = this.#o.body();
		if (!body) return;
		const paragraphs = [...body.children].map((el) => (el as HTMLElement).innerText);
		listen.start(paragraphs, this.#o.topIndex(), getLang(), {
			title: this.#o.listenTitle(),
			artist: this.#o.listenArtist()
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
		else if (marks.getColor(existing) === color) marks.remove(existing);
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
			marks.setNote(this.id, this.draft);
			marks.setColor(this.id, this.color);
		} else if (this.pending.length && this.draft.trim()) {
			marks.add(this.pending, this.draft, this.color);
		}
		this.open = false;
	};

	removeMark = (): void => {
		if (this.id) marks.remove(this.id);
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
		$effect(() => {
			const current = listen.current;
			const body = o.body();
			if (!body) return;
			spokenEl?.classList.remove('tts-current');
			spokenEl = body.children[current] ?? null;
			if (spokenEl) {
				spokenEl.classList.add('tts-current');
				spokenEl.scrollIntoView({ block: 'center', behavior: 'smooth' });
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
			const hits = query
				? findQueryHits(
						Array.from(body.children).map((el) => el.textContent ?? ''),
						query
					)
				: [];
			renderMarks(body, list, this.#editMark, hits);

			// Once per arrival: bring the first match into view. Guarded, or every
			// highlight edit would yank the reader back up the page.
			if (hits.length && !scrolledToHit) {
				scrolledToHit = true;
				requestAnimationFrame(() =>
					body
						.querySelector('mark.search-hit')
						// Both axes: the chapter reader lays pages out in columns and
						// scrolls horizontally, so `block` alone would never reach a hit on
						// a later page.
						?.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' })
				);
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
