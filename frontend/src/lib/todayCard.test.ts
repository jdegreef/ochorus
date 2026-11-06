import { describe, expect, it } from 'vitest';
import { pickToday, splitVerse } from './todayCard';

describe('splitVerse', () => {
	it.each([
		['“Bless the Lord, O, my soul” (Ps. ciii. 1).', 'Bless the Lord, O, my soul', 'Ps. ciii. 1'],
		[
			'"Delight thyself also in the Lord; and he shall give thee the desires of thine heart" Ps. 37:4',
			'Delight thyself also in the Lord; and he shall give thee the desires of thine heart',
			'Ps. 37:4'
		],
		['“But now abideth Faith, Hope, Love.”— 1Co 13:13.', 'But now abideth Faith, Hope, Love.', '1Co 13:13'],
		['«Yo derramaré aguas sobre el sediento». (Isaías 44:3)', 'Yo derramaré aguas sobre el sediento', 'Isaías 44:3'],
		['«وَتَلَذَّذْ بِٱلرَّبِّ» (مزمور 37: 4)', 'وَتَلَذَّذْ بِٱلرَّبِّ', 'مزمور 37: 4'],
		['«ነፍሴ ሆይ፥ እግዚአብሔርን ባርኪ» (መዝሙር 103:1)።', 'ነፍሴ ሆይ፥ እግዚአብሔርን ባርኪ', 'መዝሙር 103:1']
	])('splits %s', (line, text, ref) => {
		expect(splitVerse(line)).toEqual({ text, ref });
	});

	it('keeps a quotation nested inside the verse', () => {
		expect(splitVerse('«Diciendo: «Esta es la sangre»». (Hebreos 9:20)')?.text).toBe(
			'Diciendo: «Esta es la sangre»'
		);
	});

	it.each([
		['a line that does not open on a quotation', 'The pillar of the cloud went before them. Ex. xiv. 19.'],
		['a poem', 'There are who come to me, and write, and send,'],
		['an excerpt cut short', '“For God so loved the world, that he gave…'],
		['a quotation with no reference', '“Be still.”']
	])('is null for %s', (_, line) => {
		expect(splitVerse(line)).toBeNull();
	});
});

describe('pickToday', () => {
	const day = new Date('2026-11-06T09:00:00');
	const shelf = [
		{ slug: 'a', excerpt: '“Verse A” Ps. 1:1' },
		{ slug: 'b', excerpt: 'No verse here.' },
		{ slug: 'c', excerpt: '“Verse C” Ps. 3:3' }
	];

	it('is the same all day and moves on the next', () => {
		const later = new Date('2026-11-06T23:30:00');
		const tomorrow = new Date('2026-11-07T09:00:00');
		expect(pickToday(shelf, later)).toEqual(pickToday(shelf, day));
		expect(pickToday(shelf, tomorrow).reading).not.toBe(pickToday(shelf, day).reading);
	});

	it('takes the verse from another book than the reading when it can', () => {
		for (let d = 0; d < 3; d++) {
			const { reading, verse } = pickToday(shelf, new Date(2026, 10, 6 + d, 9));
			expect(verse).not.toBeNull();
			expect(verse!.from).not.toBe(reading);
		}
	});

	it('falls back to the reading’s own verse, and to none', () => {
		const one = [{ excerpt: '“Only” Ps. 2:2' }];
		expect(pickToday(one, day).verse?.from).toBe(one[0]);
		expect(pickToday([{ excerpt: 'Prose.' }], day).verse).toBeNull();
		expect(pickToday([], day)).toEqual({ reading: null, verse: null });
	});
});
