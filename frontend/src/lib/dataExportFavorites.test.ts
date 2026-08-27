import { beforeEach, describe, expect, it, vi } from 'vitest';
import { FAVORITES_KEY } from './reading-schema';

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

	it('still falls back to the slug for an author the catalog does not know', async () => {
		localStorage.setItem(
			FAVORITES_KEY,
			JSON.stringify({ 'author:someone-unlisted': Date.parse('2026-01-01T00:00:00Z') })
		);

		const bundle = await collectExport('en', '2026-08-27T00:00:00.000Z');
		expect(bundle.favorites[0].title).toBe('Someone Unlisted');
	});
});
