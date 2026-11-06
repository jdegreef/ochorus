import { browser } from '$app/environment';
import { ANALYTICS_ENABLED, track } from '$lib/analytics';
import { afterLoadWhenIdle } from '$lib/idle';
import type { INPMetricWithAttribution } from 'web-vitals/attribution';
import type { LCPMetric, TTFBMetric } from 'web-vitals';

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
 * It also reports how fast the FIRST page of a visit loaded, as a `Page load`
 * event (see `pageLoadProps`): LCP (when the main content appeared) and TTFB
 * (when the first byte arrived), bucketed, with the route and locale.
 * Plausible adds the country to every event, so this is how to see whether
 * Kampala waits longer than Victoria, and whether an API or CDN change helped.
 * Sampled (LOAD_SAMPLE) because every custom event counts toward Plausible's
 * monthly quota, like a pageview.
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

export const PAGE_LOAD_EVENT = 'Page load';
/** The share of first page loads that report (custom events cost quota). */
export const LOAD_SAMPLE = 0.1;

export type LcpBucket = '<1s' | '1-2.5s' | '2.5-4s' | '4s+';
export type TtfbBucket = '<0.3s' | '0.3-0.8s' | '0.8-1.8s' | '1.8s+';

/** LCP in web.dev's bands (good ≤ 2.5 s, poor > 4 s), with "good" split at 1 s. */
export function lcpBucket(ms: number): LcpBucket {
	if (ms < 1000) return '<1s';
	if (ms <= 2500) return '1-2.5s';
	if (ms <= 4000) return '2.5-4s';
	return '4s+';
}

/** TTFB in web.dev's bands (good ≤ 0.8 s, poor > 1.8 s), with "good" split
 *  at 0.3 s, roughly where an edge cache hit and a trip to the origin part. */
export function ttfbBucket(ms: number): TtfbBucket {
	if (ms < 300) return '<0.3s';
	if (ms <= 800) return '0.3-0.8s';
	if (ms <= 1800) return '0.8-1.8s';
	return '1.8s+';
}

/** Props for the `Page load` event. TTFB is `unknown` when it never arrived. */
export function pageLoadProps(
	lcp: Pick<LCPMetric, 'value'>,
	ttfb: Pick<TTFBMetric, 'value'> | undefined,
	route: string,
	locale: string
): Record<string, string> {
	return {
		route,
		locale,
		lcp: lcpBucket(lcp.value),
		ttfb: ttfb ? ttfbBucket(ttfb.value) : 'unknown'
	};
}

/**
 * Watch the first page load: TTFB arrives early, LCP once it is final (the
 * reader's first input, or the page being hidden). Reports once, for the
 * document's first page view; a client-side navigation has no LCP of its own.
 */
export function watchPageLoad(
	vitals: {
		onLCP: (cb: (m: LCPMetric) => void) => void;
		onTTFB: (cb: (m: TTFBMetric) => void) => void;
	},
	locale: string,
	send: typeof track = track
): void {
	let ttfb: TTFBMetric | undefined;
	let sent = false;
	vitals.onTTFB((m) => (ttfb = m));
	vitals.onLCP((m) => {
		if (sent) return;
		sent = true;
		send(PAGE_LOAD_EVENT, pageLoadProps(m, ttfb, views[0]?.route ?? '(no route)', locale));
	});
}

let started = false;

/** Start observing INP (and, sampled, the first load) after load + idle.
 *  No-op without analytics. */
export function initWebVitals(locale: string): void {
	if (!ANALYTICS_ENABLED || !browser || started) return;
	started = true;
	afterLoadWhenIdle(() => {
		import('web-vitals/attribution')
			.then(({ onINP, onLCP, onTTFB }) => {
				onINP((metric) => reportInp(metric, locale));
				// Both observers are `buffered`, so starting them after idle
				// still sees the load that has already happened.
				if (Math.random() < LOAD_SAMPLE) watchPageLoad({ onLCP, onTTFB }, locale);
			})
			.catch(() => {
				/* measurement must never break the page */
			});
	});
}
