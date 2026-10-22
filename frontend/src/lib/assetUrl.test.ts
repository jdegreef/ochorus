import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { assetHtml, assetSrcset, assetUrl, remoteAsset, remoteHtml, remoteSrcset } from './assetUrl';
import { KEEP_LOCAL, REMOTE_DIRS } from '../../app-assets.js';

const SITE = 'https://ochorus.com';

describe('remoteAsset', () => {
	it('points a path under a remote folder at the site', () => {
		expect(remoteAsset('/covers/art/confessions-640.webp', SITE)).toBe(
			'https://ochorus.com/covers/art/confessions-640.webp'
		);
		expect(remoteAsset('/portraits/andrew-murray.jpg', SITE)).toBe(
			'https://ochorus.com/portraits/andrew-murray.jpg'
		);
		expect(remoteAsset('/illustrations/pilgrims-progress/1.jpg', SITE)).toBe(
			'https://ochorus.com/illustrations/pilgrims-progress/1.jpg'
		);
		expect(remoteAsset('/pdfs/humility.pdf', SITE)).toBe('https://ochorus.com/pdfs/humility.pdf');
	});

	it('leaves what the bundle keeps alone', () => {
		for (const path of [
			'/marks/leaf.svg',
			'/emblems/prayer.svg',
			'/textures/grain-paper.png',
			'/icons/icon-192.png',
			'/covers/art/credits.json',
			'/covers/art/credits.json?v=2'
		]) {
			expect(remoteAsset(path, SITE)).toBe(path);
		}
	});

	it('leaves absolute, protocol-relative, data: and blob: URLs alone', () => {
		for (const url of [
			'https://upload.wikimedia.org/a.jpg',
			'//cdn.example.com/covers/a.jpg',
			'data:image/png;base64,AAAA',
			'blob:capacitor://localhost/abc',
			''
		]) {
			expect(remoteAsset(url, SITE)).toBe(url);
		}
	});

	it('matches whole folder names only', () => {
		expect(remoteAsset('/coversheet/a.png', SITE)).toBe('/coversheet/a.png');
		expect(remoteAsset('/covers', SITE)).toBe('/covers');
		expect(remoteAsset('/books/covers/a.png', SITE)).toBe('/books/covers/a.png');
	});
});

describe('remoteSrcset', () => {
	it('rewrites every candidate and keeps its descriptor', () => {
		expect(remoteSrcset('/covers/a-320.webp 1x, /covers/a-640.webp 2x', SITE)).toBe(
			'https://ochorus.com/covers/a-320.webp 1x, https://ochorus.com/covers/a-640.webp 2x'
		);
		expect(remoteSrcset('/portraits/x-96.webp 96w,/portraits/x-224.webp 224w', SITE)).toBe(
			'https://ochorus.com/portraits/x-96.webp 96w, https://ochorus.com/portraits/x-224.webp 224w'
		);
	});
});

describe('remoteHtml', () => {
	it('rewrites illustration srcs and nothing else', () => {
		const html =
			'<p>See <a href="/books/x/">x</a></p><figure><img alt="A" src="/illustrations/x/1.jpg"></figure>' +
			'<img src="/marks/leaf.svg" alt="">';
		expect(remoteHtml(html, SITE)).toBe(
			'<p>See <a href="/books/x/">x</a></p><figure><img alt="A" src="https://ochorus.com/illustrations/x/1.jpg"></figure>' +
				'<img src="/marks/leaf.svg" alt="">'
		);
	});
});

describe('on the website (IS_APP false)', () => {
	it('returns every input unchanged', () => {
		expect(assetUrl('/covers/a.png')).toBe('/covers/a.png');
		expect(assetUrl(null)).toBeNull();
		expect(assetSrcset('/covers/a-320.webp 1x')).toBe('/covers/a-320.webp 1x');
		expect(assetHtml('<img src="/illustrations/x/1.jpg">')).toBe('<img src="/illustrations/x/1.jpg">');
	});
});

describe('app-assets.js', () => {
	const statics = readdirSync(join(__dirname, '../../static'));

	it('names only folders that exist under static/', () => {
		for (const dir of REMOTE_DIRS) expect(statics, dir).toContain(dir);
	});

	it('keeps only files under a remote folder', () => {
		for (const file of KEEP_LOCAL) expect(REMOTE_DIRS).toContain(file.split('/')[0]);
	});
});

/**
 * Forgetting `assetUrl` is invisible on the website — the path works there —
 * and a broken image in the app, which bundles none of `REMOTE_DIRS`. So, like
 * hydrateSrc.test.ts, a source-text check: every `<img>` whose `src`/`srcset`
 * comes from data must build it with `assetUrl`/`assetSrcset`, either in the
 * attribute itself or where the variable it names is defined (`{@const src =
 * assetUrl(x)}`, `const source = $derived({ src: assetUrl(…) })`). An
 * interpolated literal is fine unless it starts in a remote folder.
 */
describe('every data-driven <img> goes through assetUrl', () => {
	const SRC = join(__dirname, '..');
	/** `file:variable` pairs whose value is never a site path. */
	const EXEMPT = new Set([
		// A blob: URL of the card drawn in the browser.
		'lib/components/notebook/TestimonyDialog.svelte:preview',
		// Set by openLightbox() from a src that already went through assetUrl.
		'routes/about/+page.svelte:lightbox'
	]);
	const svelteFiles = (dir: string, out: string[] = []): string[] => {
		for (const name of readdirSync(dir)) {
			const path = join(dir, name);
			if (statSync(path).isDirectory()) {
				if (name !== 'paraglide') svelteFiles(path, out);
			} else if (name.endsWith('.svelte')) out.push(path);
		}
		return out;
	};
	const REMOTE_LITERAL = new RegExp(`^/(?:${REMOTE_DIRS.join('|')})/`);
	const WRAPPED = /\bassetUrl\(|\bassetSrcset\(/;

	/** Is the variable `name` defined (const/let/@const) by a wrapped expression? */
	const definedWrapped = (text: string, name: string) =>
		[...text.matchAll(new RegExp(`(?:@const|const|let)\\s+${name}\\s*=`, 'g'))].some((m) =>
			WRAPPED.test(text.slice(m.index, m.index + 400).split('\n').slice(0, 4).join('\n'))
		);

	it('builds its src and srcset with assetUrl / assetSrcset', () => {
		const missing: string[] = [];
		for (const path of svelteFiles(SRC)) {
			const file = relative(SRC, path);
			const text = readFileSync(path, 'utf8');
			for (const m of text.matchAll(/<img\s[\s\S]*?\/>/g)) {
				const tag = m[0];
				const line = text.slice(0, m.index).split('\n').length;
				const values: string[] = [];
				for (const a of tag.matchAll(/\s(?:src|srcset)=\{([^}]*)\}/g)) values.push(a[1].trim());
				for (const a of tag.matchAll(/\s\{(src|srcset)\}/g)) values.push(a[1]);
				for (const a of tag.matchAll(/\s(?:src|srcset)="([^"]*\{[^"]*)"/g)) {
					if (REMOTE_LITERAL.test(a[1])) missing.push(`${file}:${line} ${a[1]}`);
				}
				for (const value of values) {
					if (WRAPPED.test(value)) continue;
					// `source.src`, `hero.srcset`, `src`: judge the variable's definition.
					const root = /^([A-Za-z_$][\w$]*)(?:\.[\w$]+)*$/.exec(value)?.[1];
					if (root && (EXEMPT.has(`${file}:${root}`) || definedWrapped(text, root))) continue;
					missing.push(`${file}:${line} ${value}`);
				}
			}
		}
		expect(missing).toEqual([]);
	});
});
