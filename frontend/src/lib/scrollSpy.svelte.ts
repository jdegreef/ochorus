/**
 * Shared on-page navigation machinery for the long-form reading surfaces.
 *
 * Three pages grew their own "which section am I in" / "jump to a section" code
 * independently — the author sub-nav (a fixed bio/books/sermons/faq set), the
 * sermon page (a dynamic homiletic outline) and the chapter reader (a single
 * "is the title still on screen" flag). This module is the one place that owns:
 *
 *  - `scrollSpy`      — an IntersectionObserver over a (possibly changing) set of
 *                       element ids, exposing whichever one sits in the spy band
 *                       as `active`;
 *  - `elementVisible` — the degenerate single-element case, a reactive boolean;
 *  - `jumpToSection`  — a smooth scroll to an id that lands the target below the
 *                       pinned bars via CSS `scroll-margin-top` (the
 *                       `--pinned-offset` contract), NOT manual `scrollTo` math;
 *  - `spy.jump`       — the sticky sub-nav's click handler (book, author and
 *                       /scripture pages): light the tab, jumpToSection, and
 *                       write `#id` keeping SvelteKit's history state;
 *  - `realignHashOnMeasure` — fix a cold `#id` load that landed under the bar
 *                       before the bar was measured.
 *
 * The landing offset lives in CSS, not here: each surface sets `scroll-margin-top`
 * on its anchors (typically `calc(var(--pinned-offset, …) + 0.5rem)`), so the
 * amount a jump clears is owned by the same variable the sticky bars publish and
 * can never drift from what is actually pinned above the prose.
 */

import { prefersReducedMotion } from './reading';

/**
 * Smooth-scroll to the element with `id`, honouring reduced-motion. The element
 * carries its own `scroll-margin-top`, so `scrollIntoView` lands it below
 * whatever is pinned above the prose — no offset arithmetic here. A caller that
 * wants `#<id>` in the address bar sets it itself; this stays a pure scroll.
 */
export function jumpToSection(id: string): void {
	const el = document.getElementById(id);
	if (!el) return;
	el.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' });
}

/**
 * Track which of a set of sections is currently on screen.
 *
 * `ids` is a getter so a *changing* set works: the sermon outline is built from
 * the rendered body after hydration, and re-reading it here re-observes when it
 * appears or changes. Call this once from a component's `<script>` (it owns an
 * `$effect`, so it must run during component init, like any runes store).
 *
 * `rootMargin` defaults to a thin band around the viewport's vertical middle, so
 * the highlight tracks the section you are actually reading. No-JS / prerender:
 * nothing lights, but the links still jump — the markup and `scroll-margin` do.
 */
export function scrollSpy(ids: () => string[], options: { rootMargin?: string } = {}) {
	const rootMargin = options.rootMargin ?? '-45% 0px -50% 0px';
	let active = $state('');

	$effect(() => {
		if (typeof IntersectionObserver === 'undefined') return;
		const els = ids()
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
		/**
		 * Pre-light a section before the observer catches up — for a jump handler
		 * that wants the tapped link lit at once rather than a frame after the
		 * smooth scroll starts.
		 */
		set(id: string) {
			active = id;
		},
		/**
		 * The sub-nav link's click handler, shared by the book, author and
		 * /scripture jump bars: write `#id` into the address bar, light the tab at
		 * once (unless `track: false`, for a target that isn't a tab, so the bar
		 * isn't left with nothing lit), and smooth-jump.
		 *
		 * `history.state`, never null: a null state erases SvelteKit's history
		 * index on the entry, and Back after the next navigation then changes only
		 * the URL.
		 */
		jump(e: MouseEvent, id: string, { track = true }: { track?: boolean } = {}) {
			// A modified or non-primary click is the reader asking for a new tab or
			// window: leave it to the browser.
			if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
			e.preventDefault();
			if (track) active = id;
			jumpToSection(id);
			// Last, and allowed to fail: Safari throws after ~100 replaceState calls
			// in 30s (and some embedded frames always do). The jump has happened;
			// only the address bar misses this one.
			try {
				history.replaceState(history.state, '', `#${id}`);
			} catch {
				/* the jump already happened */
			}
		}
	};
}

/**
 * Re-land a `#id` target the browser jumped to before the sticky bars had their
 * measured heights. A cold load of `/page/#section` scrolls during parsing, when
 * `--pinned-offset` still reads 0 for the bar (it is measured on hydration), so
 * the heading lands UNDER the bar. Nudges the target only while it sits where
 * that stale jump left it — no lower than its scroll-margin less the bar's
 * height (`barH`), i.e. hidden by the bar or above it. A reader who scrolled
 * the heading to anywhere else (including a spot SvelteKit restores on Back or
 * reload) is never moved.
 */
export function realignHashTarget(barH: number): void {
	let id = '';
	try {
		id = decodeURIComponent(location.hash.slice(1));
	} catch {
		return;
	}
	const el = id ? document.getElementById(id) : null;
	if (!el) return;
	const margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
	const top = el.getBoundingClientRect().top;
	if (top >= -1 && top < margin - 1 && top <= margin - barH + 1) el.scrollIntoView({ block: 'start' });
}

/**
 * Call once from a page with a sticky sub-nav (during component init, like
 * `scrollSpy`): when `measured()` (the bar's bound height) first turns
 * non-zero, wait a frame for `--pinned-offset` to reach layout, then
 * {@link realignHashTarget}.
 */
export function realignHashOnMeasure(measured: () => number): void {
	let frame = 0;
	$effect(() => {
		const barH = measured();
		if (frame || barH <= 0) return;
		frame = requestAnimationFrame(() => realignHashTarget(barH));
	});
	// Only on teardown — a re-measure inside that frame must not cancel it.
	$effect(() => () => cancelAnimationFrame(frame));
}

/**
 * The single-element case of {@link scrollSpy}: watch one element (given as a
 * getter, so a `bind:this` node that arrives after mount is picked up) and
 * expose whether it is on screen. Used by the chapter reader to swap a "← Book"
 * link for a "you are here" label once the title scrolls under the header.
 *
 * `initial` is the value before the observer first reports (it corrects on the
 * next frame) — pass `true` for an element that starts on screen.
 */
export function elementVisible(
	el: () => HTMLElement | undefined,
	options: { rootMargin?: string; initial?: boolean } = {}
) {
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
