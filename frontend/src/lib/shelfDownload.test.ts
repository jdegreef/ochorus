import { beforeEach, describe, expect, it, vi } from 'vitest';

// The queue's collaborators: a fake offline store and book detail.
const saved = new Set<string>();
const downloadCalls: string[] = [];
let failSlug: string | null = null;
let onDownload: ((slug: string) => void) | null = null;

vi.mock('./offlineBooks.svelte', () => ({
	offlineBooks: {
		active: null,
		has: (slug: string, lang: string) => saved.has(`${slug}:${lang}`),
		download: async (b: { slug: string; language: string }) => {
			downloadCalls.push(b.slug);
			onDownload?.(b.slug);
			if (b.slug === failSlug) return false;
			saved.add(`${b.slug}:${b.language}`);
			return true;
		},
		remove: async (slug: string, lang: string) => {
			saved.delete(`${slug}:${lang}`);
		}
	}
}));
vi.mock('./library-public', () => ({
	getBook: async (slug: string, language: string) => ({ slug, language, chapters: [{ order: 1 }] })
}));

import { shelfDownload } from './shelfDownload.svelte';

const refs = (...slugs: string[]) => slugs.map((slug) => ({ slug, language: 'en' }));

beforeEach(() => {
	saved.clear();
	downloadCalls.length = 0;
	failSlug = null;
	onDownload = null;
	shelfDownload.results = {};
	Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
});

describe('shelfDownload', () => {
	it('downloads only the books not yet saved, in shelf order', async () => {
		saved.add('b:en');
		await shelfDownload.start('to-read', refs('a', 'b', 'c'));
		expect(downloadCalls).toEqual(['a', 'c']);
		expect(shelfDownload.results['to-read']).toEqual({ saved: 2, failed: 0, stopped: false });
		expect(shelfDownload.job).toBeNull();
		expect(shelfDownload.missing(refs('a', 'b', 'c'))).toEqual([]);
	});

	it('counts a failed book and carries on', async () => {
		failSlug = 'b';
		await shelfDownload.start('to-read', refs('a', 'b', 'c'));
		expect(shelfDownload.results['to-read']).toEqual({ saved: 2, failed: 1, stopped: false });
		expect(shelfDownload.missing(refs('a', 'b', 'c'))).toEqual(refs('b'));
	});

	it('stops after the book in hand', async () => {
		onDownload = (slug) => slug === 'a' && shelfDownload.stop();
		await shelfDownload.start('to-read', refs('a', 'b', 'c'));
		expect(downloadCalls).toEqual(['a']);
		expect(shelfDownload.results['to-read']).toEqual({ saved: 1, failed: 0, stopped: true });
	});

	it('stops when the connection drops', async () => {
		onDownload = () => Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
		await shelfDownload.start('to-read', refs('a', 'b'));
		expect(downloadCalls).toEqual(['a']);
		expect(shelfDownload.results['to-read'].stopped).toBe(true);
	});

	it('runs one shelf at a time', async () => {
		let second: Promise<void> | null = null;
		onDownload = () => {
			second ??= shelfDownload.start('finished', refs('z'));
		};
		await shelfDownload.start('to-read', refs('a'));
		await second;
		expect(downloadCalls).toEqual(['a']);
		expect(shelfDownload.results.finished).toBeUndefined();
	});

	it('removes every saved download on the shelf', async () => {
		await shelfDownload.start('to-read', refs('a', 'b'));
		await shelfDownload.removeAll('to-read', refs('a', 'b'));
		expect(shelfDownload.missing(refs('a', 'b'))).toEqual(refs('a', 'b'));
		expect(shelfDownload.results['to-read']).toBeUndefined();
	});
});
