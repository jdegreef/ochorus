import { describe, expect, it } from 'vitest';
import { summarizeSaved, type SavedInput } from './savedSummary';
import type { JournalEntry } from './journal';

const empty: SavedInput = {
	favorites: [],
	booksInProgress: [],
	plansStarted: [],
	marks: [],
	bookmarks: 0,
	journal: {}
};

const entry = (id: string, kind: JournalEntry['kind'], extra: Partial<JournalEntry> = {}) =>
	({ id, kind, body: 'x', answeredAt: null, createdAt: 1, updatedAt: 1, ...extra }) as JournalEntry;

describe('summarizeSaved — the shelf', () => {
	it('is empty when nothing is saved', () => {
		expect(summarizeSaved('shelf', empty)).toEqual({ chips: [], total: 0 });
	});

	it('counts saved kinds and in-progress books, skipping zeros', () => {
		const s = summarizeSaved('shelf', {
			...empty,
			favorites: [
				{ kind: 'book', slug: 'humility' },
				{ kind: 'book', slug: 'all-of-grace' },
				{ kind: 'sermon', slug: 's1' }
			],
			booksInProgress: ['humility', 'absolute-surrender']
		});
		expect(s.chips).toEqual([
			{ labelKey: 'fav.groupBooks', count: 2 },
			{ labelKey: 'fav.shelfReading', count: 2 },
			{ labelKey: 'fav.groupSermons', count: 1 }
		]);
		// humility is saved AND being read: one book, so 3 books + 1 sermon.
		expect(s.total).toBe(4);
	});

	it('shows at most four chips but totals everything', () => {
		const s = summarizeSaved('shelf', {
			...empty,
			favorites: ['book', 'sermon', 'plan', 'quote', 'author', 'topic', 'article'].map((kind) => ({
				kind: kind as SavedInput['favorites'][number]['kind'],
				slug: 'x'
			})),
			booksInProgress: ['y']
		});
		expect(s.chips).toHaveLength(4);
		expect(s.total).toBe(8);
	});

	it('counts plans as the union of hearted and started', () => {
		const same = summarizeSaved('shelf', {
			...empty,
			favorites: [{ kind: 'plan', slug: 'a' }],
			plansStarted: ['a']
		});
		expect(same.chips).toEqual([{ labelKey: 'fav.groupPlans', count: 1 }]);
		const apart = summarizeSaved('shelf', {
			...empty,
			favorites: [{ kind: 'plan', slug: 'a' }],
			plansStarted: ['b']
		});
		expect(apart.chips).toEqual([{ labelKey: 'fav.groupPlans', count: 2 }]);
		expect(apart.total).toBe(2);
	});

	it('counts followed topics and saved articles', () => {
		const s = summarizeSaved('shelf', {
			...empty,
			favorites: [
				{ kind: 'topic', slug: 'prayer' },
				{ kind: 'article', slug: 'how-to-pray' }
			]
		});
		expect(s.total).toBe(2);
	});
});

describe('summarizeSaved — the notebook', () => {
	it('counts a highlight once across its segments, and notes apart', () => {
		const s = summarizeSaved('notebook', {
			...empty,
			marks: [
				{ work: 'book:humility:1', id: 'a' },
				{ work: 'book:humility:1', id: 'a' },
				{ work: 'book:humility:1', id: 'b' },
				{ work: 'book:humility:2', id: 'b' },
				{ work: 'book:humility:2', id: 'c', note: 'mine' }
			],
			bookmarks: 3,
			journal: {
				n: entry('n', 'note'),
				p: entry('p', 'prayer'),
				q: entry('q', 'prayer', { answeredAt: 2 }),
				gone: entry('gone', 'note', { deleted: true })
			}
		});
		expect(s.chips).toEqual([
			// 'b' in two chapters is two highlights; 'a' (two segments) is one.
			{ labelKey: 'settings.statHighlights', count: 3 },
			{ labelKey: 'settings.statNotes', count: 2 },
			{ labelKey: 'settings.statBookmarks', count: 3 },
			{ labelKey: 'notebook.tabPrayers', count: 2 }
		]);
		expect(s.total).toBe(10);
	});
});
