import { describe, expect, it } from 'vitest';
import type { AdminActionRow } from './library-admin';
import {
	actionMeta,
	actorName,
	absoluteTime,
	busiestActor,
	categoryCounts,
	CATEGORIES,
	dayLabel,
	groupByDay,
	initials,
	parseTarget,
	summariseDetail,
	todayStats,
	toCsv
} from './adminActivity';

const row = (over: Partial<AdminActionRow>): AdminActionRow => ({
	action: 'content.publish',
	label: 'Document published',
	actor: 'james.degreef@gmail.com',
	target: 'book:humility:es',
	detail: {},
	at: '2026-09-06T12:00:00Z',
	...over
});

describe('actionMeta', () => {
	it('marks only the two reader-facing actions loud', () => {
		expect(actionMeta('language.go_live').loud).toBe(true);
		expect(actionMeta('content.publish').loud).toBe(true);
		// Everything else is told apart by glyph, not colour.
		for (const a of [
			'language.create',
			'language.settings',
			'language.thresholds',
			'translation.job',
			'author.create',
			'review.decide',
			'review.undo'
		]) {
			expect(actionMeta(a).loud).toBe(false);
		}
	});

	it('files every known action under an offered category', () => {
		for (const a of [
			'language.create',
			'translation.job',
			'author.create',
			'content.publish',
			'review.decide'
		]) {
			expect(CATEGORIES).toContain(actionMeta(a).category);
		}
	});

	it('keeps an unknown action rendering, self-filing by its prefix', () => {
		// A future endpoint should show up neutral, not throw.
		expect(actionMeta('review.reopen')).toEqual({ category: 'review', icon: 'document', loud: false });
		expect(actionMeta('mystery.event').category).toBe('content');
	});
});

describe('parseTarget', () => {
	it('links a language to its admin page', () => {
		expect(parseTarget('language:sw')).toEqual({
			kind: 'language',
			slug: 'sw',
			href: '/admin/languages/sw'
		});
	});

	it('links a book to its admin page and keeps the language edition', () => {
		expect(parseTarget('book:humility:es')).toEqual({
			kind: 'document',
			slug: 'humility',
			lang: 'es',
			href: '/admin/books/humility'
		});
	});

	it('links a sermon to its admin page and keeps the language edition', () => {
		expect(parseTarget('sermon:all-of-grace:en')).toEqual({
			kind: 'document',
			slug: 'all-of-grace',
			lang: 'en',
			href: '/admin/sermons/all-of-grace'
		});
	});

	it('links an author to the public author page', () => {
		expect(parseTarget('author:andrew-murray')).toEqual({
			kind: 'author',
			slug: 'andrew-murray',
			href: '/authors/andrew-murray'
		});
	});

	it('leaves an off-shape target as an unlinked label', () => {
		expect(parseTarget('')).toEqual({ kind: 'other', slug: '', href: null });
		expect(parseTarget('weird').href).toBeNull();
	});
});

describe('actorName / initials', () => {
	it('derives a friendly actor name and monogram from an email', () => {
		expect(actorName('james.degreef@gmail.com')).toBe('James Degreef');
		expect(initials('james.degreef@gmail.com')).toBe('JD');
	});

	it('names the tokenless dev request instead of showing a gap', () => {
		expect(actorName('')).toBe('a local dev request');
		expect(initials('')).toBe('·');
	});
});

describe('summariseDetail', () => {
	it('collapses a *_from / *_to pair into one before → after, as a percentage', () => {
		const parts = summariseDetail({ readiness_from: 60, readiness_to: 75 });
		expect(parts).toEqual([{ kind: 'diff', label: 'readiness', from: '60%', to: '75%' }]);
	});

	it('leads a review decision with its outcome and quotes the reason', () => {
		const parts = summariseDetail({ outcome: 'approved', reason: 'Reads clean.' });
		expect(parts[0]).toEqual({ kind: 'outcome', text: 'approved' });
		expect(parts).toContainEqual({ kind: 'quote', text: 'Reads clean.' });
	});

	it('renders a plain field as a labelled value and drops empties', () => {
		const parts = summariseDetail({ chapters: 210, note: '' });
		expect(parts).toEqual([{ kind: 'text', text: 'chapters: 210' }]);
	});

	it('does not collapse a pair whose *_to is null — never renders "→ null"', () => {
		const parts = summariseDetail({ direction_from: 'ltr', direction_to: null });
		expect(parts).not.toContainEqual(expect.objectContaining({ kind: 'diff' }));
		expect(parts).toEqual([{ kind: 'text', text: 'direction from: ltr' }]);
	});

	it('renders a URL field as a link chip — a GitHub issue as #number', () => {
		const parts = summariseDetail({ issue: 'https://github.com/jdegreef/ochorus/issues/1852' });
		expect(parts).toEqual([
			{ kind: 'link', text: '#1852', href: 'https://github.com/jdegreef/ochorus/issues/1852' }
		]);
	});

	it('falls back to the hostname for a non-issue URL', () => {
		const parts = summariseDetail({ source: 'https://www.gutenberg.org/ebooks/12' });
		expect(parts).toEqual([
			{ kind: 'link', text: 'gutenberg.org', href: 'https://www.gutenberg.org/ebooks/12' }
		]);
	});
});

describe('dayLabel / groupByDay', () => {
	const now = new Date('2026-09-06T12:00:00');
	it('names today and yesterday, else a full date', () => {
		expect(dayLabel('2026-09-06T02:00:00', now)).toBe('Today');
		expect(dayLabel('2026-09-05T23:00:00', now)).toBe('Yesterday');
		expect(dayLabel('2026-09-01T10:00:00', now)).toMatch(/September 1/);
	});

	it('keeps newest-first order and contiguous day blocks', () => {
		const groups = groupByDay(
			[
				row({ at: '2026-09-06T10:00:00', target: 'a' }),
				row({ at: '2026-09-06T09:00:00', target: 'b' }),
				row({ at: '2026-09-05T10:00:00', target: 'c' })
			],
			now
		);
		expect(groups.map((g) => g.label)).toEqual(['Today', 'Yesterday']);
		expect(groups[0].rows).toHaveLength(2);
		expect(groups[1].rows).toHaveLength(1);
	});
});

describe('categoryCounts', () => {
	it('tallies rows into their families, zero where none', () => {
		const counts = categoryCounts([
			row({ action: 'language.go_live' }),
			row({ action: 'language.create' }),
			row({ action: 'content.publish' })
		]);
		expect(counts.language).toBe(2);
		expect(counts.content).toBe(1);
		expect(counts.review).toBe(0);
	});
});

describe('busiestActor', () => {
	it('names the actor with the most rows in the window', () => {
		const { actor, count } = busiestActor([
			row({ actor: 'a@x.com' }),
			row({ actor: 'a@x.com' }),
			row({ actor: 'b@x.com' })
		]);
		expect(actor).toBe('a@x.com');
		expect(count).toBe(2);
	});
});

describe('todayStats', () => {
	const now = new Date('2026-09-06T12:00:00');
	it('counts today and its reader-facing share', () => {
		const stats = todayStats(
			[
				row({ action: 'language.go_live', at: '2026-09-06T10:00:00' }),
				row({ action: 'review.decide', at: '2026-09-06T09:00:00' }),
				row({ action: 'content.publish', at: '2026-09-05T10:00:00' })
			],
			now
		);
		expect(stats).toEqual({ count: 2, readerFacing: 1 });
	});
});

describe('toCsv', () => {
	it('writes a stable header and escapes quotes and commas', () => {
		const csv = toCsv([row({ label: 'He said "go", now' })]);
		const [header, line] = csv.split('\n');
		expect(header).toBe('at,action,label,actor,target,detail');
		// Embedded quotes are doubled and the whole field stays wrapped, so the
		// comma inside it can't split a column: one row stays one line.
		expect(line).toContain('"He said ""go"", now"');
		expect(csv.split('\n')).toHaveLength(2);
	});

	it('neutralises a leading formula character so a cell is not executable', () => {
		const [, line] = toCsv([row({ target: '=HYPERLINK("x")' })]).split('\n');
		// The value is prefixed with a single quote inside its quoted cell.
		expect(line).toContain('"\'=HYPERLINK');
	});
});

describe('absoluteTime', () => {
	it('formats a short month/day and time', () => {
		expect(absoluteTime('2026-09-06T12:00:00')).toMatch(/Sep 6/);
	});
});
