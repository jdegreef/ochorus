import { describe, expect, it } from 'vitest';
import {
	EMBLEM_ART,
	TOPIC_EMBLEMS,
	PLAN_META,
	SERMON_EMBLEMS,
	fallbackEmblem,
	emblemForSermon,
	planMeta,
	type EmblemName
} from './emblems';
import { topicMeta } from './topics';

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
		...Object.entries(TOPIC_EMBLEMS),
		...Object.entries(PLAN_META).map(([slug, m]) => [slug, m.emblem] as [string, EmblemName]),
		...Object.entries(SERMON_EMBLEMS)
	];

	it('gives every topic, plan and sermon its own unique emblem', () => {
		const used = curated.map(([, emblem]) => emblem);
		expect(new Set(used).size, 'two catalogue entries share an emblem').toBe(used.length);
	});

	it('never hands a curated slug a fallback emblem', () => {
		const pool: EmblemName[] = ['oil-lamp', 'wheat-sheaf', 'morning-star', 'watchmans-bell'];
		for (const [slug, emblem] of curated) {
			expect(pool, `${slug} wears a generic fallback`).not.toContain(emblem);
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
