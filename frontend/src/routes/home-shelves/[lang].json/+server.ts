/**
 * The home page's shelves for one locale, as a static JSON file written at
 * build time — see `$lib/homeShelves` for why the home page reads a snapshot
 * instead of deriving its shelves from live lists in the browser.
 */
import { error, json } from '@sveltejs/kit';
import { locales } from '$lib/paraglide/runtime';
import { homeShelves } from '$lib/homeShelves';
import type { EntryGenerator } from './$types';

export const prerender = true;

export const entries: EntryGenerator = () => locales.map((lang) => ({ lang }));

export async function GET({ params }) {
	if (!(locales as readonly string[]).includes(params.lang)) {
		error(404, `No home shelves for locale '${params.lang}'.`);
	}
	return json(await homeShelves(params.lang));
}
