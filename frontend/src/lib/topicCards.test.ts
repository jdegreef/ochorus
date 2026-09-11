import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { EMBLEM_ART } from './emblems';
import { TOPIC_META, topicMeta } from './emblemNames';

/**
 * The halves of a topic share card's inputs that only JavaScript can see.
 *
 * `TopicShareCardTests` in Python recomputes the strings off `topic_seed.py`
 * (title, description, scripture) and stops there, because the emblem catalogue
 * and the drawing code are TypeScript/JS. So re-accenting a topic, swapping its
 * emblem, or restyling the card itself would leave cards stale with the Python
 * gate green — and a share card is only ever seen by someone who is not us.
 *
 * INPUTS, not output: nothing here re-derives a PNG, so a change in satori or
 * resvg is invisible. A floor, not a proof.
 */
const OG = join(process.cwd(), 'static', 'og', 'topics');
const SCRIPTS = join(process.cwd(), 'scripts');

const manifest: {
	composition: string;
	cards: Record<string, { content: string; art: string }>;
} = JSON.parse(readFileSync(join(OG, 'og-manifest.json'), 'utf-8'));

const sha = (s: string) => createHash('sha256').update(s).digest('hex');
const RERUN = 'run `cd frontend && npm run og:topics`';

describe('topic share cards', () => {
	it('records every curated topic, and only those', () => {
		// Completeness is split deliberately: Python owns "a topic with no card"
		// (it reads topic_seed.py), and this owns "a manifest entry no longer in
		// the catalogue", which nothing else would notice.
		expect(Object.keys(manifest.cards).sort(), RERUN).toEqual(Object.keys(TOPIC_META).sort());
	});

	it('was drawn from the emblem and accent each topic wears today', () => {
		const stale = Object.keys(manifest.cards).filter((slug) => {
			const { emblem, accent } = topicMeta(slug);
			// Mirrors `artDigest` in generate-topic-og.mjs — the CURATED accent, as
			// stored, not the contrast-lifted value the card ends up drawing with.
			return sha([emblem, EMBLEM_ART[emblem], accent].join('\0')) !== manifest.cards[slug].art;
		});
		expect(
			stale,
			`a topic's emblem or curated accent changed but the card did not — ${RERUN}`
		).toEqual([]);
	});

	it('was drawn by the drawing code as it stands', () => {
		const blob = ['generate-topic-og.mjs', 'og-card.mjs']
			.map((f) => readFileSync(join(SCRIPTS, f), 'utf-8'))
			.join('\0');
		expect(
			sha(blob),
			`the card generator changed but the cards were not redrawn — ${RERUN}`
		).toBe(manifest.composition);
	});
});
