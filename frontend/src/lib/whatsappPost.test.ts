import { describe, expect, it } from 'vitest';
import type { TodayPicks } from './todayPicks';
import { whatsappPost } from './whatsappPost';

const author = (name: string) => ({ name }) as never;
const PICKS = {
	verse: { text: 'Sin will not be lord over you, for you do not live under the law but under grace.', ref: 'Romans 6:14 · OWB', lang: 'en' },
	reading: { heading: '', book: { slug: 'diary-of-an-old-soul', title: 'The Diary of an Old Soul', author: author('George MacDonald') } },
	sermon: { slug: 'the-divine-banquet', title: 'The Divine Banquet', author: author('Horatius Bonar') },
	chapter: { slug: 'gospel-of-mark', order: 5, title: 'Mark 4', href: '/books/gospel-of-mark/5' }
} as unknown as TodayPicks;

const input = (picks: TodayPicks, lang = '') => ({
	date: 'Wednesday, 11 November',
	picks,
	labels: { reading: 'Today’s reading', sermon: 'Sermon of the Day', chapter: 'Chapter for today' },
	href: (p: string) => `https://ochorus.com${lang}${p}`
});

describe('the WhatsApp post', () => {
	it('sets the day out in WhatsApp’s marks, each link bare on its own line', () => {
		expect(whatsappPost(input(PICKS))).toBe(
			[
				'*Wednesday, 11 November*',
				'',
				'_Sin will not be lord over you, for you do not live under the law but under grace._',
				'Romans 6:14 · OWB',
				'',
				'*Chapter for today:* Mark 4',
				'https://ochorus.com/books/gospel-of-mark/5/',
				'',
				'*Today’s reading:* The Diary of an Old Soul — George MacDonald',
				'https://ochorus.com/today/diary-of-an-old-soul/',
				'',
				'*Sermon of the Day:* The Divine Banquet — Horatius Bonar',
				'https://ochorus.com/sermons/the-divine-banquet/'
			].join('\n')
		);
	});

	it('names the day’s entry before its book, and links in the post’s language', () => {
		const picks = { ...PICKS, reading: { ...PICKS.reading!, heading: 'Januari 1' } } as TodayPicks;
		const post = whatsappPost(input(picks, '/sw'));
		expect(post).toContain('*Today’s reading:* Januari 1 (The Diary of an Old Soul) — George MacDonald');
		expect(post).toContain('https://ochorus.com/sw/sermons/the-divine-banquet/');
	});

	it('keeps a verse’s own marks from breaking the italic, and drops what the day lacks', () => {
		const post = whatsappPost(input({ verse: { text: 'Be *still*,\nand know', ref: 'Ps 46:10', lang: 'en' }, reading: null, sermon: null, chapter: null }));
		expect(post).toBe('*Wednesday, 11 November*\n\n_Be still, and know_\nPs 46:10');
	});
});
