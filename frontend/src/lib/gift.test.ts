import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
	GIFT_NAME_MAX,
	GIFT_NOTE_MAX,
	cleanGiftName,
	cleanGiftNote,
	decodeGift,
	encodeGift,
	giftFromHash,
	giftHash,
	giftLength
} from './gift';

const book = { slug: 'all-of-grace', lang: 'en' };
const raw = (v: unknown) =>
	btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(v))))
		.replace(/\+/g, '-')
		.replace(/\//g, '_')
		.replace(/=+$/, '');

describe('gift link round trip', () => {
	it('carries slug, language, name and note', () => {
		const gift = { ...book, name: 'David', note: 'Start with chapter 1, it’s two minutes.' };
		expect(decodeGift(encodeGift(gift))).toEqual(gift);
		expect(giftFromHash(giftHash(gift))).toEqual(gift);
	});

	it.each([
		['emoji', 'Ade 🙏🏾', 'For you 👨‍👩‍👧 ❤️'],
		['Arabic (RTL)', 'مريم', 'هذا الكتاب غيّر حياتي.'],
		['Hebrew (RTL)', 'דוד', 'שלום'],
		['Amharic', 'ዳዊት', 'ይህ መጽሐፍ ለአንተ ነው።'],
		['Hindi with ZWNJ/ZWJ', 'प्रिया', 'क्‍ष यह किताब'],
		['Japanese', 'さくら', 'この本をどうぞ'],
		['accents', 'José', 'Ça m’a aidé.']
	])('survives %s', (_label, name, note) => {
		const gift = { slug: 'humility-2', lang: 'ar', name, note };
		expect(decodeGift(encodeGift(gift))).toEqual(gift);
	});

	it('is URL-safe base64 (no +, /, = or %)', () => {
		const p = encodeGift({ ...book, name: '???>>>', note: 'ÿÿÿ~~~ 🙏'.repeat(20) });
		expect(p).toMatch(/^[A-Za-z0-9_-]+$/);
	});

	it('stays short for a full note in a 3-byte script', () => {
		const p = encodeGift({ ...book, name: 'ዳዊት', note: 'ሀ'.repeat(GIFT_NOTE_MAX) });
		expect(p.length).toBeLessThan(1300);
	});

	it('rejects an invalid book when encoding', () => {
		expect(() => encodeGift({ slug: '../x', lang: 'en', name: '', note: '' })).toThrow();
		expect(() => encodeGift({ slug: 'x', lang: 'english', name: '', note: '' })).toThrow();
	});
});

describe('decodeGift on untrusted input', () => {
	it.each([
		['empty', ''],
		['null', null],
		['not base64url', 'abc$%^'],
		['not JSON', raw('x').slice(0, 3) + 'zz'],
		['too long', 'A'.repeat(5000)],
		['an object', raw({ slug: 'a' })],
		['wrong version', raw([2, 'a', 'en', 'n', 'm'])],
		['bad slug', raw([1, 'A Book', 'en', 'n', 'm'])],
		['path in slug', raw([1, '../../admin', 'en', 'n', 'm'])],
		['bad language', raw([1, 'a', 'EN-us', 'n', 'm'])],
		['non-string name', raw([1, 'a', 'en', { x: 1 }, 'm'])],
		['invalid UTF-8', btoa('\xff\xfe\xfd').replace(/=+$/, '')]
	])('refuses %s', (_label, payload) => {
		expect(decodeGift(payload as string | null)).toBeNull();
	});

	it('re-cleans a hand-made payload: caps, links, markup stays text', () => {
		const g = decodeGift(
			raw([1, 'a', 'en', 'Eve '.repeat(30), '<script>alert(1)</script> see https://evil.example/x ' + 'x'.repeat(400)])
		);
		expect(g).not.toBeNull();
		expect(giftLength(g!.name)).toBeLessThanOrEqual(GIFT_NAME_MAX);
		expect(giftLength(g!.note)).toBeLessThanOrEqual(GIFT_NOTE_MAX);
		expect(g!.note).not.toContain('evil.example');
		// Markup is not stripped but never interpreted: the page renders text.
		expect(g!.note.startsWith('<script>')).toBe(true);
	});

	it('reads only a #g= fragment', () => {
		expect(giftFromHash('')).toBeNull();
		expect(giftFromHash('#access_token=x')).toBeNull();
		expect(giftFromHash('g=' + encodeGift({ ...book, name: 'A', note: '' }))?.name).toBe('A');
	});
});

describe('cleanGiftNote', () => {
	it.each([
		'Read https://example.com/page now',
		'Read http://x.y now',
		'Read www.example.org now',
		'Read bit.ly/abc123 now',
		'Read example.com now',
		'Read sub.domain.co.uk/path?q=1 now',
		'Read wa.me/123456 now',
		'Read me@example.com now',
		'Read HTTPS://EXAMPLE.COM now'
	])('removes the link in %j', (input) => {
		const out = cleanGiftNote(input);
		expect(out.text).toBe('Read now');
		expect(out.removedLinks).toBe(true);
	});

	it.each(['Read it.It changed me', 'Mr.Smith said so', 'See ch.3 and v.12', 'Come to me. It helps', 'e.g. this'])(
		'leaves ordinary text alone: %j',
		(input) => {
			expect(cleanGiftNote(input)).toEqual({ text: input, removedLinks: false });
		}
	);

	it('normalises whitespace but keeps one blank line between paragraphs', () => {
		expect(cleanGiftNote('  Hi\t\tthere \r\n\r\n\r\n\r\n  Second   line  ').text).toBe('Hi there\n\nSecond line');
	});

	it('strips bidi overrides and invisibles but keeps joiners', () => {
		expect(cleanGiftNote('a‮b​c\u0007d').text).toBe('abcd');
		expect(cleanGiftNote('👨‍👩').text).toBe('👨‍👩');
		expect(cleanGiftNote('क‌ष').text).toBe('क‌ष');
	});

	it('caps by characters without splitting an emoji', () => {
		const out = cleanGiftNote('🙏🏾'.repeat(GIFT_NOTE_MAX + 10)).text;
		expect(giftLength(out)).toBe(GIFT_NOTE_MAX);
		expect(out.endsWith('🙏🏾')).toBe(true);
	});
});

describe('cleanGiftName', () => {
	it('is one line, trimmed and capped', () => {
		expect(cleanGiftName('  Mary\n  Ann  ').text).toBe('Mary Ann');
		expect(giftLength(cleanGiftName('x'.repeat(100)).text)).toBe(GIFT_NAME_MAX);
	});

	it('drops a link posing as a name', () => {
		expect(cleanGiftName('Free prizes at win.com').text).toBe('Free prizes at');
	});
});

describe('the gift landing page (source guard)', () => {
	// A source check, not a render: the page needs a live API. What matters is
	// that untrusted link text can never become markup or metadata.
	const PAGE = readFileSync(join(import.meta.dirname, '..', 'routes/gift/+page.svelte'), 'utf8');
	const head = PAGE.slice(PAGE.indexOf('<svelte:head>'), PAGE.indexOf('</svelte:head>'));

	it('never renders link text as HTML', () => {
		expect(PAGE).not.toMatch(/\{@html/);
	});

	it('keeps the name and note out of <title> and meta tags, and is noindex', () => {
		expect(head).not.toMatch(/gift[!?]*\.(name|note)|fromLine|noteHeading/);
		expect(head).toContain('<meta name="robots" content="noindex" />');
	});
});
