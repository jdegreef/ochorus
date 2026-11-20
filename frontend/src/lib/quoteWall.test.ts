import { describe, expect, it } from 'vitest';
import { wallTopic } from './quoteWall';
import type { Quote, QuoteTopicPage } from './library-public';

const q = (text: string): Quote => ({
	slug: text,
	text,
	paragraph: 1,
	source: { kind: 'chapter', slug: 'b', title: 'c', work: 'W', order: 1, cover_color: '' }
});
const group = (name: string, quotes: Quote[]) => ({
	author: { slug: name, name, birth_year: null },
	count: quotes.length,
	has_page: false,
	quotes
});

describe('wallTopic', () => {
	it("takes each writer's shortest line, shortest first, one per writer", () => {
		const page = {
			topic: { slug: 'prayer', title: 'Prayer', blurb: '', scripture_ref: '', scripture_text: '' },
			authors: [
				group('A', [q('a medium length line here'), q('a short one')]),
				group('B', [q('x'.repeat(200))]),
				group('C', [q('tiny')]),
				group('D', [q('the longest of the kept ones, still under the cap')])
			]
		} as QuoteTopicPage;
		const w = wallTopic(page, 2);
		expect(w.lines.map((l) => [l.author, l.quote.text])).toEqual([
			['C', 'tiny'],
			['A', 'a short one']
		]);
	});
	it('skips a line already on the wall under an earlier theme', () => {
		const page = {
			topic: { slug: 'faith', title: 'Faith', blurb: '', scripture_ref: '', scripture_text: '' },
			authors: [group('A', [q('shared'), q('own line')])]
		} as QuoteTopicPage;
		expect(wallTopic(page, 3, new Set(['shared'])).lines.map((l) => l.quote.text)).toEqual(['own line']);
	});
});
