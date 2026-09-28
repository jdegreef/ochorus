import { describe, it, expect } from 'vitest';
import { cardQuote } from './authorCard';
import { featuredQuote, quoteCardUrl } from './quoteShareCard';

const voice = (slug: string, count: number, ...texts: string[]) => ({
	author: { slug, name: slug },
	count,
	quotes: texts.map((text) => ({ text }))
});

describe('quote share cards', () => {
	it('live at one path per page', () => {
		expect(quoteCardUrl({ author: 'andrew-murray' })).toBe('/og/quotes/andrew-murray.jpg');
		expect(quoteCardUrl({ author: 'andrew-murray', topic: 'prayer' })).toBe(
			'/og/quotes/andrew-murray/prayer.jpg'
		);
		expect(quoteCardUrl({ topic: 'prayer' })).toBe('/og/quotes/topics/prayer.jpg');
	});

	it('feature the writer who says the most on a topic', () => {
		const voices = [
			voice('murray', 26, 'The knowledge of God’s Father love is the first lesson.'),
			voice('bounds', 47, 'Prayer makes the man; prayer makes the preacher.')
		];
		expect(featuredQuote(voices, cardQuote)).toEqual({
			author: { slug: 'bounds', name: 'bounds' },
			text: 'Prayer makes the man; prayer makes the preacher.'
		});
	});

	it('fall to the next writer when the first has nothing short enough', () => {
		const voices = [
			voice('bounds', 47, 'x'.repeat(400)),
			voice('muller', 8, 'In our natural state we dislike dealing with God alone.')
		];
		expect(featuredQuote(voices, cardQuote)?.author.slug).toBe('muller');
		expect(featuredQuote([voice('a', 1, 'short')], cardQuote)).toBeNull();
	});
});
