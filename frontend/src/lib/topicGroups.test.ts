import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import en from '../../messages/en.json';
import { TOPIC_META } from './emblemNames';
import { TOPIC_GROUPS, groupTopics, topicGroupKey, type TopicGroupId } from './topicGroups';

const TOPIC_SEED = join(process.cwd(), '..', 'backend', 'library', 'topic_seed.py');

/** The seed's topic slugs — the first string of each `("slug", "Title",` tuple
 *  (the same reader as articleTopicSlugs.test.ts). */
const seedSlugs = (): string[] =>
	[...readFileSync(TOPIC_SEED, 'utf-8').matchAll(/\(\s*"([a-z0-9-]+)",\s*\n\s*"[^"]+",/g)].map(
		(m) => m[1]
	);

const listed = TOPIC_GROUPS.flatMap((g) => g.slugs);

describe('topic families', () => {
	it('places every seeded and every curated topic in a family', () => {
		const seeded = seedSlugs();
		expect(seeded.length).toBeGreaterThan(20);
		const unplaced = [...new Set([...seeded, ...Object.keys(TOPIC_META)])].filter(
			(s) => !listed.includes(s)
		);
		expect(unplaced, 'add the new shelf to a family in TOPIC_GROUPS (topicGroups.ts)').toEqual([]);
	});

	it('places each topic once', () => {
		expect(listed.length).toBe(new Set(listed).size);
	});

	it('has a heading in the catalogue for every family, the fallback included', () => {
		const ids: TopicGroupId[] = [...TOPIC_GROUPS.map((g) => g.id), 'more'];
		const key = (id: TopicGroupId) =>
			topicGroupKey(id)
				.replace(/([a-z0-9])([A-Z])/g, '$1_$2')
				.replace(/\./g, '_')
				.toLowerCase();
		expect(ids.filter((id) => !(key(id) in en))).toEqual([]);
	});
});

describe('groupTopics', () => {
	it('orders shelves by family, drops empty families, and never loses a new topic', () => {
		const groups = groupTopics([
			{ slug: 'for-teens' },
			{ slug: 'brand-new-shelf' },
			{ slug: 'the-inner-life' },
			{ slug: 'prayer' }
		]);
		expect(groups.map((g) => [g.id, g.topics.map((t) => t.slug)])).toEqual([
			['innerLife', ['prayer', 'the-inner-life']],
			['young', ['for-teens']],
			['more', ['brand-new-shelf']]
		]);
	});
});
