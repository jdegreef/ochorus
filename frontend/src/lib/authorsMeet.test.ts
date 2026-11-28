import { describe, expect, it } from 'vitest';
import { MEET_FIRST, meetFirst, timeline } from './authorsMeet';

const person = (slug: string, birth: number | null = 1800, photo = '/p.jpg') => ({
	slug,
	name: slug,
	photo_url: photo,
	birth_year: birth,
	death_year: null
});
const book = (slug: string, author: string) => ({ slug, title: slug, author: { slug: author } });

describe('meetFirst', () => {
	const people = MEET_FIRST.map((m) => person(m.author));
	it('pairs each pick with its named book, in the curated order', () => {
		const books = MEET_FIRST.map((m) => book(m.book, m.author));
		const picks = meetFirst(people, books);
		expect(picks.map((p) => p.author.slug)).toEqual(MEET_FIRST.map((m) => m.author));
		expect(picks.map((p) => p.book.slug)).toEqual(MEET_FIRST.map((m) => m.book));
	});
	it("falls back to the writer's book here, drops a writer with none, hides a short list", () => {
		const books = [
			book('other-augustine', 'augustine-of-hippo'),
			book('pilgrims-progress', 'john-bunyan'),
			book('all-of-grace', 'charles-h-spurgeon'),
			book('if', 'amy-carmichael')
		];
		const picks = meetFirst(people, books);
		expect(picks.map((p) => p.book.slug)).toEqual([
			'other-augustine',
			'pilgrims-progress',
			'all-of-grace',
			'if'
		]);
		expect(meetFirst(people, books.slice(0, 3))).toEqual([]);
	});
});

describe('timeline', () => {
	it('groups pictured, dated writers by era, earliest first, with a count of the rest', () => {
		const rows = timeline(
			[
				person('b', 1830),
				person('a', 354),
				person('c', 1820),
				person('undated', null),
				person('no-photo', 1500, ''),
				person('d', 1850)
			],
			2
		);
		expect(rows.map((r) => r.era.id)).toEqual(['early', 'missionary']);
		expect(rows[1].faces.map((p) => p.slug)).toEqual(['c', 'b']);
		expect(rows[1].more).toBe(1);
	});
});
