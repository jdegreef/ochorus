import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { EMBLEM_ART } from './emblems';
import { emblemForSermon } from './emblemNames';

/**
 * The half of a share card's inputs that only JavaScript can see.
 *
 * `SermonShareCardTests` in Python recomputes the strings off the fixture, and
 * stops there because the emblem catalogue is TypeScript. So reassigning a
 * sermon's emblem or editing a drawing would leave those cards stale with the
 * Python gate green — and a share card is only ever seen by someone who is not
 * us.
 *
 * This recomputes the `art` digest `generate-sermon-og.mjs` records. Neither
 * side covers the generator's own composition — its layout, palette and
 * contrast floor are not content, and a redesign is caught by re-running it,
 * not by a digest. A floor, not a proof.
 */
const MANIFEST = join(process.cwd(), 'static', 'og', 'sermons', 'og-manifest.json');
const cards: Record<string, { content: string; art: string }> = JSON.parse(
	readFileSync(MANIFEST, 'utf-8')
).cards;

describe('sermon share cards', () => {
	it('records every sermon it drew', () => {
		expect(Object.keys(cards).length).toBeGreaterThan(0);
	});

	it('was drawn from the art each slug resolves to today', () => {
		const stale = Object.keys(cards).filter((slug) => {
			const emblem = emblemForSermon(slug);
			// Mirrors `artDigest` in generate-sermon-og.mjs: the emblem and its
			// drawing, in that order.
			const blob = [emblem, EMBLEM_ART[emblem]].join('\0');
			return createHash('sha256').update(blob).digest('hex') !== cards[slug].art;
		});
		expect(
			stale,
			'the emblem or its drawing changed but the share card did not — run ' +
				'`cd frontend && npm run og:sermons`'
		).toEqual([]);
	});
});
