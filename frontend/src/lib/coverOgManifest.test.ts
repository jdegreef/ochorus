import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { coverStyleFor } from './coverStyles';
import { eraOf } from './eras';

/**
 * The other half of the share-card staleness gate.
 *
 * A book's og:image twin is drawn from three things: the ground on disk, the
 * strings over it, and the house style its author's century is set in. The
 * first two are digested into `og-manifest.json` and recomputed by
 * `CoverAssetTests.test_every_twin_was_made_from_the_cover_it_stands_in_for`.
 * That gate is Python and cannot read `coverStyles.ts` — the API image has
 * rootDir `backend/` — so a digest covering the style would be one it could
 * never reproduce, and the build would fail forever.
 *
 * So the style is recorded beside the digest, and checked here, where the table
 * actually lives. Restyle an author — or move them between eras, or add an
 * override — and this fails until `npm run og:covers` is re-run. Without it,
 * every one of that author's shared links would keep showing the old face while
 * the site showed the new one, and nothing would say so: a share card is only
 * ever seen by someone who is not us.
 */
const STATIC = resolve(process.cwd(), 'static');
const CONTENT = resolve(process.cwd(), '..', 'backend', 'library', 'fixtures', 'content');

type Twin = { ground: string; style: string };

const manifest = (): Record<string, Twin> =>
	JSON.parse(readFileSync(join(STATIC, 'covers', 'og-manifest.json'), 'utf8')).twins;

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

/** Every English book row, which is the only edition a twin is made for. */
const englishBooks = () =>
	readdirSync(join(CONTENT, 'books'))
		.filter((f) => f.endsWith('.en.json'))
		.flatMap((f) => JSON.parse(readFileSync(join(CONTENT, 'books', f), 'utf8')))
		.filter((row) => row.model === 'library.book')
		.map((row) => row.fields as { slug: string; author: string[]; cover_url?: string });

describe('the og twins were drawn in the style the table names now', () => {
	it('records a style for every twin it records a digest for', () => {
		// A half-written entry would let the check below pass by skipping.
		const half = Object.entries(manifest())
			.filter(([, twin]) => !twin.ground || !twin.style)
			.map(([slug]) => slug);
		expect(half, 'run `cd frontend && npm run og:covers`').toEqual([]);
	});

	it('agrees with coverStyles for every book that has one', () => {
		const recorded = manifest();
		const birth = births();
		const stale = englishBooks()
			.filter((b) => recorded[b.slug])
			.map((b) => ({
				slug: b.slug,
				was: recorded[b.slug].style,
				now: coverStyleFor(eraOf(birth.get(b.author[0]) ?? null), b.author[0]).id
			}))
			.filter((b) => b.was !== b.now)
			.map((b) => `${b.slug}: drawn in ${b.was}, now ${b.now}`);
		expect(
			stale,
			'an author was restyled but their share cards were not redrawn — run ' +
				'`cd frontend && npm run og:covers`'
		).toEqual([]);
	});
});
