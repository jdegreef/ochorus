/**
 * Shared on-page navigation machinery for the long-form reading surfaces.
 *
 * Three pages grew their own "which section am I in" / "jump to a section"
 * code independently — the author page (a fixed bio/books/sermons/faq sub-nav),
 * the sermon page (a dynamic homiletic outline) and the chapter reader (a single
 * "is the title still on screen" flag). This module is the one place that owns:
 *
 *  - `scrollSpy`      — an IntersectionObserver over a (possibly changing) set of
 *                       element ids, exposing whichever one currently sits in the
 *                       spy band as `active`;
 *  - `elementVisible` — the degenerate single-element case, a reactive boolean;
 *  - `jumpToSection`  — a smooth scroll to an id that lands the target below the
 *                       pinned bars via CSS `scroll-margin-top` (the
 *                       `--pinned-offset` contract), NOT manual `scrollTo` math.
 *
 * Landing offset lives in CSS, not here: each surface sets `scroll-margin-top`
 * on its anchors (typically `calc(var(--pinned-offset, …) + 0.5rem)`), so the
 * amount a jump clears is owned by the same variable the sticky bars publish and
 * can never drift from what is actually pinned above the prose.
 */

/** The vertical band a section must enter to become `active`. */
export interface ScrollSpyOptions {
	/**
	 * IntersectionObserver `rootMargin`. The default lights whatever section
	 * crosses a thin band around the viewport's vertical middle
	 * (`-45% 0px -50% 0px`) — the same band first used on the author sub-nav, so
	 * the highlight tracks the section you are actually reading rather than the
	 * one whose heading happens to touch the top bar.
	 */
	rootMargin?: string;
}

/** Options for a single jump. */
export interface JumpOptions {
	/**
	 * Write `#<id>` into the address bar (via `history.replaceState`, so it does
	 * not add a history entry). Defaults to `true` — a linkable jump-nav wants a
	 * shareable/back-restorable hash. Pass `false` for an ephemeral in-page
	 * outline that should not rewrite the URL.
	 */
	updateHash?: boolean;
}

/**
 * Smooth-scroll to the element with `id`, honouring reduced-motion. The element
 * is expected to carry its own `scroll-margin-top`, so `scrollIntoView` lands it
 * below whatever is pinned above the prose — no offset arithmetic here.
 */
export function jumpToSection(id: string, options: JumpOptions = {}): void {
	const el = document.getElementById(id);
	if (!el) return;
	const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
	el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
	if (options.updateHash ?? true) history.replaceState(null, '', `#${id}`);
}

/** The reactive handle returned by {@link scrollSpy}. */
export interface ScrollSpy {
	/** The id of the section currently in the spy band, or `''` before any. */
	readonly active: string;
	/**
	 * Jump to a section AND light it at once, so the tap feels immediate rather
	 * than waiting for the scroll to bring it into the band. Forwards
	 * {@link JumpOptions} to {@link jumpToSection}.
	 */
	jumpTo(id: string, options?: JumpOptions): void;
	/** Set the active id directly (e.g. to pre-light before an external scroll). */
	set(id: string): void;
}

/**
 * Track which of a set of sections is currently on screen.
 *
 * `ids` is a getter so a *changing* set works: the sermon outline is built from
 * the rendered body after hydration, and re-reading it here re-observes when it
 * appears or changes. Call this once from a component's `<script>` (it owns an
 * `$effect`, so it must run during component init, like any runes store).
 *
 * No-JS / prerender: nothing lights (there is no observer), but the links still
 * jump — the markup and `scroll-margin` do that on their own.
 */
export function scrollSpy(ids: () => string[], options: ScrollSpyOptions = {}): ScrollSpy {
	const rootMargin = options.rootMargin ?? '-45% 0px -50% 0px';
	let active = $state('');

	$effect(() => {
		const list = ids();
		if (typeof IntersectionObserver === 'undefined') return;
		const els = list
			.map((id) => document.getElementById(id))
			.filter((el): el is HTMLElement => el != null);
		if (!els.length) return;
		const io = new IntersectionObserver(
			(entries) => {
				// Last intersecting entry wins: as you scroll down, the section
				// entering the band supersedes the one leaving it.
				for (const e of entries) if (e.isIntersecting) active = e.target.id;
			},
			{ rootMargin }
		);
		els.forEach((el) => io.observe(el));
		return () => io.disconnect();
	});

	return {
		get active() {
			return active;
		},
		set(id: string) {
			active = id;
		},
		jumpTo(id: string, options?: JumpOptions) {
			active = id;
			jumpToSection(id, options);
		}
	};
}

/** Options for {@link elementVisible}. */
export interface ElementVisibleOptions {
	/** IntersectionObserver `rootMargin` (e.g. inset the top by the header height). */
	rootMargin?: string;
	/**
	 * Value before the observer first reports — the observer corrects it on the
	 * next frame. Defaults to `false`; pass `true` for an element that starts on
	 * screen (e.g. a title at the top of the page on load).
	 */
	initial?: boolean;
}

/** The reactive handle returned by {@link elementVisible}. */
export interface ElementVisible {
	/** Whether the observed element currently intersects the viewport/band. */
	readonly visible: boolean;
}

/**
 * The single-element case of {@link scrollSpy}: watch one element (given as a
 * getter, so a `bind:this` node that arrives after mount is picked up) and
 * expose whether it is on screen. Used by the chapter reader to swap a "← Book"
 * link for a "you are here" label once the title scrolls under the header.
 */
export function elementVisible(
	el: () => HTMLElement | undefined,
	options: ElementVisibleOptions = {}
): ElementVisible {
	let visible = $state(options.initial ?? false);

	$effect(() => {
		const node = el();
		if (!node || typeof IntersectionObserver === 'undefined') return;
		const io = new IntersectionObserver(([e]) => (visible = e.isIntersecting), {
			rootMargin: options.rootMargin
		});
		io.observe(node);
		return () => io.disconnect();
	});

	return {
		get visible() {
			return visible;
		}
	};
}
