/**
 * Locales that ship their OWN localized sermon Open Graph share cards — the
 * emblem, passage and title drawn in that language — instead of forwarding as
 * the English card.
 *
 * STAGED SCAFFOLDING, not a permanent home. The end state is the book-cover
 * twin: `twinUrl(slug, language)` (coverArt.ts) routes every edition's
 * og:image per-language with NO opt-in list, because the content model has no
 * English fallback (CLAUDE.md) — a language with no row shows nothing rather
 * than English. Sermons should get there too. They aren't there yet for two
 * reasons: the card renderer (`og-card.mjs`) is LTR-only, so an RTL locale
 * (ar/he) would render a broken card until it learns direction; and we are
 * rolling localized cards out a language at a time as each is vetted. So this
 * list is the set of locales whose sermon cards are BUILT AND CHECKED — grow it
 * toward "all translated editions", then delete it when sermons adopt the twin.
 *
 * The contract while it exists, load-bearing because a prerendered page cannot
 * test for a file: a locale named here MUST have a card committed for EVERY one
 * of its translated sermons, or that sermon's `og:image` 404s the moment
 * someone forwards the link. `SermonShareCardTests` (Python) and
 * `sermonCards.test.ts` enforce that both ways — completeness and freshness —
 * against the `localized` block of `og-manifest.json` that the generator writes
 * from this same list. Add a locale here, run `cd frontend && npm run
 * og:sermons`, commit the cards and the manifest together.
 */
export const SERMON_OG_LOCALES = ['fr'] as const;

/** Does this content language ship its own sermon share cards (vs the English one)? */
export const hasLocalizedSermonCard = (lang: string): boolean =>
	(SERMON_OG_LOCALES as readonly string[]).includes(lang);
