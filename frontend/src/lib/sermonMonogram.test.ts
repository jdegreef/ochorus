import { describe, expect, it } from 'vitest';
import { passageMark, sermonMonogram } from './sermonMonogram';

describe('sermonMonogram', () => {
	it.each([
		['Matthew 11:28', 'MAT', '11'],
		['Isaiah 53:3', 'ISA', '53'],
		['1 Corinthians 9:26-27', '1 COR', '9'],
		['1 Petro 1:3-4', '1 PET', '1'],
		['Números 15:38-39', 'NÚM', '15'],
		['Маттея 11:28', 'МАТ', '11'],
		['John 3:16; Romans 5:8', 'JOH', '3'],
		['भजन संहिता 23:6', 'भजन', '23'],
		['Psalm 23', 'PSA', '23'],
		['1ኛ ዮሐንስ 4:8', '1 ዮሐን', '4'],
		['يوحنا ٣:١٦', 'يوح', '٣']
	])('%s → %s %s', (ref, book, chapter) => {
		expect(sermonMonogram(ref, 'Title')).toEqual({ book, chapter });
	});

	it('keeps a book with no chapter', () => {
		expect(sermonMonogram('Jude', 'Title')).toEqual({ book: 'JUD', chapter: '' });
	});

	it('never splits a grapheme', () => {
		const m = sermonMonogram('यूहन्ना 1:29', 'Title');
		expect(m.chapter).toBe('1');
		// Three whole clusters, not three code units: a prefix longer than 3.
		expect('यूहन्ना'.startsWith(m.book)).toBe(true);
		expect(m.book.length).toBeGreaterThan(3);
	});

	it.each(['', '   ', null, undefined, '12:3'])('falls back to the title initial for %j', (ref) => {
		expect(sermonMonogram(ref, ' Himself')).toEqual({ book: '', chapter: 'H' });
		// A whole grapheme, vowel sign included.
		expect(sermonMonogram(ref, 'मैं प्रभु').chapter).toBe('मैं');
	});
});

describe('passageMark', () => {
	it('is the monogram as a badge mark', () => {
		expect(passageMark('Jeremiah 33:3')).toEqual({ top: 'JER', value: '33' });
	});

	it.each(['', null, undefined])('is null with no passage (%j), so the emblem stays', (ref) => {
		expect(passageMark(ref)).toBeNull();
	});
});
