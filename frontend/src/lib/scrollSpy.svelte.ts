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
 *  - `subnavOffset`   — the sub-nav's share of `--pinned-offset`, estimated
 *                       until it is measured so a cold `#id` load lands near;
 *  - `realignHashOnMeasure` — on a cold `#id` load, re-land a target still
 *                       hidden by the bars once they are measured.
 *
 * The landing offset lives in CSS, not here: each surface sets `scroll-margin-top`
 * on its anchors (typically `calc(var(--pinned-offset, …) + 0.5rem)`), so the
 * amount a jump clears is owned by the same variable the sticky bars publish and
 * can never drift from what is actually pinned above the prose.
 */

import { prefersReducedMotion } from './reading';
import { isUnmodifiedPrimaryClick } from './plainClick';

/**
 * Smooth-scroll to the element with `id`, honouring reduced-motion. The element
 * carries its own `scroll-margin-top`, so `scrollIntoView` lands it below
 * whatever is pinned above the prose — no offset arithmetic here. A caller that
 * wants `#<id>` in the address bar sets it itself; this stays a pure scroll.
 */
export function jumpToSection(id: string): void {
	const el = document.getElementById(id);
	if (!el) return;
	const smooth = !prefersReducedMotion();
	el.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' });
	relandAfterJump(el, smooth);
}

/**
 * A smooth jump aims at where the target was when it started. Sections that
 * skip rendering until they near the viewport (`content-visibility: auto`, the
 * author page's shelves) take their real height as the scroll passes them, so
 * a target BELOW them — the author page's biography, after its books and
 * sermons — moved while the page was on its way, and the jump stopped short
 * (measured: ~340px, the biography heading mid-screen). Once the scroll has
 * settled, land it again, instantly; unless the reader took over the scroll
 * in the meantime, which is theirs to keep.
 */
let cancelReland: (() => void) | undefined;

function relandAfterJump(el: HTMLElement, smooth: boolean): void {
	// A newer jump supersedes an older one still settling: its listener must
	// not fire on the new scroll's end and pull the page back.
	cancelReland?.();
	let taken = false;
	const take = () => (taken = true);
	const userInput = ['wheel', 'touchstart', 'keydown', 'pointerdown'] as const;
	for (const t of userInput) window.addEventListener(t, take, { once: true, passive: true });
	const cancel = () => {
		clearTimeout(timer);
		window.removeEventListener('scrollend', settle);
		for (const t of userInput) window.removeEventListener(t, take);
		if (cancelReland === cancel) cancelReland = undefined;
	};
	const settle = () => {
		cancel();
		if (taken) return;
		const margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
		if (Math.abs(el.getBoundingClientRect().top - margin) > 2) el.scrollIntoView({ block: 'start' });
	};
	// `scrollend` where the browser has it; a timeout past any smooth scroll
	// where it does not (and as a backstop if no scroll happened at all).
	window.addEventListener('scrollend', settle);
	const timer = setTimeout(settle, smooth ? 1200 : 50);
	cancelReland = cancel;
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
 *
 * `line` (0–1, a share of the viewport's height from its top): the ids name a
 * section's HEADING — a point in the text — not a box holding the whole
 * section, so the band test is the wrong question. A heading crosses the band
 * on its way back down too, and "last intersecting wins" then lit the section
 * BELOW the one being read on every scroll up; a jump or a fast scroll could
 * also carry a heading clean over a thin band with no crossing reported at
 * all. With `line`, the observed region is everything ABOVE the reading line
 * (its top margin reaches far past the page's top), so a heading intersects
 * exactly while its top is above the line, whatever the speed it got there,
 * and the section is the last such heading in document order ('' above the
 * first) — read from the observer's own reports, no layout reads.
 *
 * A section lit by `set` or `jump` is HELD until that jump's scroll ends: the
 * smooth scroll sweeps other sections past the band or the line on its way,
 * and a short section's next heading can sit above the line where the target
 * lands — either would light a section the reader did not choose.
 */
export function scrollSpy(
	ids: () => string[],
	options: { rootMargin?: string; line?: never } | { line: number; rootMargin?: never } = {}
) {
	const { line } = options;
	const rootMargin =
		line != null
			? `${MARKER_REACH_PX}px 0px ${-Math.round((1 - line) * 100)}% 0px`
			: (options.rootMargin ?? '-45% 0px -50% 0px');
	let active = $state('');

	// The jump hold: released by the jump's `scrollend`, or after HOLD_MS where
	// there is no such event (or no scroll — the target was already in place).
	let held = false;
	let holdTimer: ReturnType<typeof setTimeout> | undefined;
	const release = () => {
		held = false;
		clearTimeout(holdTimer);
		window.removeEventListener('scrollend', release);
	};
	function hold(id: string) {
		active = id;
		release();
		held = true;
		holdTimer = setTimeout(release, HOLD_MS);
		// Added after the jump starts, so a scroll already ending can't release it.
		requestAnimationFrame(() => held && window.addEventListener('scrollend', release, { once: true }));
	}
	$effect(() => release);

	$effect(() => {
		if (typeof IntersectionObserver === 'undefined') return;
		const els = ids()
			.map((id) => document.getElementById(id))
			.filter((el): el is HTMLElement => el != null);
		if (!els.length) return;
		// `line` mode: the anchors above the line, as last reported.
		const above = new Set<Element>();
		const io = new IntersectionObserver(
			(entries) => {
				if (line != null) {
					for (const e of entries) {
						if (e.isIntersecting) above.add(e.target);
						else above.delete(e.target);
					}
					if (!held) active = els.findLast((el) => above.has(el))?.id ?? '';
					return;
				}
				if (held) return;
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
		 * Light a section a jump handler is scrolling to: at once rather than a
		 * frame after the smooth scroll starts, and held until it ends (above).
		 */
		set(id: string) {
			hold(id);
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
			// window: leave it to the browser. (Deliberately not isPlainPrimaryClick:
			// this has never deferred to an earlier handler's preventDefault.)
			if (!isUnmodifiedPrimaryClick(e)) return;
			e.preventDefault();
			if (track) hold(id);
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

/** How far above the viewport `scrollSpy`'s `line` region reaches: past the
 *  top of any page, so a heading above the line is always inside it. */
const MARKER_REACH_PX = 1_000_000;

/** The longest a jump holds its section where no `scrollend` arrives. */
export const HOLD_MS = 1500;

/** The sticky sub-nav's height before it is measured: one row of
 *  `.subnav-link` tabs (measured 44.6px at every width). The prerendered page
 *  publishes it, so the browser's own cold `#id` jump already clears a bar of
 *  about this size. */
export const SUBNAV_H_EST = 44;

/** The sub-nav's share of `--pinned-offset`: its measured height, the estimate
 *  while it is shown but not yet measured, and 0 when there is none. */
export const subnavOffset = (shown: boolean, measured: number): number =>
	measured || (shown ? SUBNAV_H_EST : 0);

/**
 * Re-land the `#id` target if it sits hidden behind the pinned bars. Its own
 * `scroll-margin-top` is the bars' height plus the 0.5rem the anchors add
 * (`calc(var(--pinned-offset) + 0.5rem)`), read now, so it is the measured
 * figure; a target whose top is above that line but still on screen is under
 * the bars. One that is lower, or scrolled off the top, is left alone.
 */
export function realignHashTarget(): void {
	let id = '';
	try {
		id = decodeURIComponent(location.hash.slice(1));
	} catch {
		return;
	}
	const el = id ? document.getElementById(id) : null;
	if (!el) return;
	const margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
	const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
	const top = el.getBoundingClientRect().top;
	if (top >= -1 && top < margin - rem / 2 - 1) el.scrollIntoView({ block: 'start' });
}

const navigationType = (): string => {
	try {
		const [entry] = performance.getEntriesByType('navigation') as PerformanceNavigationTiming[];
		return entry?.type ?? 'navigate';
	} catch {
		return 'navigate';
	}
};

/** Whether the next page to call {@link realignHashOnMeasure} is the one the
 *  document loaded with. */
let firstPage = true;
/** Tests only: treat the next page as the one the document loaded with. */
export const resetFirstPage = (): void => {
	firstPage = true;
};

/**
 * Call once from a page with a sticky sub-nav (during component init, like
 * `scrollSpy`). On a cold `/page/#section` load the browser jumps while parsing,
 * against estimated bar heights (`subnavOffset`, `.app-root` in app.css); when
 * `measured()` (the bar's bound height) first turns non-zero, wait a frame for
 * `--pinned-offset` to reach layout, then {@link realignHashTarget}.
 *
 * Only for the page a fresh load hydrates: a client-side navigation already
 * lands against the measured nav and the sub-nav estimate, and a reload or Back
 * restores a scroll position the reader chose, which is never moved.
 */
export function realignHashOnMeasure(measured: () => number): void {
	if (typeof window === 'undefined') return;
	const cold = firstPage && navigationType() === 'navigate';
	firstPage = false;
	if (!cold) return;
	let frame = 0;
	$effect(() => {
		if (frame || measured() <= 0) return;
		frame = requestAnimationFrame(realignHashTarget);
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
