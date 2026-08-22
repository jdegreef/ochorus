import { describe, expect, it } from 'vitest';
import { EMBLEM_ART, emblemHue, MIN_ACCENT_SATURATION, type EmblemName } from './emblems';
import {
	TOPIC_META,
	PLAN_META,
	SERMON_EMBLEMS,
	FALLBACK_POOL,
	fallbackEmblem,
	emblemForSermon,
	planMeta,
	topicMeta
} from './emblemNames';

const names = Object.keys(EMBLEM_ART) as EmblemName[];

describe('emblem artwork', () => {
	it('is genuinely multicolour — every emblem uses at least three distinct colours', () => {
		for (const name of names) {
			const colours = new Set(EMBLEM_ART[name].match(/#[0-9a-f]{6}/gi)?.map((c) => c.toLowerCase()));
			expect(colours.size, `${name} uses ${colours.size} colour(s)`).toBeGreaterThanOrEqual(3);
		}
	});

	it('contains only inert drawing markup (it is rendered via {@html})', () => {
		// The art is static and author-controlled; this guards against someone
		// pasting in markup that would turn the trusted sink into a liability.
		for (const name of names) {
			expect(EMBLEM_ART[name]).not.toMatch(/<(script|foreignObject|use|image|a)\b|href|javascript:|\son\w+=/i);
		}
	});
});

describe('curated assignments', () => {
	const curated: Array<[string, EmblemName]> = [
		...Object.entries(TOPIC_META).map(([slug, m]) => [slug, m.emblem] as [string, EmblemName]),
		...Object.entries(PLAN_META).map(([slug, m]) => [slug, m.emblem] as [string, EmblemName]),
		...Object.entries(SERMON_EMBLEMS)
	];

	it('gives every topic, plan and sermon its own unique emblem', () => {
		const used = curated.map(([, emblem]) => emblem);
		expect(new Set(used).size, 'two catalogue entries share an emblem').toBe(used.length);
	});

	it('never hands a curated slug a fallback emblem', () => {
		for (const [slug, emblem] of curated) {
			expect(FALLBACK_POOL, `${slug} wears a generic fallback`).not.toContain(emblem);
		}
	});
});

describe('fallbacks for future content', () => {
	it('picks stably — the same slug always wears the same art', () => {
		expect(fallbackEmblem('a-brand-new-work')).toBe(fallbackEmblem('a-brand-new-work'));
		expect(names).toContain(fallbackEmblem('a-brand-new-work'));
	});

	it('resolves unmapped sermons, plans and topics to complete identities', () => {
		expect(names).toContain(emblemForSermon('some-future-sermon'));
		const plan = planMeta('some-future-plan');
		expect(plan.accent).toMatch(/^#[0-9a-f]{6}$/i);
		expect(names).toContain(plan.emblem);
		const topic = topicMeta('some-future-topic');
		expect(topic.accent).toMatch(/^#[0-9a-f]{6}$/i);
		expect(names).toContain(topic.emblem);
	});
});

describe('derived emblem hues', () => {
	/** HSL saturation of a #rrggbb colour. */
	const saturation = (hex: string): number => {
		const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
		const [max, min] = [Math.max(r, g, b), Math.min(r, g, b)];
		const lightness = (max + min) / 2;
		if (max === min) return 0;
		return lightness > 0.5 ? (max - min) / (2 - max - min) : (max - min) / (max + min);
	};

	it('gives every emblem a hex accent', () => {
		for (const name of names) {
			expect(emblemHue(name), name).toMatch(/^#[0-9a-f]{6}$/i);
		}
	});

	it('never returns one of the paper tints', () => {
		// Cream and warm white highlight nearly every emblem, so a naive
		// most-used-ink pick hands them the accent everywhere — and a card
		// lettered in #fdfaf3 has no accent at all, just two shades of white.
		const paper = ['#f3e2c4', '#e0c69a', '#fdfaf3'];
		for (const name of names) {
			expect(paper, name).not.toContain(emblemHue(name).toLowerCase());
		}
	});

	it('clears the saturation floor, so an accent reads as a colour not as grey', () => {
		// Asserted against the exported constant, so raising the floor tightens
		// the test instead of quietly leaving it behind.
		for (const name of names) {
			expect(saturation(emblemHue(name)), `${name} is ${emblemHue(name)}`).toBeGreaterThanOrEqual(
				MIN_ACCENT_SATURATION - 0.005
			);
		}
	});

	it('picks the colour the drawing is actually made of', () => {
		// A fixed expectation per emblem, rather than re-deriving the formula the
		// function uses: these are the hues the committed share cards are drawn
		// in, so a change to the scoring has to be looked at, not just absorbed.
		const expected: Array<[string, string]> = [
			['ravens-bread', '#273748'], // the raven — slate, saturated up off the floor
			['golden-key', '#d9a441'], // gold key on a night ground
			['still-waters', '#2f8f85'], // teal water
			['bruised-reed', '#3d7434'], // the green reed, not its cream highlight
			['cross-sunrise', '#d9a441'] // the rising sun behind the cross
		];
		for (const [emblem, hue] of expected) {
			expect(emblemHue(emblem as EmblemName), emblem).toBe(hue);
		}
	});
});
