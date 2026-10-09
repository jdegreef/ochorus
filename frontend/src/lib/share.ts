import { isCoarsePointer } from '$lib/reading';

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
 *  first row before any click). */
export function hasNativeShare(): boolean {
	return (
		typeof navigator !== 'undefined' &&
		typeof navigator.share === 'function' &&
		!('userAgentData' in navigator && !isCoarsePointer())
	);
}

/** Try the OS share sheet. `aborted` = the reader dismissed it (do nothing);
 *  `unavailable` = no sheet, or it failed for any other reason (show the
 *  fallback targets). */
export async function nativeShare(title: string, url: string): Promise<'shared' | 'aborted' | 'unavailable'> {
	// Not on desktop Chromium (the only engine with `userAgentData`): Chrome
	// and Edge there hand off to a system dialog that often shows nothing —
	// a click that "does nothing". Phones and Safari keep the OS sheet.
	if (!hasNativeShare()) return 'unavailable';
	try {
		await navigator.share({ title, url });
		return 'shared';
	} catch (err) {
		return (err as Error)?.name === 'AbortError' ? 'aborted' : 'unavailable';
	}
}
