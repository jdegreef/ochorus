/**
 * The host keeps serving pages an earlier deploy published (scripts/
 * build-tombstones.mjs). These pin the parts of that step that can go quietly
 * wrong: the list parser, the "what to overwrite" rule, the committed seed, the
 * postbuild wiring — and, end to end over a scratch build dir, that a withdrawn
 * page's prose is really replaced and a returning page is never touched.
 */
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import {
	MANIFEST,
	htmlFiles,
	main,
	parsePageList,
	tombstonesFor
} from '../../scripts/build-tombstones.mjs';

const ROOT = process.cwd();
const read = (p: string) => readFileSync(join(ROOT, p), 'utf8');

describe('parsePageList', () => {
	it('reads paths, skipping comments, blanks and the two shells', () => {
		expect(parsePageList('# note\n\na/index.html\n200.html\n404.html\nb.html\n', 't')).toEqual([
			'a/index.html',
			'b.html'
		]);
	});

	it.each([
		'/abs/index.html',
		'../escape/index.html',
		'a/../../b.html',
		'<!doctype html>',
		'sermons/x/'
	])('rejects %j — an error page must never read as a list of paths', (line) => {
		expect(() => parsePageList(`ok/index.html\n${line}\n`, 't')).toThrow(/build-relative/);
	});
});

describe('tombstonesFor', () => {
	it('is every known path the build no longer has, never one it does', () => {
		expect(
			tombstonesFor(['gone/index.html', 'kept/index.html', 'gone/index.html', '404.html'], ['kept/index.html'])
		).toEqual(['gone/index.html']);
	});
});

describe('the committed seed', () => {
	const seed = parsePageList(read('scripts/withdrawn-pages.txt'), 'seed');

	it('parses, without duplicates', () => {
		expect(seed.length).toBeGreaterThan(0);
		expect(new Set(seed).size).toBe(seed.length);
	});

	// The case that made this serious: a copyright-blocked work whose leaked
	// translations kept serving after migration 0164 unpublished them.
	it('covers the leaked copyright-blocked Grace for Grace translations', () => {
		for (const lang of ['es', 'fr', 'pt']) {
			expect(seed).toContain(`${lang}/books/grace-for-grace-2/index.html`);
			expect(seed).toContain(`${lang}/books/grace-for-grace-2/1/index.html`);
		}
	});
});

it('runs as the LAST postbuild step, after build-404 writes the shell it copies', () => {
	const steps = JSON.parse(read('package.json')).scripts.postbuild.split('&&').map((s: string) => s.trim());
	expect(steps.at(-1)).toBe('node scripts/build-tombstones.mjs');
	expect(steps.indexOf('node scripts/build-404.mjs')).toBeLessThan(steps.length - 1);
});

describe('main, over a scratch build', () => {
	let dir = '';
	const build = () => join(dir, 'build');
	const put = (p: string, body: string) => {
		mkdirSync(dirname(join(build(), p)), { recursive: true });
		writeFileSync(join(build(), p), body);
	};
	const page = (p: string) => readFileSync(join(build(), p), 'utf8');
	const saved = { previous: process.env.TOMBSTONE_PREVIOUS, render: process.env.RENDER };
	const restore = (key: string, value: string | undefined) =>
		value === undefined ? delete process.env[key] : (process.env[key] = value);
	afterEach(() => {
		restore('TOMBSTONE_PREVIOUS', saved.previous);
		restore('RENDER', saved.render);
		delete process.env.TOMBSTONE_MAX;
		if (dir) rmSync(dir, { recursive: true, force: true });
	});

	it('overwrites withdrawn pages, leaves rebuilt ones, and lists everything', async () => {
		dir = mkdtempSync(join(tmpdir(), 'tombstones-'));
		const previous = join(dir, 'previous.txt');
		writeFileSync(previous, 'books/gone/index.html\nbooks/gone/1/index.html\nbooks/back/index.html\n');
		put('404.html', '<meta name="robots" content="noindex">SHELL');
		put('200.html', 'SHELL');
		put('books/back/index.html', 'REAL PAGE');
		put('books/new/index.html', 'NEW PAGE');
		process.env.TOMBSTONE_PREVIOUS = previous;
		delete process.env.RENDER;

		await main(build());

		expect(page('books/gone/index.html')).toContain('SHELL');
		expect(page('books/gone/1/index.html')).toContain('SHELL');
		expect(page('books/back/index.html')).toBe('REAL PAGE');
		// The seed's paths are tombstoned too, so the list is cumulative from day one.
		expect(page('sermons/the-marriage-tie/index.html')).toContain('SHELL');

		const listed = parsePageList(page(MANIFEST), MANIFEST);
		expect(listed).toEqual(htmlFiles(build()).filter((p) => !/^(200|404)\.html$/.test(p)).sort());
		expect(listed).toEqual(expect.arrayContaining(['books/gone/index.html', 'books/new/index.html']));
	});

	it('refuses a burst of withdrawals — a build short of pages, not a withdrawal', async () => {
		dir = mkdtempSync(join(tmpdir(), 'tombstones-'));
		const previous = join(dir, 'previous.txt');
		writeFileSync(previous, 'a/index.html\nb/index.html\nc/index.html\n');
		put('404.html', 'SHELL');
		put('a/index.html', 'REAL');
		process.env.TOMBSTONE_PREVIOUS = previous;
		process.env.TOMBSTONE_MAX = '2';
		delete process.env.RENDER;

		// b, c and every seed path would be tombstoned: over the limit.
		await expect(main(build())).rejects.toThrow(/missing from this build \(limit 2\)/);
		expect(page('a/index.html')).toBe('REAL');
	});
});
