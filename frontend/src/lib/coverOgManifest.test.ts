import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { coverLayoutFor, layoutKey, typeTopFor } from './coverLayouts';
import { coverStyleFor, scriptOf, volumeNumeral } from './coverStyles';
import { baseEdition } from './reading-schema';
import { eraOf } from './eras';
import { COVER_CSS_CODE } from '../test/coverCss';
import { isArtCover, isPlateCover, twinUrl } from './coverArt';

/**
 * The other half of the share-card staleness gate.
 *
 * A book's og:image twin is drawn from three things: the ground on disk, the
 * strings over it, and the house style its author's century is set in. The
 * first two are digested into `og-manifest.json` and recomputed by
 * `CoverAssetTests.test_every_twin_was_made_from_the_cover_it_stands_in_for`.
 * That gate is Python and cannot evaluate `coverStyles.ts`, so a digest
 * covering the style would be one it could never reproduce and the build would
 * fail forever.
 *
 * So the style is recorded beside the digest, and checked here, where the table
 * lives. Restyle an author — or move them between eras, or add an override —
 * and this fails until `npm run og:covers` is re-run. Without it, every one of
 * that author's shared links would keep showing the old face while the site
 * showed the new one, and nothing would say so: a share card is only ever seen
 * by someone who is not us.
 *
 * WHY IT DOES NOT IMPORT `needTwins` FROM THE SCRIPT, which would be the
 * obvious way to stop restating how a twin is chosen (and is what
 * `messageCatalogues.test.ts` does with `sync-ui-catalogues.mjs`): importing
 * `generate-cover-og.mjs` from `src/` pulls it into the type-check graph, and
 * it imports `../src/lib/*.ts` by extension — which `svelte-check` rejects
 * without `allowImportingTsExtensions`. That flag is a repo-wide decision about
 * import style, not this gate's to make. So the two DECISIONS that matter are
 * imported (`coverStyleFor` and the tier predicates); only the fixture-reading
 * boilerplate is restated, and a drift there fails the completeness check
 * below rather than passing silently.
 */
/**
 * Read once, not once per assertion.
 *
 * `needTwins()` reads and JSON-parses EVERY book fixture — 158 files, 82 MB —
 * and it was called by three separate tests, as `manifestFile()` and `births()`
 * were by several more. The file spent most of its time re-parsing the whole
 * library, which put it right at vitest's 5s default: it passed alone and timed
 * out under load, an intermittent red that told nobody anything true. Nothing
 * here mutates the fixtures, so one read is the correct number.
 */
function once<T>(read: () => T): () => T {
	let value: T;
	let done = false;
	return () => {
		if (!done) {
			value = read();
			done = true;
		}
		return value;
	};
}

const STATIC = resolve(process.cwd(), 'static');
const CONTENT = resolve(process.cwd(), '..', 'backend', 'library', 'fixtures', 'content');

type Twin = { ground: string; style: string; volume?: string | null; layout?: string };

const manifestText = once(() => readFileSync(join(STATIC, 'covers', 'og-manifest.json'), 'utf8'));
const manifestFile = once(() => JSON.parse(manifestText()));

const manifest = (): Record<string, Twin> => manifestFile().twins;

/** Author slug → birth year, from the shipped fixture. */
const births = once(
	(): Map<string, number | null> =>
		new Map(
			JSON.parse(readFileSync(join(CONTENT, 'authors.json'), 'utf8')).map(
				(r: { fields: { slug: string; birth_year: number | null } }) => [
					r.fields.slug,
					r.fields.birth_year ?? null
				]
			)
		)
);

/**
 * Every EDITION whose cover cannot be its own og:image, keyed the way the
 * manifest keys it, with the style its card should be set in — the same two
 * conditions the script filters on, and the same conditions the Python gate
 * spells out for itself.
 *
 * Every edition, not every English book. A twin carries the TITLE in its
 * pixels, so one card per work served the English title on all 93 translated
 * pages; this gate agreed with the script that that was complete, because both
 * of them only ever looked at `.en.json`.
 */
const needTwins = once(() => {
	const birth = births();
	return readdirSync(join(CONTENT, 'books'))
		.filter((f) => f.endsWith('.json'))
		.flatMap((f) => JSON.parse(readFileSync(join(CONTENT, 'books', f), 'utf8')))
		.filter((row) => row.model === 'library.book')
		.map(
			(row) =>
				row.fields as {
					slug: string;
					language: string;
					author: string[];
					cover_url?: string;
					series_position?: number | null;
				}
		)
		.filter((f) => isArtCover(f.cover_url) || isPlateCover(f.cover_url))
		.map((f) => ({
			// The manifest is keyed by the twin's path without its extension, which
			// `twinUrl` owns — restating it here would be the drift this whole file
			// exists to catch, one directory up.
			key: twinUrl(f.slug, f.language).replace('/covers/', '').replace(/\.png$/, ''),
			style: coverStyleFor(eraOf(birth.get(f.author[0]) ?? null), f.author[0], f.slug),
			volume: volumeNumeral(f.series_position, baseEdition(f.language)),
			layout: (() => {
				const art = isArtCover(f.cover_url);
				const layout = art ? coverLayoutFor(f.author[0], scriptOf(f.language || 'en'), f.slug) : null;
				return layoutKey(layout, art && typeTopFor(f.slug, layout));
			})()
		}));
});

describe('the og twins were drawn with the composition that ships now', () => {
	it('records the stylesheet the cards were drawn with', () => {
		// `ground` digests the cover file and the strings; `style` names the recipe.
		// NEITHER SEES THE DRAWING. A cover's type — its rules, its ornaments, the
		// arrangement its era composes in — is `cover-type.css`, which the script
		// inlines into every card and no digest covered. Edit a `.style-*` block
		// and the committed twins keep the previous composition, indefinitely, with
		// every gate green: the exact defect `generate-cover-og.mjs`'s own header
		// describes as the reason it exists, re-created one layer up.
		//
		// Python could never have closed this — `CoverAssetTests` cannot evaluate a
		// stylesheet — which is why the script's header said only running it would
		// catch a composition change. This gate is JS and reads the file directly.
		//
		// Comments stripped on both sides, matching the writer: this stylesheet is
		// more than half prose, and failing the build over a typo in a docstring is
		// how a gate gets deleted rather than obeyed.
		const drawn = createHash('sha256').update(Buffer.from(COVER_CSS_CODE)).digest('hex');
		expect(
			manifestFile().css,
			'the cover composition changed but the og:image twins did not — every ' +
				'shared link would show the previous design. Run `cd frontend && ' +
				'npm run og:covers`'
		).toBe(drawn);
	});

	it('records the markup the cards were drawn from', () => {
		// The stylesheet only decides how a card looks GIVEN a tree to hang on, and
		// the tree is a second file that moves on its own. `coverCardMarkup.ts` is
		// what the script builds each card from, and a change there — a reordered
		// title and rule, a dropped `script-` class — leaves every committed twin
		// on the old arrangement with `css` unmoved and every other gate green.
		// The same hole as the one above, one file over.
		//
		// NOT comment-stripped, unlike the stylesheet: this is a TypeScript module
		// of about a hundred lines, not a document that is half prose, so digesting
		// it whole costs nothing anyone will resent and needs no parser that could
		// itself be wrong about what a comment is.
		const source = readFileSync(join(process.cwd(), 'src/lib/coverCardMarkup.ts'));
		expect(
			manifestFile().markup,
			'the cover markup changed but the og:image twins did not — every shared ' +
				'link would show the previous tree. Run `cd frontend && npm run og:covers`'
		).toBe(createHash('sha256').update(source).digest('hex'));
	});
});

describe('the og twins were drawn in the style the table names now', () => {
	it('keeps the twins once each, in the order the generator writes them', () => {
		// The generator writes this file sorted, so a run is a stable diff. An
		// entry hand-patched in out of order — a translation adding its card at
		// the end — makes the NEXT person's run re-sort it, and their cover PR
		// arrives carrying a reshuffle of other people's entries that they then
		// have to pick apart by hand. Caught here, at the edit that caused it.
		//
		// Read off the RAW text, not the parsed object: a hand-patch once added
		// `fr/waiting-on-god` a second time, and JSON.parse keeps one silently,
		// so a check on the parsed keys could never see it.
		const keys = [...manifestText().matchAll(/^\t\t"([^"]+)": \{$/gm)].map(([, key]) => key);
		expect(keys.length, 'the twin entries were not found where expected').toBeGreaterThan(0);
		expect(keys, 'og-manifest.json twins are duplicated or out of order — run `npm run og:covers`').toEqual(
			[...new Set(keys)].sort((a, b) => a.localeCompare(b))
		);
	});

	it('records a ground and a style for every twin', () => {
		// A half-written entry would let the checks below pass by skipping.
		const half = Object.entries(manifest())
			.filter(([, twin]) => !twin.ground || !twin.style)
			.map(([slug]) => slug);
		expect(half, 'run `cd frontend && npm run og:covers`').toEqual([]);
	});

	it('covers every edition that needs a twin, and none that does not', () => {
		const recorded = new Set(Object.keys(manifest()));
		const wanted = new Set(needTwins().map((b) => b.key));
		expect(
			[...wanted].filter((key) => !recorded.has(key)),
			'an edition whose cover cannot be its own og:image has no twin recorded — ' +
				'run `npm run og:covers`'
		).toEqual([]);
		expect(
			[...recorded].filter((key) => !wanted.has(key)),
			'a twin for an edition that no longer needs one — it has designed artwork ' +
				'now, or it is gone. Re-run `npm run og:covers` and delete the orphan png.'
		).toEqual([]);
	});

	it('gives every translated edition a card of its own', () => {
		// The gate above would pass on a library that had no translations at all.
		// This is the property that was actually broken: a work with editions in
		// several languages needs a card per EDITION, because the title is in the
		// pixels, and it had one for the whole work.
		const byLanguage = new Map<string, number>();
		for (const key of Object.keys(manifest())) {
			const lang = key.includes('/') ? key.split('/')[0] : 'en';
			byLanguage.set(lang, (byLanguage.get(lang) ?? 0) + 1);
		}
		expect(
			[...byLanguage.keys()].filter((l) => l !== 'en').length,
			'every twin is English, so a shared link to a translated edition would ' +
				'show a card with the English title on it'
		).toBeGreaterThan(0);
	});

	it('agrees with coverStyles for every edition that has a card', () => {
		const recorded = manifest();
		const stale = needTwins()
			.filter((b) => recorded[b.key] && recorded[b.key].style !== b.style)
			.map((b) => `${b.key}: drawn in ${recorded[b.key].style}, now ${b.style}`);
		expect(
			stale,
			'an author was restyled but their share cards were not redrawn — run ' +
				'`cd frontend && npm run og:covers`'
		).toEqual([]);
	});

	it('composes every card in the layout the table names', () => {
		// `coverLayouts.ts` is a table Python cannot read, like the style, so it
		// is recorded beside the digest and checked here. An entry without one
		// predates layouts, and every card drawn then was framed.
		const recorded = manifest();
		const stale = needTwins()
			.filter((b) => recorded[b.key] && (recorded[b.key].layout ?? 'framed') !== b.layout)
			.map((b) => `${b.key}: drawn ${recorded[b.key].layout ?? 'framed'}, now ${b.layout}`);
		expect(
			stale,
			'a work was given a layout but its share cards were not redrawn — run ' +
				'`cd frontend && npm run og:covers`'
		).toEqual([]);
	});

	it('numbers every card as the series table does', () => {
		// The numeral is drawn from a table the other digests never see: `ground`
		// is the file and the strings, `markup` the tree's SHAPE. A book added to
		// a series would otherwise keep a card with no numeral on it.
		const recorded = manifest();
		const stale = needTwins()
			.filter((b) => recorded[b.key] && (recorded[b.key].volume ?? null) !== b.volume)
			.map((b) => `${b.key}: drawn as ${recorded[b.key].volume ?? null}, now ${b.volume}`);
		expect(stale, 'a series changed but its share cards did not — run `npm run og:covers`').toEqual(
			[]
		);
	});
});
