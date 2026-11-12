import { flushSync, mount, tick, unmount } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

const loadNeedPicks = vi.fn();
vi.mock('$lib/needFinder', async (importOriginal) => ({
	...(await importOriginal<typeof import('$lib/needFinder')>()),
	loadNeedPicks: (...args: unknown[]) => loadNeedPicks(...args)
}));

import NeedFinder from './NeedFinder.svelte';

let app: ReturnType<typeof mount> | null = null;
afterEach(() => {
	if (app) unmount(app);
	app = null;
	document.body.innerHTML = '';
	loadNeedPicks.mockReset();
});

const render = (needs: string[]) => {
	app = mount(NeedFinder, { target: document.body, props: { needs } });
	flushSync();
};
// The situation buttons, as chips (/topics) or tiles (home) alike.
const chips = () => [...document.querySelectorAll<HTMLButtonElement>('[role="group"] > button')];

describe('NeedFinder', () => {
	it('renders nothing below three situations', () => {
		render(['anxious', 'prayerDry']);
		expect(document.querySelector('section')).toBeNull();
	});

	it('draws real buttons, none pressed, and fetches nothing until one is pressed', () => {
		render(['anxious', 'prayerDry', 'grieving']);
		expect(chips()).toHaveLength(3);
		expect(chips().every((b) => b.type === 'button' && b.getAttribute('aria-pressed') === 'false')).toBe(true);
		expect(loadNeedPicks).not.toHaveBeenCalled();
	});

	it('loads and shows the picks on a press, with "More on" the topic', async () => {
		loadNeedPicks.mockResolvedValue({
			topic: { slug: 'prayer', title: 'On Prayer' },
			picks: [
				{ kind: 'shortRead', href: '/sermons/s', title: 'A sermon', byline: 'Spurgeon', words: 2000, language: 'en' },
				{ kind: 'book', href: '/books/b', title: 'A book', byline: 'Murray', language: 'en' },
				{ kind: 'plan', href: '/plans/p', title: 'A plan', byline: '', language: 'en' }
			]
		});
		render(['anxious', 'prayerDry', 'grieving']);
		chips()[1].click();
		flushSync();
		expect(chips()[1].getAttribute('aria-pressed')).toBe('true');
		expect(loadNeedPicks.mock.calls[0][0]).toMatchObject({ id: 'prayerDry', topic: 'prayer' });
		await tick();
		await tick();
		flushSync();
		const links = [...document.querySelectorAll<HTMLAnchorElement>('#need-finder-picks a')].map((a) =>
			a.getAttribute('href')
		);
		expect(links).toEqual(['/sermons/s/', '/books/b/', '/plans/p/', '/topics/prayer/']);

		// Pressing it again closes the picks.
		chips()[1].click();
		flushSync();
		expect(chips()[1].getAttribute('aria-pressed')).toBe('false');
		expect(document.querySelectorAll('#need-finder-picks a')).toHaveLength(0);
	});
});
