import type { IconName } from '$lib/components/Icon.svelte';
import { localizeHref } from '$lib/href';
import { loginHref, withSignup } from '$lib/loginHref';

/**
 * The reader's own pages, in one list for every surface that offers them —
 * the footer's "My Account" column and the phone "More" sheet — so they can't
 * drift (the sheet's first draft already linked signed-out readers somewhere
 * the footer didn't).
 *
 * `signup`: a signed-out reader following Bookshelf / Notebook most likely has
 * no account yet, so /login opens on "create account" and pitches that page
 * beside the form (LoginPitch).
 */
export const ACCOUNT_NAV: { path: string; labelKey: string; icon: IconName; signup: boolean }[] = [
	{ path: '/favorites', labelKey: 'fav.yourFavorites', icon: 'bookmark', signup: true },
	{ path: '/notebook', labelKey: 'notebook.title', icon: 'book', signup: true },
	{ path: '/settings', labelKey: 'account.settings', icon: 'gear', signup: false }
];

/**
 * Signed in, straight to the page; signed out, through /login carrying a
 * redirect to it, so a successful sign-in lands the reader where they asked.
 */
export function accountHref(path: string, signedIn: boolean, signup = false): string {
	const target = localizeHref(path);
	if (signedIn) return target;
	const href = localizeHref(loginHref(target));
	return signup ? withSignup(href) : href;
}
