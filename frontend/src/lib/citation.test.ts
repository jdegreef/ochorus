import { describe, expect, it } from 'vitest';
import { CITATION_STYLES, cite, citedName, type Citable } from './citation';

const book: Citable = {
	kind: 'book',
	author: 'Charles H. Spurgeon',
	title: 'All of Grace',
	year: 1886,
	url: 'https://ochorus.com/books/all-of-grace/'
};
const sermon: Citable = {
	kind: 'sermon',
	author: 'J. C. Ryle',
	title: 'Do You Pray?',
	year: null,
	url: 'https://ochorus.com/sermons/do-you-pray/'
};

describe('citations', () => {
	it('puts the surname first as the A–Z index files it, and leaves a body or a title as written', () => {
		expect(citedName({ author: 'Charles H. Spurgeon' })).toBe('Spurgeon, Charles H.');
		expect(citedName({ author: 'Corrie ten Boom' })).toBe('ten Boom, Corrie');
		for (const n of ['Augustine', 'Gregory of Nyssa', 'Thomas à Kempis', 'Brother Lawrence', 'Saint Patrick']) {
			expect(citedName({ author: n })).toBe(n);
		}
		expect(citedName({ author: 'Ochorus Originals', corporate: true })).toBe('Ochorus Originals');
	});

	it('cites a book in each style, its title italic in the HTML', () => {
		expect(cite(book, 'mla').text).toBe('Spurgeon, Charles H. All of Grace. 1886. Ochorus, https://ochorus.com/books/all-of-grace/.');
		expect(cite(book, 'mla').html).toBe(
			'Spurgeon, Charles H. <i>All of Grace</i>. 1886. Ochorus, https://ochorus.com/books/all-of-grace/.'
		);
		expect(cite(book, 'chicago').text).toBe(
			'Spurgeon, Charles H. All of Grace. 1886. Reprint, Ochorus. https://ochorus.com/books/all-of-grace/.'
		);
		expect(cite(book, 'chicagoNote').text).toBe(
			'Charles H. Spurgeon, All of Grace (1886; repr., Ochorus), https://ochorus.com/books/all-of-grace/.'
		);
		expect(cite(book, 'bibtex').text).toBe(
			[
				'@book{spurgeon1886grace,',
				'  author = {Spurgeon, Charles H.},',
				'  title = {{All of Grace}},',
				'  year = {1886},',
				'  publisher = {Ochorus},',
				'  url = {https://ochorus.com/books/all-of-grace/}',
				'}'
			].join('\n')
		);
	});

	it('leaves out a year it does not know, and does not double a title’s own stop', () => {
		expect(cite(sermon, 'mla').text).toBe('Ryle, J. C. “Do You Pray?” Sermon. Ochorus, https://ochorus.com/sermons/do-you-pray/.');
		expect(cite(sermon, 'chicago').text).toBe('Ryle, J. C. “Do You Pray?” Sermon. Ochorus. https://ochorus.com/sermons/do-you-pray/.');
		expect(cite({ ...book, year: null }, 'chicago').text).toBe(
			'Spurgeon, Charles H. All of Grace. Ochorus. https://ochorus.com/books/all-of-grace/.'
		);
		expect(cite(sermon, 'chicagoNote').text).toBe('J. C. Ryle, “Do You Pray?” sermon, Ochorus, https://ochorus.com/sermons/do-you-pray/.');
		expect(cite({ ...sermon, title: 'Rest', year: 1875 }, 'chicagoNote').text).toContain('“Rest,” sermon, 1875,');
		expect(cite(sermon, 'bibtex').text).not.toContain('year');
	});

	it('escapes the HTML and the BibTeX, and keys an entry in plain ASCII', () => {
		const odd = { ...book, title: 'Faith & <Works> {1}' };
		expect(cite(odd, 'mla').html).toContain('<i>Faith &amp; &lt;Works&gt; {1}</i>');
		expect(cite(odd, 'bibtex').text).toContain('title = {{Faith \\& <Works> 1}}');
		const nee = cite({ ...book, author: 'Watchman Nee', title: 'الحياة المسيحية', year: null }, 'bibtex').text;
		expect(nee.split('\n')[0]).toBe('@book{nee,');
		expect(cite({ ...book, author: 'Ochorus Originals', corporate: true }, 'bibtex').text).toContain(
			'author = {{Ochorus Originals}}'
		);
	});

	it('marks the title as a run of its own, for the page to isolate', () => {
		expect(cite(book, 'mla').parts).toContainEqual({ title: 'All of Grace', italic: true });
		expect(cite(sermon, 'mla').parts).toContainEqual({ title: 'Do You Pray?', italic: false });
	});

	it('offers every style for both kinds', () => {
		for (const c of [book, sermon]) {
			for (const { style } of CITATION_STYLES) expect(cite(c, style).text.length).toBeGreaterThan(20);
		}
	});
});
