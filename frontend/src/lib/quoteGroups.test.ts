/**
 * Grouping quotations by work.
 *
 * The grouping is what earns the page its colour — STYLE_GUIDE §5 says a list's
 * hue tracks whatever it is grouped by — so these hold the two things that
 * would quietly break it: a group must be a CONSECUTIVE run (the API sends
 * reading order, and a re-sort without a regroup would shatter every work into
 * singletons), and the sermons must arrive as one group rather than six.
 */
import { describe, expect, it } from 'vitest';
import { groupQuotes } from './library-public';
import type { Quote, QuotePage } from './library-public';

const chapter = (work: string, slug: string, order: number, p: number): Quote => ({
	slug: `${slug}-${order}-${p}`,
	text: `A sentence from ${work}.`,
	paragraph: p,
	source: { kind: 'chapter', slug, title: `Ch ${order}`, work, order, cover_color: '#334' }
});

const sermon = (title: string, p: number): Quote => ({
	slug: `${title}-${p}`,
	text: `A sentence from ${title}.`,
	paragraph: p,
	source: { kind: 'sermon', slug: title, title, work: title, order: null, cover_color: '' }
});

const page = (quotes: Quote[]): QuotePage => ({
	author: { slug: 'w', name: 'A Writer', photo_url: '', birth_year: 1834 },
	topics: [],
	quotes
});

describe('grouping quotations by work', () => {
	it('makes one group per work, in the order they arrive', () => {
		const groups = groupQuotes(
			page([
				chapter('All of Grace', 'aog', 1, 2),
				chapter('All of Grace', 'aog', 3, 9),
				chapter('Till He Come', 'thc', 2, 4)
			]),
			'#888'
		);
		expect(groups.map((g) => g.work)).toEqual(['All of Grace', 'Till He Come']);
		expect(groups[0].quotes).toHaveLength(2);
	});

	it('gathers every sermon into ONE trailing group', () => {
		// Six sermons carrying nine quotations between them would otherwise be
		// six groups of one or two, which reads as debris rather than structure.
		const groups = groupQuotes(
			page([chapter('All of Grace', 'aog', 1, 2), sermon('Free Grace', 3), sermon('Christ Crucified', 5)]),
			'#888'
		);
		expect(groups.map((g) => g.work)).toEqual(['All of Grace', 'Sermons']);
		expect(groups[1].quotes).toHaveLength(2);
	});

	it('takes a book group’s hue from the book and a sermon group’s from the era', () => {
		const groups = groupQuotes(page([chapter('All of Grace', 'aog', 1, 2), sermon('Free Grace', 3)]), '#abc');
		expect(groups[0].hue).toBe('#334');
		expect(groups[1].hue).toBe('#abc');
	});

	it('falls back to the era hue when a book has no cover colour', () => {
		const q = chapter('Uncoloured', 'unc', 1, 1);
		q.source.cover_color = '';
		expect(groupQuotes(page([q]), '#abc')[0].hue).toBe('#abc');
	});

	it('gives each group an anchor the jump row can target', () => {
		const groups = groupQuotes(page([chapter('All of Grace', 'aog', 1, 2), sermon('Free Grace', 3)]), '#888');
		expect(groups.map((g) => g.id)).toEqual(['w-aog', 'sermons']);
		expect(new Set(groups.map((g) => g.id)).size).toBe(groups.length);
	});

	it('would split a work that arrives out of order — which is why order is the API’s job', () => {
		// Documents the contract rather than defending against it: grouping scans
		// CONSECUTIVE runs, so re-sorting the list client-side without regrouping
		// shatters a work into singletons.
		const groups = groupQuotes(
			page([
				chapter('All of Grace', 'aog', 1, 2),
				chapter('Till He Come', 'thc', 2, 4),
				chapter('All of Grace', 'aog', 3, 9)
			]),
			'#888'
		);
		expect(groups).toHaveLength(3);
	});

	it('handles a single work without inventing a group', () => {
		expect(groupQuotes(page([chapter('Solo', 's', 1, 1)]), '#888')).toHaveLength(1);
	});
});
