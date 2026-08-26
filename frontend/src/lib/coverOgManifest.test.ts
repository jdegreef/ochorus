import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { coverStyleFor } from './coverStyles';
import { eraOf } from './eras';
import { COVER_CSS_CODE } from '../test/coverCss';
import { isArtCover, isPlateCover } from './coverArt';

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
const STATIC = resolve(process.cwd(), 'static');
const CONTENT = resolve(process.cwd(), '..', 'backend', 'library', 'fixtures', 'content');

type Twin = { ground: string; style: string };

const manifestFile = () =>
	JSON.parse(readFileSync(join(STATIC, 'covers', 'og-manifest.json'), 'utf8'));

const manifest = (): Record<string, Twin> => manifestFile().twins;

/** Author slug → birth year, from the shipped fixture. */
const births = (): Map<string, number | null> =>
	new Map(
		JSON.parse(readFileSync(join(CONTENT, 'authors.json'), 'utf8')).map(
			(r: { fields: { slug: string; birth_year: number | null } }) => [
				r.fields.slug,
				r.fields.birth_year ?? null
			]
		)
	);

/**
 * Every English book whose cover cannot be its own og:image, with the style its
 * card should be set in — the same two conditions the script filters on, and
 * the same conditions the Python gate spells out for itself.
 */
const needTwins = () => {
	const birth = births();
	return readdirSync(join(CONTENT, 'books'))
		.filter((f) => f.endsWith('.en.json'))
		.flatMap((f) => JSON.parse(readFileSync(join(CONTENT, 'books', f), 'utf8')))
		.filter((row) => row.model === 'library.book')
		.map((row) => row.fields as { slug: string; author: string[]; cover_url?: string })
		.filter((f) => isArtCover(f.cover_url) || isPlateCover(f.cover_url))
		.map((f) => ({
			slug: f.slug,
			style: coverStyleFor(eraOf(birth.get(f.author[0]) ?? null), f.author[0])
		}));
};

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
});

describe('the og twins were drawn in the style the table names now', () => {
	it('records a ground and a style for every twin', () => {
		// A half-written entry would let the checks below pass by skipping.
		const half = Object.entries(manifest())
			.filter(([, twin]) => !twin.ground || !twin.style)
			.map(([slug]) => slug);
		expect(half, 'run `cd frontend && npm run og:covers`').toEqual([]);
	});

	it('covers every book that needs a twin, and no book that does not', () => {
		const recorded = new Set(Object.keys(manifest()));
		const wanted = new Set(needTwins().map((b) => b.slug));
		expect(
			[...wanted].filter((slug) => !recorded.has(slug)),
			'a cover that cannot be its own og:image has no twin recorded — run `npm run og:covers`'
		).toEqual([]);
		expect(
			[...recorded].filter((slug) => !wanted.has(slug)),
			'a twin for a book that no longer needs one — it has designed artwork now, ' +
				'or it is gone. Re-run `npm run og:covers` and delete the orphan png.'
		).toEqual([]);
	});

	it('agrees with coverStyles for every book that has one', () => {
		const recorded = manifest();
		const stale = needTwins()
			.filter((b) => recorded[b.slug] && recorded[b.slug].style !== b.style)
			.map((b) => `${b.slug}: drawn in ${recorded[b.slug].style}, now ${b.style}`);
		expect(
			stale,
			'an author was restyled but their share cards were not redrawn — run ' +
				'`cd frontend && npm run og:covers`'
		).toEqual([]);
	});
});
