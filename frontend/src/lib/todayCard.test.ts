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

	it('reads a reference in any script’s digits', () => {
		expect(splitVerse('«تلذذ بالرب» (مزمور ٣٧: ٤)')?.ref).toBe('مزمور ٣٧: ٤');
		expect(splitVerse('«ደስ ይበልህ» (መዝሙር ፴፯:፬)')?.ref).toBe('መዝሙር ፴፯:፬');
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
		['a quotation with no reference', '“Be still.”'],
		['a reference the server cut short', '«Si se humillare mi pueblo, y oraren» 2…'],
		[
			'two quoted verses in a row',
			'“The spirit of man is the candle of the Lord.”— Pr 20:27. “For Thou wilt light my candle.”— Ps 18:28.'
		]
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

	it('offers the other books’ verses first, the reading’s own last', () => {
		for (let d = 0; d < 3; d++) {
			const { reading, verses } = pickToday(shelf, new Date(2026, 10, 6 + d, 9));
			expect(verses).toHaveLength(2);
			expect(verses[0].from).not.toBe(reading);
		}
	});

	it('is empty where no entry opens on a verse', () => {
		expect(pickToday([{ excerpt: 'Prose.' }], day).verses).toEqual([]);
		expect(pickToday([], day)).toEqual({ reading: null, verses: [] });
	});
});
