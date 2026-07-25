import { getAuthor, listAuthors, listBooks } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
import type { EntryGenerator, PageLoad } from './$types';

// Trailing-slash canonical -> prerenders to authors/<slug>/index.html, which the
// static host serves as a directory index (see books/[slug] for the full note).
export const trailingSlash = 'always';

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
// Same content-race applies to photo_url: migration 0027 added 5 PD portraits,
// which the web build must re-prerender AFTER the API migration lands — this
// refresh forces that rebuild (Müller/Taylor/Allen/Crowther/Berry Smith). 2026-07-11.
//
// Prerender refresh 2026-07-21 (queue job #270): force a rebuild after the
// Luganda edition of the David Brainerd biography (PR #301) went live, so
// /lg/authors/david-brainerd re-crawls and bakes the translated bio.
//
// Prerender refresh 2026-07-21 (queue job #271): same again after the Luganda
// edition of the Amanda Berry Smith biography (PR #303) went live, so
// /lg/authors/amanda-berry-smith re-crawls and bakes the translated bio.
//
// Prerender refresh 2026-07-25 (queue job #389): the Spanish Amy Carmichael
// biography was re-translated from the expanded English source (PR #431), so
// force a rebuild once the API ships it — /es/authors/amy-carmichael re-crawls
// and bakes the fresh translated bio.
export const load: PageLoad = async ({ params }) => {
	const author = await orNotFound(() => getAuthor(params.slug, getLang()));
	// A mid-deploy API (before the sermon fields ship) may omit these; default
	// them so the page renders instead of throwing during prerender.
	return { author: { ...author, sermons: author.sermons ?? [], bio_html: author.bio_html ?? '' } };
};
