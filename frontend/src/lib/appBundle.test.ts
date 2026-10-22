import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { dirBytes, fallbackWoffs, listFiles, prunable, prune, resolveCssUrl } from '../../scripts/app-bundle.mjs';

describe('resolveCssUrl', () => {
	it('resolves root-relative and sheet-relative urls to build paths', () => {
		expect(resolveCssUrl('/_app/immutable/assets/a.woff', '_app/immutable/assets/0.css')).toBe(
			'_app/immutable/assets/a.woff'
		);
		expect(resolveCssUrl('./a.woff?v=1', '_app/immutable/assets/0.css')).toBe('_app/immutable/assets/a.woff');
		expect(resolveCssUrl('../fonts/a.woff', '_app/immutable/assets/0.css')).toBe('_app/immutable/fonts/a.woff');
	});

	it('returns null for a url outside the build', () => {
		expect(resolveCssUrl('https://fonts.example/a.woff', 'x.css')).toBeNull();
		expect(resolveCssUrl('//fonts.example/a.woff', 'x.css')).toBeNull();
		expect(resolveCssUrl('data:font/woff;base64,AA', 'x.css')).toBeNull();
		expect(resolveCssUrl('../a.woff', 'x.css')).toBeNull();
	});
});

describe('fallbackWoffs', () => {
	const sheet = (css: string, file = '_app/immutable/assets/0.css') => ({ file, css });

	it('drops a .woff only where a .woff2 sits beside it', () => {
		const css =
			'@font-face{font-family:A;src:url(/_app/immutable/assets/a.X1.woff2)format("woff2"),url(/_app/immutable/assets/a.X2.woff)format("woff")}' +
			'@font-face{font-family:B;src:url("/_app/immutable/assets/b.Y.woff") format("woff")}';
		expect([...fallbackWoffs([sheet(css)])]).toEqual(['_app/immutable/assets/a.X2.woff']);
	});

	it('keeps a .woff that any rule needs on its own', () => {
		const withTwin = '@font-face{src:url(/a/c.Z.woff2)format("woff2"),url(/a/c.Z.woff)format("woff")}';
		const alone = '@font-face{src:url(/a/c.Z.woff)format("woff")}';
		expect(fallbackWoffs([sheet(withTwin), sheet(alone)]).size).toBe(0);
	});

	it('matches by path, so a same-named file elsewhere is not a fallback', () => {
		const css = '@font-face{src:url(./c.woff2)format("woff2"),url(./c.woff)format("woff")}';
		expect([...fallbackWoffs([sheet(css, 'fonts/a.css')])]).toEqual(['fonts/c.woff']);
	});
});

describe('prune', () => {
	let out: string;
	const put = (path: string, bytes = 10) => {
		mkdirSync(dirname(join(out, path)), { recursive: true });
		writeFileSync(join(out, path), 'x'.repeat(bytes));
	};

	beforeAll(() => {
		out = mkdtempSync(join(tmpdir(), 'app-bundle-'));
		put('index.html');
		put('service-worker.js');
		put('covers/humility.png', 100);
		put('covers/art/credits.json');
		put('covers/art/humility.jpg', 100);
		put('portraits/a.jpg', 50);
		put('og/default.png', 50);
		put('marks/leaf.svg');
		put('_app/immutable/assets/a.X.woff2');
		put('_app/immutable/assets/a.X.woff', 30);
		// Same file name, different folder, named by no stylesheet: kept.
		put('fonts/a.X.woff', 7);
		writeFileSync(
			join(out, '_app/immutable/assets/0.css'),
			'@font-face{src:url(/_app/immutable/assets/a.X.woff2)format("woff2"),url(/_app/immutable/assets/a.X.woff)format("woff")}'
		);
	});
	afterAll(() => rmSync(out, { recursive: true, force: true }));

	const assets = { remoteDirs: ['covers', 'portraits', 'og'], keepLocal: ['covers/art/credits.json'] };

	it('lists remote folders, the service worker and fallback fonts', () => {
		expect(prunable(out, assets).sort()).toEqual([
			'_app/immutable/assets/a.X.woff',
			'covers/art/humility.jpg',
			'covers/humility.png',
			'og/default.png',
			'portraits/a.jpg',
			'service-worker.js'
		]);
	});

	it('deletes them, drops emptied folders and keeps the rest', () => {
		const before = dirBytes(out);
		const freed = prune(out, assets);
		expect(freed).toBe(100 + 100 + 50 + 50 + 30 + 10);
		expect(dirBytes(out)).toBe(before - freed);
		expect(existsSync(join(out, 'portraits'))).toBe(false);
		expect(existsSync(join(out, 'og'))).toBe(false);
		expect(listFiles(out).sort()).toEqual([
			'_app/immutable/assets/0.css',
			'_app/immutable/assets/a.X.woff2',
			'covers/art/credits.json',
			'fonts/a.X.woff',
			'index.html',
			'marks/leaf.svg'
		]);
	});
});
