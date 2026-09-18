import { mount, unmount } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

// The card's Quote-card button hands the branded PNG renderer the SAME source
// line the copy text uses. Mock the renderer (it is pure canvas, which jsdom
// has no context for) and assert the attribution it receives, because a card
// that leaves the site under the wrong citation is the one failure this whole
// component exists to prevent.
vi.mock('$lib/quoteCard', () => ({
	shareQuoteCard: vi.fn(() => Promise.resolve('downloaded' as const))
}));

import QuoteCard from './QuoteCard.svelte';
import { shareQuoteCard } from '$lib/quoteCard';
import type { Quote } from '$lib/library-public';

const mockShare = vi.mocked(shareQuoteCard);

const quote = (over: Partial<Quote> = {}, source: Partial<Quote['source']> = {}): Quote => ({
	slug: 'faith-does-not-deliver',
	text: 'Faith does not deliver us from the chisel or hammer of the Divine sculptor.',
	paragraph: 45,
	source: {
		kind: 'chapter',
		slug: 'he-holds-my-tomorrows',
		title: 'Chapter 16',
		work: 'He Holds My Tomorrows',
		order: 16,
		cover_color: '#6f9d8b',
		...source
	},
	...over
});

let target: HTMLElement;
let component: Record<string, unknown> | undefined;

const render = (props: { quote: Quote; authorName: string; cite: string }): HTMLElement => {
	teardown();
	target = document.createElement('div');
	document.body.appendChild(target);
	component = mount(QuoteCard, { target, props }) as Record<string, unknown>;
	return target;
};

const teardown = () => {
	if (component) unmount(component);
	target?.remove();
	component = undefined;
};

const cardButton = (el: HTMLElement): HTMLButtonElement => {
	const btn = [...el.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Quote card');
	if (!btn) throw new Error('Quote card button not found');
	return btn as HTMLButtonElement;
};

afterEach(() => {
	teardown();
	mockShare.mockClear();
});

describe('the quote card offers a shareable Quote card', () => {
	it('renders a Quote card button beside Copy', () => {
		const el = render({
			quote: quote(),
			authorName: 'Gareth Evans',
			cite: 'Chapter 16 ¶45'
		});
		expect(cardButton(el)).toBeTruthy();
	});

	it('shares the line with author and "Work, chapter N" as its source', async () => {
		const el = render({
			quote: quote(),
			authorName: 'Gareth Evans',
			cite: 'Chapter 16 ¶45'
		});
		cardButton(el).click();
		// The handler dynamically imports the renderer before calling it, so wait
		// for the call rather than flushing a single microtask.
		await vi.waitFor(() => expect(mockShare).toHaveBeenCalledTimes(1));
		expect(mockShare).toHaveBeenCalledWith({
			quote: 'Faith does not deliver us from the chisel or hammer of the Divine sculptor.',
			author: 'Gareth Evans',
			source: 'He Holds My Tomorrows, chapter 16',
			site: 'ochorus.com'
		});
	});

	it('omits the chapter for a sermon (order null)', async () => {
		const el = render({
			quote: quote({ paragraph: 7 }, { kind: 'sermon', order: null, work: 'A Sermon on Faith' }),
			authorName: 'Gareth Evans',
			cite: 'A Sermon on Faith'
		});
		cardButton(el).click();
		await vi.waitFor(() =>
			expect(mockShare).toHaveBeenCalledWith(
				expect.objectContaining({ source: 'A Sermon on Faith' })
			)
		);
	});
});
