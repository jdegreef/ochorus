/**
 * An "Ochorus for …" page's snapshot in a language besides English
 * (/for-shelves/fr/<group>.json) — built from that language's own lists, as
 * the English one is from English's ([group].json).
 */
import { error, json } from '@sveltejs/kit';
import { FOR_LOCALES, forLocale } from '$lib/forLinks';
import { FOR_PAGES_BY_LOCALE, forPage } from '$lib/forPages';
import { buildForShelf } from '$lib/forShelves';
import type { EntryGenerator } from './$types';

export const prerender = true;

export const entries: EntryGenerator = () =>
	FOR_LOCALES.filter((l) => l !== 'en').flatMap((locale) =>
		FOR_PAGES_BY_LOCALE[locale].map((p) => ({ locale, group: p.slug }))
	);

export async function GET({ params, fetch }) {
	const locale = forLocale(params.locale);
	const page = locale === 'en' ? undefined : forPage(params.group, locale);
	if (!page) error(404, `No page for '${params.locale}/${params.group}'.`);
	return json(await buildForShelf(page, locale, fetch));
}
