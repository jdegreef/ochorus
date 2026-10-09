import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { EMBLEM_ART } from './emblems';
import { FOR_META } from './emblemNames';
import { FOR_INDEX_CARD, FOR_LINKS, type ForLinkDest } from './forLinks';

/**
 * The "Ochorus for …" share cards (scripts/generate-for-og.mjs) are drawn from
 * TypeScript alone — FOR_LINKS' label and tagline, FOR_META's accent and
 * emblem — so this one gate recomputes every input, the topic cards' pattern
 * (topicCards.test.ts) without a Python half.
 *
 * INPUTS, not output: nothing here re-derives a PNG. A floor, not a proof.
 */
const OG = join(process.cwd(), 'static', 'og', 'for');
const SCRIPTS = join(process.cwd(), 'scripts');

const manifest: { composition: string; cards: Record<string, string> } = JSON.parse(
	readFileSync(join(OG, 'og-manifest.json'), 'utf-8')
);

const sha = (s: string) => createHash('sha256').update(s).digest('hex');
const RERUN = 'run `cd frontend && npm run og:for`';

// Mirrors `groupDigest` / `indexDigest` in generate-for-og.mjs.
const groupDigest = (l: ForLinkDest) => {
	const { accent, emblem } = FOR_META[l.slug];
	return sha([l.label, l.tagline, emblem, EMBLEM_ART[emblem], accent].join('\0'));
};
const indexDigest = () =>
	sha(
		[FOR_INDEX_CARD.eyebrow, FOR_INDEX_CARD.title, FOR_INDEX_CARD.tagline, ...FOR_LINKS.map(groupDigest)].join(
			'\0'
		)
	);

describe('"Ochorus for" share cards', () => {
	it('gives every group an identity, and nothing else one', () => {
		expect(Object.keys(FOR_META).sort()).toEqual(FOR_LINKS.map((l) => l.slug).sort());
	});

	it('has a card per group and one for the index, each on disk', () => {
		const names = [...FOR_LINKS.map((l) => l.slug), 'index'];
		expect(Object.keys(manifest.cards).sort(), RERUN).toEqual(names.sort());
		for (const n of names) expect(existsSync(join(OG, `${n}.png`)), `og/for/${n}.png — ${RERUN}`).toBe(true);
	});

	it('was drawn from the words and art each group has today', () => {
		const stale = FOR_LINKS.filter((l) => manifest.cards[l.slug] !== groupDigest(l)).map((l) => l.slug);
		if (manifest.cards.index !== indexDigest()) stale.push('index');
		expect(stale, `a label, tagline, accent or emblem changed but its card did not — ${RERUN}`).toEqual([]);
	});

	it('was drawn by the drawing code as it stands', () => {
		const blob = ['generate-for-og.mjs', 'og-card.mjs'].map((f) => readFileSync(join(SCRIPTS, f), 'utf-8')).join('\0');
		expect(sha(blob), `the card generator changed but the cards were not redrawn — ${RERUN}`).toBe(
			manifest.composition
		);
	});
});
