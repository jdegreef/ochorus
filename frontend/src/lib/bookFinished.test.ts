import { describe, expect, it } from 'vitest';
import { finishedPicks } from './bookFinished';
import type { BookDetail, BookSummary, PlanSummary } from './library-public';

const b = (slug: string, author = 'murray') => ({ slug, author: { slug: author } }) as unknown as BookSummary;
const plan = (slug: string, covers: string[]) =>
	({ slug, covers: covers.map((c) => ({ kind: 'book', slug: c })) }) as unknown as PlanSummary;

const book = {
	...b('inner-chamber'),
	editions: [b('inner-chamber-teens')],
	related: [b('with-christ'), b('power-of-prayer', 'bounds'), b('pilgrims-progress', 'bunyan')]
} as unknown as BookDetail;

const none = () => ({ finished: false });

describe('finishedPicks', () => {
	it("offers the author's other books, never this one or its editions", () => {
		const catalog = [b('inner-chamber'), b('inner-chamber-teens'), b('abide'), b('humility'), b('other', 'bounds')];
		const { moreByAuthor } = finishedPicks({ book, catalog, plans: [], progress: none, max: 4 });
		expect(moreByAuthor.map((x) => x.slug)).toEqual(['abide', 'humility']);
	});

	it('leaves out books the reader has already finished', () => {
		const catalog = [b('abide'), b('humility')];
		const progress = (s: string) => ({ finished: s === 'abide' || s === 'pilgrims-progress' });
		const picks = finishedPicks({ book, catalog, plans: [], progress, max: 4 });
		expect(picks.moreByAuthor.map((x) => x.slug)).toEqual(['humility']);
		expect(picks.related.map((x) => x.slug)).toEqual(['with-christ', 'power-of-prayer']);
	});

	it('does not repeat an author pick under "More like this"', () => {
		const catalog = [b('with-christ')];
		const picks = finishedPicks({ book, catalog, plans: [], progress: none, max: 4 });
		expect(picks.moreByAuthor.map((x) => x.slug)).toEqual(['with-christ']);
		expect(picks.related.map((x) => x.slug)).toEqual(['power-of-prayer', 'pilgrims-progress']);
	});

	it('caps each list', () => {
		const catalog = ['a', 'b', 'c', 'd', 'e'].map((s) => b(s));
		expect(finishedPicks({ book, catalog, plans: [], progress: none, max: 2 }).moreByAuthor).toHaveLength(2);
	});

	it('finds the plans that read this book', () => {
		const plans = [plan('prayer-31', ['inner-chamber', 'abide']), plan('other', ['humility'])];
		const picks = finishedPicks({ book, catalog: [], plans, progress: none, max: 4 });
		expect(picks.plans.map((p) => p.slug)).toEqual(['prayer-31']);
	});
});
