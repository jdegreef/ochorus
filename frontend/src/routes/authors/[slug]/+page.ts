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
//
// Prerender refresh 2026-07-25 (queue job #390): same for the Swahili Amy
// Carmichael biography (PR #433) — /sw/authors/amy-carmichael re-crawls and
// bakes the fresh translated bio once the API ships it.
//
// Prerender refresh 2026-07-25 (queue job #391): same for the Luganda Amy
// Carmichael biography (PR #435) — /lg/authors/amy-carmichael re-crawls and
// bakes the fresh translated bio, completing the es/sw/lg re-translation set.
//
// Prerender refresh 2026-07-25 (queue job #392): the Spanish Andrew Murray
// biography was re-translated from the expanded English source (PR #438) —
// /es/authors/andrew-murray re-crawls and bakes the fresh translated bio.
//
// Prerender refresh 2026-07-25 (queue job #393): same for the Swahili Andrew
// Murray biography (PR #441) — /sw/authors/andrew-murray re-crawls and bakes
// the fresh translated bio.
//
// Prerender refresh 2026-07-25 (queue job #394): same for the Luganda Andrew
// Murray biography (PR #444) — /lg/authors/andrew-murray re-crawls and bakes
// the fresh translated bio, completing the es/sw/lg re-translation set.
//
// Prerender refresh 2026-07-26 (queue job #395): the Spanish Catherine Booth
// biography was re-translated from the expanded English source (PR #450) —
// /es/authors/catherine-booth re-crawls and bakes the fresh translated bio.
//
// Prerender refresh 2026-07-28 (queue jobs #396 + #397): the Swahili (PR #456)
// and Luganda (PR #461) Catherine Booth biographies were re-translated from the
// same expanded English source — /sw/authors/catherine-booth and
// /lg/authors/catherine-booth re-crawl and bake the fresh bios, completing the
// Catherine Booth es/sw/lg re-translation set (one prerender PR for both langs).
//
// Prerender refresh 2026-07-29 (queue job #474): the first Portuguese author
// biography — Andrew Murray — ships (new author_bios_pt/ dir). /pt/authors/
// andrew-murray re-crawls and bakes the translated bio.
//
// Prerender refresh 2026-07-29 (queue job #475): the Portuguese Amanda Berry
// Smith biography ships (PR #505). /pt/authors/amanda-berry-smith re-crawls and
// bakes the translated bio.
//
// Prerender refresh 2026-07-29 (queue job #478): the Portuguese A. B. Simpson
// biography ships (PR #533). /pt/authors/a-b-simpson re-crawls and bakes the
// translated bio.
//
// Prerender refresh 2026-07-30 (queue jobs #398/#401/#404/#407/#410/#512/#513):
// seven Spanish biographies ship (PR #562) — Spurgeon, Meyer, Gareth Evans,
// Hannah Whitall Smith and Jeanne Guyon re-translated from the English expanded
// in #387 (the old files were still the pre-expansion ones, down to 29% of the
// current source for Gareth Evans), plus first-ever Spanish bios for R. A.
// Torrey and Augustine of Hippo. Each /es/authors/<slug> re-crawls and bakes
// the full bio with its prayer callouts.
//
// Prerender refresh 2026-07-30 (queue jobs #400/#403/#406/#409/#412/#413/#511):
// five Luganda biographies re-translated from the English expanded in #387, plus
// first-ever Spanish bios for John Wesley and Jonathan Edwards (PR #565). Each
// /lg/authors/<slug> and /es/authors/<slug> re-crawls and bakes the full bio.
//
// Prerender refresh 2026-07-30 (queue jobs #414/#415): the Swahili and Luganda
// John Wesley bios were each MISSING TWO PARAGRAPHS — the doctrine paragraph on
// grace and Christian perfection, and the works-of-mercy paragraph on prisons,
// schools and medical care for the poor. Word-count alone looked healthy (89% and
// 82%, both in band); only a full ordered TAG-SEQUENCE diff caught it (174 tags
// vs the English 178). Supplied and verified, so /sw/authors/john-wesley and
// /lg/authors/john-wesley re-bake complete.
//
// Prerender refresh 2026-07-30 (queue jobs #399/#402/#405/#408/#411/#569/#575):
// seven Swahili biographies re-translated from the current English (the
// KNOWN_GAPS backlog), clearing the sw bio queue. Worst was gareth-evans, whose
// sw bio had held only a quarter of the English (34 of 86 tags). Each
// /sw/authors/<slug> re-crawls and bakes the full bio with its prayer callouts.
//
// Prerender refresh 2026-07-30 (queue jobs #567/#568/#570/#571/#572/#573/#574/
// #576/#577/#578): the entire remaining KNOWN_GAPS backlog clears — four
// authors re-translated from the current English so their tag sequences match
// it 1:1. Amy Carmichael (es/lg) and Watchman Nee (es/lg) regained dropped
// paragraphs; Susanna Wesley (es/lg/sw) regained the whole "Letters to her
// sons" section (and the sw bio also had "ten children" mistranslated as
// "eight"); William Booth (es/lg/sw) regained the "empty stomach and cold
// feet" blockquote and his one-word last message ("Others"). The bio-markup
// CI gate now runs with an empty allowlist. Each affected /es|lg|sw/authors/
// <slug> re-crawls and bakes the completed bio with its prayer callouts.
export const load: PageLoad = async ({ params }) => {
	const author = await orNotFound(() => getAuthor(params.slug, getLang()));
	// A mid-deploy API (before the sermon fields ship) may omit these; default
	// them so the page renders instead of throwing during prerender.
	return { author: { ...author, sermons: author.sermons ?? [], bio_html: author.bio_html ?? '' } };
};
