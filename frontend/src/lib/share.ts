import { canShare, share } from '$lib/platform';

/**
 * Sharing a page, in one place — ShareButton and the readers' "⋯" menus both
 * use it, so a fix (a new service, a link detail) lands everywhere at once.
 */

export type ShareLink = { name: string; href: string; newTab: boolean };

/** The fallback targets where there's no OS share sheet. WhatsApp leads,
 *  because that is how this content travels. Email is a `mailto:` handed to
 *  the mail client — opening it in a new tab leaves a blank tab behind. */
export function shareLinks(title: string, url: string, emailLabel: string): ShareLink[] {
	const enc = encodeURIComponent;
	return [
		{ name: 'WhatsApp', href: `https://wa.me/?text=${enc(`${title} ${url}`)}`, newTab: true },
		{ name: 'Facebook', href: `https://www.facebook.com/sharer/sharer.php?u=${enc(url)}`, newTab: true },
		{ name: emailLabel, href: `mailto:?subject=${enc(title)}&body=${enc(`${title}\n\n${url}`)}`, newTab: false }
	];
}

/** A whole MESSAGE (its link inside it) rather than a page: WhatsApp takes
 *  it as the text, email as the body under `subject`. The "Ochorus for"
 *  pages' pass-it-on kit. */
export function messageShareLinks(subject: string, message: string, emailLabel: string): ShareLink[] {
	const enc = encodeURIComponent;
	return [
		{ name: 'WhatsApp', href: `https://wa.me/?text=${enc(message)}`, newTab: true },
		{ name: emailLabel, href: `mailto:?subject=${enc(subject)}&body=${enc(message)}`, newTab: false }
	];
}

/** Whether `nativeShare` will try the OS sheet here (decides the menu's
 *  first row before any click): always in the app, and in a browser whose
 *  sheet works ($lib/platform `canShare`, which leaves out desktop Chromium). */
export const hasNativeShare = canShare;

/** Try the OS share sheet. `aborted` = the reader dismissed it (do nothing);
 *  `unavailable` = no sheet, or it failed for any other reason (show the
 *  fallback targets). */
export async function nativeShare(title: string, url: string): Promise<'shared' | 'aborted' | 'unavailable'> {
	return share({ title, url });
}
