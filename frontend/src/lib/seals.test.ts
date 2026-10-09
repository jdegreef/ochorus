import { describe, expect, it } from 'vitest';
import { computeSeals, firstRunReaching, shelfOrder, type SealInput } from './seals';

const at = (iso: string) => new Date(`${iso}T12:00:00`).getTime();
const author = (slug: string, birth: number | null) => ({ slug, name: slug.toUpperCase(), birth_year: birth });

const base = (over: Partial<SealInput> = {}): SealInput => ({
	progress: [],
	books: [],
	days: [],
	plans: [],
	planDone: {},
	marks: 0,
	...over
});
const get = (input: SealInput, key: string) => computeSeals(input).find((s) => s.key === key)!;

describe('reading seals', () => {
	it('starts every seal unearned for a new reader, and none of them on the way', () => {
		const seals = computeSeals(base());
		expect(seals).toHaveLength(12);
		expect(seals.every((s) => s.state === 'locked')).toBe(true);
	});

	it('presses First Finish and Five on the Shelf on the finishes that earned them', () => {
		const progress = ['a', 'b', 'c', 'd', 'e'].map((slug, i) => ({
			slug,
			kind: 'book',
			finished_at: at(`2026-03-0${i + 1}`),
			language: 'en'
		}));
		progress.push({ slug: 'open', kind: 'book', finished_at: null as unknown as number, language: 'en' });
		const input = base({ progress });
		expect(get(input, 'first')).toMatchObject({ state: 'earned', earnedOn: '2026-03-01', via: { slug: 'a' } });
		expect(get(input, 'five')).toMatchObject({ state: 'earned', earnedOn: '2026-03-05', via: { slug: 'e' } });
		expect(get(input, 'year')).toMatchObject({ need: 12 });
	});

	it('gives a Pupil seal per writer read three times, and shows the nearest one otherwise', () => {
		const books = [
			{ slug: 'm1', author: author('murray', 1828) },
			{ slug: 'm2', author: author('murray', 1828) },
			{ slug: 'm3', author: author('murray', 1828) },
			{ slug: 's1', author: author('spurgeon', 1834) }
		];
		const progress = ['m1', 's1', 'm2', 'm3'].map((slug, i) => ({
			slug,
			kind: 'book',
			finished_at: at(`2026-06-1${i}`),
			language: 'en'
		}));
		const seals = computeSeals(base({ books, progress }));
		const pupils = seals.filter((s) => s.id === 'pupil');
		expect(pupils).toHaveLength(1);
		expect(pupils[0]).toMatchObject({ key: 'pupil:murray', state: 'earned', via: { slug: 'm3' }, author: { name: 'MURRAY' } });

		const one = computeSeals(base({ books, progress: progress.slice(0, 2) })).filter((s) => s.id === 'pupil');
		expect(one).toHaveLength(1);
		expect(one[0]).toMatchObject({ state: 'progress', have: 1, need: 3 });
	});

	it('keeps a streak seal once the run is broken, dated the day the run first reached it', () => {
		const run = Array.from({ length: 7 }, (_, i) => `2026-03-${String(10 + i).padStart(2, '0')}`);
		const days = [...run, '2026-04-01'];
		expect(firstRunReaching(days, 7)).toBe('2026-03-16');
		expect(get(base({ days }), 'week')).toMatchObject({ state: 'earned', earnedOn: '2026-03-16' });
		expect(get(base({ days }), 'thirty')).toMatchObject({ state: 'progress', have: 7, need: 30 });
	});

	it('walks Through the Centuries by the writers’ eras and names what is missing', () => {
		const books = [
			{ slug: 'aug', author: author('augustine', 354) },
			{ slug: 'bun', author: author('bunyan', 1628) },
			{ slug: 'mur', author: author('murray', 1828) },
			{ slug: 'nob', author: author('nobody', null) }
		];
		const progress = books.map((b, i) => ({ slug: b.slug, kind: 'book', finished_at: at(`2026-01-0${i + 1}`), language: 'en' }));
		const s = get(base({ books, progress }), 'centuries');
		expect(s).toMatchObject({ state: 'progress', have: 3, need: 6 });
		expect(s.missingEras).toEqual(['medieval', 'awakenings', 'modern']);
	});

	it('earns Pilgrim only for a plan read to its last day', () => {
		const plans = [{ slug: 'humility-12-days', day_count: 12 }];
		expect(get(base({ plans, planDone: { 'humility-12-days': [1, 2, 3] } }), 'pilgrim').state).toBe('progress');
		const walked = get(base({ plans, planDone: { 'humility-12-days': Array.from({ length: 12 }, (_, i) => i + 1) } }), 'pilgrim');
		expect(walked).toMatchObject({ state: 'earned', via: { kind: 'plan', slug: 'humility-12-days' } });
	});

	it('earns Two Tongues on the first finish in a second language, books or sermons', () => {
		const progress = [
			{ slug: 'a', kind: 'book', finished_at: at('2026-02-01'), language: 'en' },
			{ slug: 'b', kind: 'book', finished_at: at('2026-02-02'), language: 'en' },
			{ slug: 's', kind: 'sermon', finished_at: at('2026-02-03'), language: 'sw' }
		];
		expect(get(base({ progress }), 'tongues')).toMatchObject({ state: 'earned', via: { kind: 'sermon', slug: 's' } });
		expect(get(base({ progress }), 'hearer')).toMatchObject({ state: 'earned', earnedOn: '2026-02-03' });
	});

	it('orders the shelf earned (newest first), then on the way, then not yet', () => {
		const days = Array.from({ length: 8 }, (_, i) => `2026-05-0${i + 1}`);
		const progress = [{ slug: 'a', kind: 'book', finished_at: at('2026-01-01'), language: 'en' }];
		const order = shelfOrder(computeSeals(base({ days, progress, marks: 3 }))).map((s) => `${s.id}:${s.state}`);
		expect(order.slice(0, 2)).toEqual(['week:earned', 'first:earned']);
		const states = order.map((o) => o.split(':')[1]);
		expect(states.lastIndexOf('progress')).toBeLessThan(states.indexOf('locked'));
	});
});
