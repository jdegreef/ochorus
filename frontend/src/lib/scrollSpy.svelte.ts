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
 *                       `--pinned-offset` contract), NOT manual `scrollTo` math.
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
		}
	};
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
