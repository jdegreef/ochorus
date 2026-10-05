/**
 * When to offer "Add Ochorus to your home screen", and how (pure, tested).
 *
 * Ochorus is a full installable app (manifest, service worker, offline
 * books), but the site never offered to install. Installed readers come back,
 * and a returning reader is who signs up — so this is a retention prompt.
 *
 * Rules: never on the first visit; never once installed or running as the
 * app; "Not now" hides it for 30 days. The platform decides the offer:
 * Android Chrome has a real install dialog (beforeinstallprompt), iPhone
 * Safari needs two taps explained, and an in-app browser (WhatsApp,
 * Facebook, Instagram — how links travel in East Africa) can't install at
 * all, so it's told to open the page in the browser instead.
 */

export type InstallPlatform = 'native' | 'ios' | 'inapp-android' | 'inapp-ios' | 'none';

export interface InstallState {
	/** Visits so far on this device (a gap of 30 min starts a new one). */
	visits: number;
	lastSeen: number;
	snoozedUntil: number;
	installed: boolean;
	/** Arrived via "Open in Chrome": the reader already asked to install. */
	requested?: boolean;
}

export const NEW_VISIT_GAP_MS = 30 * 60 * 1000;
export const SNOOZE_MS = 30 * 24 * 60 * 60 * 1000;
export const MIN_VISITS = 2;

export const EMPTY: InstallState = { visits: 0, lastSeen: 0, snoozedUntil: 0, installed: false };

/** Record this page view; a new visit after 30 minutes away. */
export function noteVisit(s: InstallState, now: number): InstallState {
	const isNew = !s.lastSeen || now - s.lastSeen >= NEW_VISIT_GAP_MS;
	return { ...s, visits: s.visits + (isNew ? 1 : 0), lastSeen: now };
}

/** What a browser user agent can do about installing. */
export function platformFor(ua: string, canPromptNatively: boolean): InstallPlatform {
	const ios = /iPhone|iPad|iPod/.test(ua);
	if (/FBAN|FBAV|FB_IAB|Instagram|Line\/|WhatsApp|; wv\)/i.test(ua)) {
		return ios ? 'inapp-ios' : 'inapp-android';
	}
	if (canPromptNatively) return 'native';
	// Every iOS browser can Share → Add to Home Screen since iOS 16.4 (Safari,
	// Chrome, Edge, Firefox alike); only in-app views (above) can't.
	if (ios && /Safari\//.test(ua)) return 'ios';
	return 'none';
}

/** The query flag "Open in Chrome" carries: the reader asked to install, so
 *  the visit rule (and Chrome's fresh, empty storage) doesn't apply. */
export const INSTALL_PARAM = 'install';

export function shouldOffer(
	s: InstallState,
	platform: InstallPlatform,
	standalone: boolean,
	now: number
): boolean {
	if (standalone || s.installed || platform === 'none') return false;
	if (s.visits < MIN_VISITS && !s.requested) return false;
	return now >= s.snoozedUntil;
}

export const snooze = (s: InstallState, now: number): InstallState => ({
	...s,
	snoozedUntil: now + SNOOZE_MS
});

/** Android only: the same page in Chrome, from inside another app's browser. */
export function chromeIntentUrl(href: string): string | null {
	try {
		const u = new URL(href);
		u.searchParams.set(INSTALL_PARAM, '1');
		// Without Chrome (some Android builds), fall back to the plain page.
		const fallback = encodeURIComponent(u.href);
		return `intent://${u.host}${u.pathname}${u.search}#Intent;scheme=https;package=com.android.chrome;S.browser_fallback_url=${fallback};end`;
	} catch {
		return null;
	}
}
