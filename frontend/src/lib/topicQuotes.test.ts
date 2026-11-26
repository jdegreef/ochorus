import { describe, expect, it } from 'vitest';
import { TOPIC_QUOTE_THEMES, quoteThemesFor, topicsForTheme } from './topicQuotes';

// The quote themes as library/quote_seed.py QUOTE_TOPICS lists them.
const QUOTE_THEMES = [
	'prayer',
	'faith',
	'grace',
	'holy-spirit',
	'love-of-god',
	'humility',
	'suffering',
	'holiness',
	'the-cross',
	'trusting-god',
	'joy',
	'hope',
	'peace',
	'repentance',
	'scripture',
	'salvation',
	'heaven',
	'surrender',
	'sin-and-temptation',
	'contentment'
];

describe('the topic ⇄ quote-theme bridge', () => {
	it('names only real quote themes', () => {
		for (const themes of Object.values(TOPIC_QUOTE_THEMES))
			for (const s of themes) expect(QUOTE_THEMES).toContain(s);
	});

	it('links only themes and shelves that have a page, in order', () => {
		const themes = [{ slug: 'hope' }, { slug: 'suffering' }];
		expect(quoteThemesFor('grace-and-comfort', themes).map((q) => q.slug)).toEqual([
			'suffering',
			'hope'
		]);
		expect(quoteThemesFor('for-teens', themes)).toEqual([]);
		const topics = [{ slug: 'the-way-of-holiness' }, { slug: 'prayer' }, { slug: 'deeper-life' }];
		expect(topicsForTheme('holiness', topics).map((tp) => tp.slug)).toEqual([
			'the-way-of-holiness',
			'deeper-life'
		]);
	});
});
