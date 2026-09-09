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
	document.head.appendChild(s);
}
