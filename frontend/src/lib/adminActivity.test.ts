import { describe, expect, it } from 'vitest';
import type { AdminActionRow } from './library-admin';
import {
	actionMeta,
	actorName,
	absoluteTime,
	CATEGORIES,
	dayLabel,
	groupBursts,
	groupByDay,
	initials,
	issueRange,
	jobStatusMeta,
	jobTally,
	parseTarget,
	summariseDetail,
	titleParts,
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
	it('files an unknown role.* action under access, as the server does', () => {
		expect(actionMeta('role.edit').category).toBe('access');
		expect(actionMeta('broadcast.send').category).toBe('content');
	});

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

describe('summariseDetail: created', () => {
	it('hides the normal created=true and flags a job that was already open', () => {
		expect(summariseDetail({ created: true })).toEqual([]);
		expect(summariseDetail({ created: false })).toEqual([
			{ kind: 'warn', text: 'Already open — nothing filed' }
		]);
	});
});

describe('titleParts', () => {
	it('lifts the edition, in the title\'s own language, into a chip', () => {
		expect(
			titleParts('amanda-smith-autobiography-children', 'The Story of Amanda Smith (For Children)')
		).toEqual({ name: 'The Story of Amanda Smith', edition: 'For Children' });
		expect(titleParts('a-retrospect-children', 'Una retrospectiva (Para niños)')).toEqual({
			name: 'Una retrospectiva',
			edition: 'Para niños'
		});
	});
	it('leaves a work whose own title ends that way alone', () => {
		expect(titleParts('divine-songs-for-children', 'Divine Songs for Children')).toEqual({
			name: 'Divine Songs for Children',
			edition: null
		});
	});
	it('falls back to the slug without a title', () => {
		expect(titleParts('grace-abounding', '')).toEqual({ name: 'Grace Abounding', edition: null });
	});
});

describe('groupBursts', () => {
	const job = (slug: string, at: string, over: Partial<AdminActionRow> = {}) =>
		row({ action: 'translation.job', target: `book:${slug}:es`, at, ...over });

	it('folds a run of the same action into one burst, keeping order', () => {
		const rows = [
			job('a', '2026-10-01T07:07:00Z'),
			job('b', '2026-10-01T07:06:30Z'),
			job('c', '2026-10-01T07:06:00Z'),
			row({ action: 'review.decide', at: '2026-10-01T06:40:00Z' })
		];
		const items = groupBursts(rows);
		expect(items.map((i) => i.kind)).toEqual(['burst', 'row']);
		expect(items[0].kind === 'burst' && items[0].rows.map((r) => r.target)).toEqual([
			'book:a:es',
			'book:b:es',
			'book:c:es'
		]);
	});

	it('leaves runs of two, other languages, and long gaps as rows', () => {
		expect(groupBursts([job('a', '2026-10-01T07:07:00Z'), job('b', '2026-10-01T07:06:00Z')]).map((i) => i.kind)).toEqual([
			'row',
			'row'
		]);
		const mixed = [
			job('a', '2026-10-01T07:07:00Z'),
			job('b', '2026-10-01T07:06:00Z', { target: 'book:b:fr' }),
			job('c', '2026-10-01T07:05:00Z')
		];
		expect(groupBursts(mixed).every((i) => i.kind === 'row')).toBe(true);
		const kinds = [
			job('a', '2026-10-01T07:07:00Z'),
			job('b', '2026-10-01T07:06:00Z', { target: 'sermon:b:es' }),
			job('c', '2026-10-01T07:05:00Z')
		];
		expect(groupBursts(kinds).every((i) => i.kind === 'row')).toBe(true);
		const gappy = [job('a', '2026-10-01T09:00:00Z'), job('b', '2026-10-01T08:00:00Z'), job('c', '2026-10-01T07:00:00Z')];
		expect(groupBursts(gappy).every((i) => i.kind === 'row')).toBe(true);
	});
});

describe('issueRange', () => {
	it('spans the issues a burst filed', () => {
		const r = (n: number) => row({ detail: { issue: `https://github.com/o/r/issues/${n}` } });
		expect(issueRange([r(4821), r(4722), r(4800)])).toBe('#4722–#4821');
		expect(issueRange([r(7)])).toBe('#7');
		expect(issueRange([row({ detail: {} })])).toBe('');
	});
});

describe('groupBursts: reviews', () => {
	const review = (outcome: string, at: string, reason?: string) =>
		row({ action: 'review.decide', at, detail: reason ? { outcome, reason } : { outcome } });
	it('keeps a rejection, or a row with a reason, out of a run of approvals', () => {
		const items = groupBursts([
			review('approved', '2026-10-01T07:05:00Z'),
			review('approved', '2026-10-01T07:04:00Z'),
			review('approved', '2026-10-01T07:03:00Z'),
			review('rejected', '2026-10-01T07:02:00Z'),
			review('approved', '2026-10-01T07:01:00Z', 'fine')
		]);
		expect(items.map((i) => i.kind)).toEqual(['burst', 'row', 'row']);
	});
});

describe('jobStatusMeta', () => {
	it('says Live, not Approved, where nothing is approved', () => {
		expect(jobStatusMeta('done', 'book:grace:es').label).toBe('Approved');
		expect(jobStatusMeta('done', 'plan:advent:es').label).toBe('Live');
		expect(jobStatusMeta('closed', 'book:grace:es').hint).toMatch(/not planned/);
	});
});

describe('jobTally', () => {
	it('counts a burst by stage in journey order, skipping rows without one', () => {
		const r = (job_status?: AdminActionRow['job_status']) => row({ job_status });
		expect(jobTally([r('queued'), r('done'), r('queued'), r('stalled'), r(undefined)])).toEqual([
			{ status: 'done', count: 1 },
			{ status: 'stalled', count: 1 },
			{ status: 'queued', count: 2 }
		]);
	});
});
