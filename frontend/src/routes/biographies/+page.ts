import { listAuthors } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// This page is prerendered per locale, baking whatever bios the API returns for
// getLang() at build time. So author-bio *content* translations must be live on
// the API before the web build runs — otherwise the localized page bakes English
// and needs a fresh ochorus-web deploy once the API catches up.
export const load: PageLoad = async () => {
	const authors = await listAuthors(getLang());
	return { authors };
};

// Biographies book counts are locale-aware (server-side) and prerendered per
// locale; a backend-only change to the count needs a web rebuild to refresh
// the static pages.
