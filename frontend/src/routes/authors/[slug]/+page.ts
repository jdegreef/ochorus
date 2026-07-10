import { getAuthor, listAuthors, listBooks } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

// Prerender a page for every author who has books or a biography. The slug set
// is the union of book authors and bio'd authors, from the API at build time.
export const entries: EntryGenerator = async () => {
	const [books, authors] = await Promise.all([listBooks('en'), listAuthors()]);
	const slugs = new Set<string>();
	for (const b of books) slugs.add(b.author.slug);
	for (const a of authors) slugs.add(a.slug);
	return [...slugs].map((slug) => ({ slug }));
};

// This page is prerendered per locale, baking the author's bio/bio_html in
// getLang() at build time — so author-bio *content* translations must be live
// on the API before the web build runs, else the localized page bakes English
// and needs a fresh ochorus-web deploy once the API catches up. Author bios are
// currently translated in es, sw and lg (English is the source / fallback).
export const load: PageLoad = async ({ params }) => {
	const author = await orNotFound(() => getAuthor(params.slug, getLang()));
	// A mid-deploy API (before the sermon fields ship) may omit these; default
	// them so the page renders instead of throwing during prerender.
	return { author: { ...author, sermons: author.sermons ?? [], bio_html: author.bio_html ?? '' } };
};
