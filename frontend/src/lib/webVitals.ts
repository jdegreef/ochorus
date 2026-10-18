import { browser } from '$app/environment';
import { ANALYTICS_ENABLED, track } from '$lib/analytics';
import { afterLoadWhenIdle } from '$lib/idle';
import type { INPMetricWithAttribution } from 'web-vitals/attribution';

/**
 * Field INP attribution: which tap is slow on real readers' phones.
 *
 * Search Console only says "INP poor" for a URL group; it can't say which
 * control, on which page, or which phase of the interaction was slow. This
 * reports the page view's INP interaction to Plausible as a `Slow tap` custom
 * event when it is over 200 ms ("needs improvement" or worse), with short,
 * non-personal labels only: the canonical ROUTE id (`/authors/[slug]`, never a
 * URL or query), the locale, a bucket rather than the exact ms, the
 * interaction type, a scrubbed CSS selector (tag/id/class names, never text),
 * and the longest phase.
 *
 * Cost at load: nothing. Google's `web-vitals/attribution` build (~4 KB gz) is
 * dynamically imported after load + idle; its observer is `buffered`, so a slow
 * tap before then is still seen. It reports when the page is hidden. Off with
 * analytics (local dev, tests, the phone app — no PUBLIC_PLAUSIBLE_DOMAIN).
 */

export const SLOW_TAP_EVENT = 'Slow tap';
/** web.dev's "good" INP ceiling; only interactions above it are reported. */
export const SLOW_TAP_MS = 200;

export type InpBucket = '200-300' | '300-500' | '500+';
export type InpPhase = 'input delay' | 'processing' | 'presentation delay';

/** Coarse bucket for an INP value, or null when it is not slow enough to report. */
export function inpBucket(ms: number): InpBucket | null {
	if (!(ms > SLOW_TAP_MS)) return null;
	if (ms <= 300) return '200-300';
	if (ms <= 500) return '300-500';
	return '500+';
}

/** Which of the three INP phases took longest (ties go to the earlier phase). */
export function longestPhase(a: {
	inputDelay: number;
	processingDuration: number;
	presentationDelay: number;
}): InpPhase {
	const phases: [InpPhase, number][] = [
		['input delay', a.inputDelay],
		['processing', a.processingDuration],
		['presentation delay', a.presentationDelay]
	];
	return phases.reduce((best, p) => (p[1] > best[1] ? p : best))[0];
}

const MAX_SELECTOR = 80;

/**
 * web-vitals' selector is tag/#id/.class names up the tree — no text — but an
 * id or class can still carry a number or a hash (`#note-8812`, a Svelte scope
 * class). Drop scope classes, mask digits and long hex runs, and cap the length.
 */
export function scrubSelector(selector: string | undefined): string {
	if (!selector) return '(removed)';
	const clean = selector
		.replace(/\.svelte-[a-z0-9]+/gi, '')
		.replace(/[0-9a-f]{8,}(?:-[0-9a-f]{4,})*/gi, '*')
		.replace(/\d+/g, 'N');
	return clean.length > MAX_SELECTOR ? '…' + clean.slice(-(MAX_SELECTOR - 1)) : clean;
}

/** Props for the `Slow tap` event, or null when the interaction wasn't slow. */
export function slowTapProps(
	metric: Pick<INPMetricWithAttribution, 'value' | 'attribution'>,
	route: string,
	locale: string
): Record<string, string> | null {
	const bucket = inpBucket(metric.value);
	if (!bucket) return null;
	const a = metric.attribution;
	return {
		route,
		locale,
		inp: bucket,
		type: a.interactionType ?? 'unknown',
		target: scrubSelector(a.interactionTarget),
		phase: longestPhase(a)
	};
}

/**
 * Page views in this document, by start time — so an interaction is credited
 * to the page it happened ON (a tap on a link belongs to the page it was
 * tapped on, not the one it opened), and each view reports at most once.
 */
type View = { at: number; route: string; index: number };
const views: View[] = [];
const reported = new Set<number>();

/** Record a page view (call from afterNavigate, which also runs on hydration). */
export function notePageView(routeId: string | null | undefined, at = performance.now()): void {
	views.push({ at, route: routeId ?? '(no route)', index: views.length });
}

/** The page view that was showing at `time`. */
export function viewAt(time: number | undefined): View | undefined {
	if (time === undefined) return views.at(-1);
	let found = views[0];
	for (const v of views) if (v.at <= time) found = v;
	return found;
}

/** Turn an INP report into at most one `Slow tap` event per page view. */
export function reportInp(
	metric: Pick<INPMetricWithAttribution, 'value' | 'attribution'>,
	locale: string,
	send: typeof track = track
): void {
	const view = viewAt(metric.attribution.interactionTime);
	if (!view || reported.has(view.index)) return;
	const props = slowTapProps(metric, view.route, locale);
	if (!props) return;
	reported.add(view.index);
	send(SLOW_TAP_EVENT, props);
}

/** Test hook: forget the page views and reports. */
export function resetWebVitals(): void {
	views.length = 0;
	reported.clear();
}

let started = false;

/** Start observing INP after load + idle. No-op without analytics. */
export function initWebVitals(locale: string): void {
	if (!ANALYTICS_ENABLED || !browser || started) return;
	started = true;
	afterLoadWhenIdle(() => {
		import('web-vitals/attribution')
			.then(({ onINP }) => onINP((metric) => reportInp(metric, locale)))
			.catch(() => {
				/* measurement must never break the page */
			});
	});
}
