import { browser } from '$app/environment';
import { env } from '$env/dynamic/public';

/**
 * Privacy-friendly, cookieless web analytics via Plausible.
 *
 * Env-gated like Sentry (see hooks.client.ts), but injected from the root
 * layout's onMount alongside the other subsystem inits rather than from a
 * client hook: nothing is loaded and no request is made until
 * PUBLIC_PLAUSIBLE_DOMAIN is set, so local dev and any unconfigured deploy ship
 * zero tracking. No cookies, no localStorage, no cross-site identifiers — so
 * this needs no consent banner in the EU/UK.
 *
 * PUBLIC_PLAUSIBLE_DOMAIN — the site's `data-domain`, i.e. the property name you
 *   registered in Plausible (e.g. `ochorus.com`). This is the ON switch.
 * PUBLIC_PLAUSIBLE_SRC — override the script URL for a self-hosted or proxied
 *   instance. Defaults to Plausible Cloud. If you change this to another host,
 *   that host must also be added to `script-src` AND `connect-src` in
 *   render.yaml, or the script won't load / events won't send.
 *
 * We use the standard `script.js`, which fires the first pageview on load and
 * then follows History API (`pushState`) changes — which is how SvelteKit's
 * client router navigates. So every SPA route change is counted with no manual
 * wiring. The event POST goes to `<src origin>/api/event`, whose origin must be
 * in the CSP `connect-src` (and the script URL in `script-src`) — see
 * render.yaml, which owns and documents that hand-maintained host list.
 */

const domain = env.PUBLIC_PLAUSIBLE_DOMAIN?.trim() || '';
const src = env.PUBLIC_PLAUSIBLE_SRC?.trim() || 'https://plausible.io/js/script.js';

/** True only when a Plausible property is configured for this deploy. */
export const ANALYTICS_ENABLED = domain !== '';

let injected = false;

type Plausible = ((event: string, options?: { props?: Record<string, string> }) => void) & {
	q?: unknown[];
};

/**
 * Plausible's own queue stub: calls made before the script loads are kept and
 * replayed by it, so a custom event fired during the first render isn't lost.
 */
function plausible(): Plausible {
	const w = window as unknown as { plausible?: Plausible };
	w.plausible ??= Object.assign(
		(...args: unknown[]) => {
			(w.plausible!.q ??= []).push(args);
		},
		{ q: [] as unknown[] }
	) as Plausible;
	return w.plausible;
}

/**
 * Inject the Plausible script once, in the browser, when configured. Safe to
 * call on every mount: it no-ops when disabled, off the browser, or already in.
 */
export function initAnalytics(): void {
	if (!ANALYTICS_ENABLED || injected || !browser) return;
	injected = true;
	const s = document.createElement('script');
	s.defer = true;
	s.setAttribute('data-domain', domain);
	s.src = src;
	plausible();
	document.head.appendChild(s);
}

/**
 * Send a Plausible custom event. A no-op when analytics is off or off the
 * browser. Props are short labels only — never a URL, an id or anything
 * personal (Plausible stays cookieless and consent-free).
 */
export function track(event: string, props?: Record<string, string>): void {
	if (!ANALYTICS_ENABLED || !browser) return;
	try {
		plausible()(event, props ? { props } : undefined);
	} catch {
		/* analytics must never break the page */
	}
}
