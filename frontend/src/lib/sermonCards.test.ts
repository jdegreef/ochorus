import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { EMBLEM_ART, emblemHue } from './emblems';
import { emblemForSermon } from './emblemNames';
import { SERMON_OG_LOCALES } from './sermonOgLocales';

/**
 * The halves of a share card's inputs that only JavaScript can see.
 *
 * `SermonShareCardTests` in Python recomputes the strings off the fixture and
 * stops there, because the emblem catalogue and the drawing code are both
 * TypeScript/JS. So reassigning a sermon's emblem, editing a drawing, moving
 * the catalogue's saturation floor, or restyling the card itself would leave
 * cards stale with the Python gate green — and a share card is only ever seen
 * by someone who is not us.
 *
 * The line the digests draw is INPUTS, not output: nothing here re-derives a
 * PNG, so a change in satori or resvg is still invisible. A floor, not a proof.
 */
const OG = join(process.cwd(), 'static', 'og', 'sermons');
const SCRIPTS = join(process.cwd(), 'scripts');
const FIXTURES = join(process.cwd(), '..', 'backend', 'library', 'fixtures', 'content', 'sermons');

const manifest: {
	composition: string;
	cards: Record<string, { content: string; art: string }>;
	localized?: Record<string, Record<string, { content: string; art: string }>>;
} = JSON.parse(readFileSync(join(OG, 'og-manifest.json'), 'utf-8'));

const sha = (s: string) => createHash('sha256').update(s).digest('hex');

/** Slugs of every sermon translated into `lang`, from the fixtures. */
const slugsFor = (lang: string): string[] =>
	readdirSync(FIXTURES)
		.filter((f) => f.endsWith(`.${lang}.json`))
		.flatMap((f) => JSON.parse(readFileSync(join(FIXTURES, f), 'utf-8')))
		.filter((row) => row.model === 'library.sermon')
		.map((row) => row.fields.slug as string);

const RERUN = 'run `cd frontend && npm run og:sermons`';

describe('sermon share cards', () => {
	it('records every English sermon, and only those', () => {
		// Completeness is checked on both sides deliberately: Python owns "a sermon
		// with no card", and this owns "a manifest entry for a sermon that is gone",
		// which nothing else would notice.
		expect(Object.keys(manifest.cards).sort(), RERUN).toEqual(slugsFor('en').sort());
	});

	it('was drawn from the art each slug resolves to today', () => {
		const stale = Object.keys(manifest.cards).filter((slug) => {
			const emblem = emblemForSermon(slug);
			// Mirrors `artDigest` in generate-sermon-og.mjs.
			const blob = [emblem, EMBLEM_ART[emblem], emblemHue(emblem)].join('\0');
			return sha(blob) !== manifest.cards[slug].art;
		});
		expect(
			stale,
			`the emblem, its drawing or its hue changed but the card did not — ${RERUN}`
		).toEqual([]);
	});

	it('was drawn by the drawing code as it stands', () => {
		// The failure this whole gate exists for was a DESIGN change nobody
		// redrew for: editing the palette in og-card.mjs restyles all 29 cards
		// while every content digest still agrees.
		const blob = ['generate-sermon-og.mjs', 'og-card.mjs']
			.map((f) => readFileSync(join(SCRIPTS, f), 'utf-8'))
			.join('\0');
		expect(
			sha(blob),
			`the card generator changed but the cards were not redrawn — ${RERUN}`
		).toBe(manifest.composition);
	});
});

describe('localized sermon share cards', () => {
	const localized = manifest.localized ?? {};

	it('carries exactly the locales that opt into their own cards', () => {
		// The frontend page reads SERMON_OG_LOCALES to decide whether to point a
		// sermon's og:image at its localized card. If the manifest names a
		// different set, a page would either reference a card that was never drawn
		// (404) or ignore one that was — so the two lists must agree.
		expect(Object.keys(localized).sort(), RERUN).toEqual([...SERMON_OG_LOCALES].sort());
	});

	for (const lang of SERMON_OG_LOCALES) {
		it(`records every ${lang} sermon, and only those`, () => {
			expect(Object.keys(localized[lang] ?? {}).sort(), RERUN).toEqual(slugsFor(lang).sort());
		});

		it(`${lang} cards were drawn from the art each slug resolves to today`, () => {
			const stale = Object.keys(localized[lang] ?? {}).filter((slug) => {
				const emblem = emblemForSermon(slug);
				const blob = [emblem, EMBLEM_ART[emblem], emblemHue(emblem)].join('\0');
				return sha(blob) !== localized[lang][slug].art;
			});
			expect(stale, `${lang} card art drifted — ${RERUN}`).toEqual([]);
		});
	}
});
