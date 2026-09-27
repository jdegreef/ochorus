import { beforeEach, describe, expect, it, vi } from 'vitest';

const listArticlesWithFallback = vi.hoisted(() =>
	vi.fn(async () => [{ slug: 'how-to-pray', h1: 'How to Pray So That God Answers' }])
);
vi.mock('./library-public', () => ({
	listBooks: async () => [],
	listSermons: async () => [],
	listAuthors: async () => [],
	listArticlesWithFallback
}));

const { loadWorkTitles } = await import('./workTitles');

describe('loadWorkTitles', () => {
	beforeEach(() => {
		localStorage.clear();
		listArticlesWithFallback.mockClear();
	});

	it('skips the article list when this device holds nothing of an article', async () => {
		localStorage.setItem('ochorus:progress', JSON.stringify({ humility: { order: 1 } }));
		const titles = await loadWorkTitles('en');
		expect(listArticlesWithFallback).not.toHaveBeenCalled();
		expect(titles.article.size).toBe(0);
	});

	it('fetches it once anything is keyed to an article', async () => {
		localStorage.setItem('ochorus:marks', JSON.stringify({ 'article:how-to-pray:1': { m: [] } }));
		const titles = await loadWorkTitles('en');
		expect(titles.article.get('how-to-pray')).toEqual({
			title: 'How to Pray So That God Answers',
			author: ''
		});
	});
});
