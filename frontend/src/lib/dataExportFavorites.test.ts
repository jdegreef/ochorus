import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BOOKMARKS_KEY, FAVORITES_KEY } from './reading-schema';

/**
 * A favorited author must export under their real NAME.
 *
 * The favorites store names an author `author` (FavoriteKind), while the
 * export's title catalog keys authors `bio`, after the work kind. So the
 * lookup found no map at all and fell through to `unslug(slug)`: "J C Ryle"
 * for J. C. Ryle, and worse for any name whose punctuation or casing a slug
 * cannot carry — while the real name sat unused in `maps.bio`.
 *
 * The existing dataExport test only exercises `toMarkdown` against a
 * pre-built bundle, so the lookup path had no coverage at all.
 */
vi.mock('./library-public', () => ({
	listBooks: async () => [],
	listSermons: async () => [],
	listPlans: async () => [],
	listArticlesWithFallback: async () => [{ slug: 'how-to-pray', h1: 'How to Pray So That God Answers' }],
	listAuthors: async () => [
		{ slug: 'j-c-ryle', name: 'J. C. Ryle' },
		{ slug: 'andrew-murray', name: 'Andrew Murray' }
	]
}));

const { collectExport } = await import('./dataExport');

beforeEach(() => localStorage.clear());

describe('favorited authors in the export', () => {
	it('uses the author’s real name, not a name rebuilt from the slug', async () => {
		localStorage.setItem(
			FAVORITES_KEY,
			JSON.stringify({ 'author:j-c-ryle': Date.parse('2026-01-01T00:00:00Z') })
		);

		const bundle = await collectExport('en', '2026-08-27T00:00:00.000Z');
		expect(bundle.favorites).toHaveLength(1);
		expect(bundle.favorites[0].title).toBe('J. C. Ryle');
		expect(bundle.favorites[0].kind).toBe('author');
	});

	it('titles a favorited article by its headline, as it does a read one', async () => {
		localStorage.setItem(
			FAVORITES_KEY,
			JSON.stringify({ 'article:how-to-pray': Date.parse('2026-01-01T00:00:00Z') })
		);

		const bundle = await collectExport('en', '2026-08-27T00:00:00.000Z');
		expect(bundle.favorites[0]).toMatchObject({ kind: 'article', title: 'How to Pray So That God Answers' });
	});

	it('still falls back to the slug for an author the catalog does not know', async () => {
		localStorage.setItem(
			FAVORITES_KEY,
			JSON.stringify({ 'author:someone-unlisted': Date.parse('2026-01-01T00:00:00Z') })
		);

		const bundle = await collectExport('en', '2026-08-27T00:00:00.000Z');
		expect(bundle.favorites[0].title).toBe('Someone Unlisted');
	});
});

describe('bookmarks in the export', () => {
	it('files a bookmark under its own kind, not as a book named after its key', async () => {
		localStorage.setItem(
			BOOKMARKS_KEY,
			JSON.stringify({
				'article:how-to-pray': [{ id: 'b', order: 1, p: 3, snippet: 'Most of us', title: 't', at: 1 }]
			})
		);
		const bundle = await collectExport('en', '2026-08-27T00:00:00.000Z');
		expect(bundle.works).toHaveLength(1);
		expect(bundle.works[0]).toMatchObject({
			kind: 'article',
			slug: 'how-to-pray',
			title: 'How to Pray So That God Answers'
		});
		expect(bundle.works[0].bookmarks).toHaveLength(1);
	});
});
