import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import {
	EMBED_FRAME_HEIGHT,
	EMBED_HEIGHT_MESSAGE,
	EMBED_THEMES,
	embedFrameSnippet,
	embedSnippet,
	embedTheme,
	embedUrl,
	isEmbedPath,
	isEmbedRoute
} from './embed';
import { FOR_CHROME } from './forChrome';
import { cspDirectives } from '../../csp.config.js';
import { isShellPath } from './shellRoutes';

const FRONTEND = process.cwd();
const EMBED_JS = readFileSync(join(FRONTEND, 'static', 'embed.js'), 'utf8');
const RENDER_YAML = readFileSync(join(FRONTEND, '..', 'render.yaml'), 'utf8');
const LAYOUT = readFileSync(join(FRONTEND, 'src', 'routes', '+layout.svelte'), 'utf8');
const EMBED_PAGE = readFileSync(join(FRONTEND, 'src', 'routes', 'embed', 'today', '+page.svelte'), 'utf8');
const EMBED_CARD = readFileSync(join(FRONTEND, 'src', 'lib', 'components', 'EmbedToday.svelte'), 'utf8');
const LOCALES: string[] = JSON.parse(readFileSync(join(FRONTEND, 'project.inlang/settings.json'), 'utf8')).locales;

/** Put `<script>` tags (not run — jsdom loads no src) in the body, then run embed.js. */
function runEmbed(...tags: Record<string, string>[]) {
	for (const attrs of tags) {
		const s = document.createElement('script');
		for (const [k, v] of Object.entries(attrs)) s.setAttribute(k, v);
		document.body.appendChild(s);
	}
	new Function(EMBED_JS)();
	return [...document.querySelectorAll('iframe')];
}

afterEach(() => {
	document.body.innerHTML = '';
	delete (window as { __ochorusEmbedFrames?: unknown }).__ochorusEmbedFrames;
});

describe('the church widget page', () => {
	it('is drawn bare only under /embed/', () => {
		expect(isEmbedRoute('/embed/today')).toBe(true);
		expect(isEmbedRoute('/today')).toBe(false);
		expect(isEmbedRoute(null)).toBe(false);
	});

	it('takes its look from ?theme=, light by default', () => {
		expect(embedTheme(null)).toBe('light');
		expect(embedTheme('dark')).toBe('dark');
		expect(embedTheme('sepia')).toBe('sepia');
		expect(embedTheme('auto')).toBe('system');
		expect(embedTheme('<script>')).toBe('light');
	});

	it('is served the SPA shell, bare and in every locale', () => {
		expect(isShellPath('/embed/today')).toBe(true);
	});

	it('may be framed under every locale prefix, and only there', () => {
		// render.yaml's header paths take no `:lang` placeholder, so each prefix
		// is written out — a new locale needs its own rule, or its widget is a
		// blank frame on every church site that asks for it.
		for (const l of LOCALES) {
			const rule = `- path: ${l === 'en' ? '' : `/${l}`}/embed/*\n        name: Content-Security-Policy\n        value: "frame-ancestors *"\n`;
			expect(RENDER_YAML, `no frame-ancestors rule for ${l}`).toContain(rule);
		}
		const framed = [...RENDER_YAML.matchAll(/- path: (\S+)\n\s+name: Content-Security-Policy/g)].map((m) => m[1]);
		expect(framed.every((p) => /^(\/[a-z]{2,3})?\/embed\/\*$/.test(p))).toBe(true);
		expect(RENDER_YAML).toMatch(/- path: \/\*\n\s+name: X-Frame-Options\n\s+value: DENY/);
	});

	it('leaves every other path, and the site-wide policy, unframeable', () => {
		// One X-Frame-Options rule, DENY on everything: nothing loosens it to
		// SAMEORIGIN / ALLOW-FROM for some other path.
		const xfo = [...RENDER_YAML.matchAll(/- path: (\S+)\n\s+name: X-Frame-Options\n\s+value: (\S+)/g)];
		expect(xfo.map((m) => [m[1], m[2]])).toEqual([['/*', 'DENY']]);
		// Every CSP header is an /embed/ path's frame-ancestors, nothing else:
		// never a header on `/*` that would replace the meta policy everywhere.
		const csp = [...RENDER_YAML.matchAll(/- path: (\S+)\n\s+name: Content-Security-Policy\n\s+value: "([^"]*)"/g)];
		expect(csp.length).toBe(LOCALES.length);
		for (const [, path, value] of csp) {
			expect(path).toMatch(/\/embed\/\*$/);
			expect(value).toBe('frame-ancestors *');
		}
		// The meta CSP is not widened for the widget: the live preview on the
		// /for/ pages is drawn inline (EmbedToday), so it needs no frame.
		expect(cspDirectives['frame-ancestors']).toEqual(['none']);
		expect(cspDirectives['frame-src']).not.toContain("'self'");
		expect(cspDirectives['frame-src'].some((s: string) => /ochorus\.com/.test(s))).toBe(false);
	});

	it('keeps sign-in, prompts and the service worker out of the framed page', () => {
		expect(LAYOUT).toContain('if (!embedded) auth.init();');
		expect(LAYOUT).toContain('if (!embedded) pwa.init();');
		expect(LAYOUT).toContain('if (!embedded) install.init();');
		expect(EMBED_PAGE).toContain('<meta name="robots" content="noindex" />');
	});

	it('counts every frameable path, a 404 included, as the widget', () => {
		// Exactly render.yaml's frame-ancestors paths: [/<lang>]/embed/*.
		for (const p of ['/embed/today', '/fr/embed/today', '/ja/embed/nope', '/embed/'])
			expect(isEmbedPath(p), p).toBe(true);
		for (const p of ['/today', '/embedded', '/fr/today', '/books/embed/x', '/'])
			expect(isEmbedPath(p), p).toBe(false);
		expect(LAYOUT).toContain('isEmbedRoute($page.route.id) || isEmbedPath($page.url.pathname)');
	});

	it('never lets the framed page become the full site in place', () => {
		// The palette's results navigate client-side, and so would an error
		// page's links: no new document for X-Frame-Options to refuse.
		expect(LAYOUT).toMatch(/function onWindowKeydown\(e: KeyboardEvent\) \{\n\t\tif \(embedded\) return;/);
		expect(LAYOUT).toMatch(/window\.top !== window\.self &&[\s\S]{0,200}!isEmbedPath\(to\.url\.pathname\)/);
	});

	it('tells a pasted-iframe user the starting height the snippet really has', () => {
		for (const c of Object.values(FOR_CHROME)) expect(c.embed.frameBody).toContain(`${EMBED_FRAME_HEIGHT}px`);
	});

	it('opens every link in a new tab, as a plain ochorus.com URL', () => {
		// Whole tags, past the `>` of an `onclick={() => …}` arrow.
		const anchors = EMBED_CARD.match(/<a\b(?:[^>{]|\{[^}]*\})*>/g) ?? [];
		expect(anchors).toHaveLength(4);
		for (const a of anchors) {
			expect(a).toContain('target="_blank"');
			expect(a).toContain('rel="noopener"');
			// No tagging: the framed pageview's referrer attributes the visit.
			expect(a).not.toMatch(/utm_|[?&]ref=/);
		}
	});

	it('gives churches a tag embed.js will mount', () => {
		expect(embedSnippet('https://ochorus.com', 'fr')).toBe(
			'<script src="https://ochorus.com/embed.js" data-widget="today" data-lang="fr" async></script>'
		);
		expect(EMBED_JS).toContain(`'${EMBED_HEIGHT_MESSAGE}'`);
	});

	it('builds the widget URL per language and look', () => {
		expect(embedUrl('https://ochorus.com', 'en')).toBe('https://ochorus.com/embed/today');
		expect(embedUrl('https://ochorus.com', 'sw', 'light')).toBe('https://ochorus.com/sw/embed/today');
		expect(embedUrl('https://ochorus.com', 'fr', 'dark')).toBe('https://ochorus.com/fr/embed/today?theme=dark');
		// Every look a church can ask for reads back as itself (auto = the OS's).
		expect(EMBED_THEMES.map((th) => embedTheme(th))).toEqual(['light', 'dark', 'sepia', 'system']);
	});

	it('gives builders that strip scripts a sandboxed iframe of the same page', () => {
		const host = document.createElement('div');
		host.innerHTML = embedFrameSnippet('https://ochorus.com', 'fr');
		const frame = host.querySelector('iframe')!;
		expect(frame.getAttribute('src')).toBe(embedUrl('https://ochorus.com', 'fr'));
		expect(frame.getAttribute('loading')).toBe('lazy');
		expect(frame.getAttribute('title')).toBeTruthy();
		expect(frame.style.height).toBe(`${EMBED_FRAME_HEIGHT}px`);
		// The same sandbox as embed.js's own frame: links may open tabs, never
		// navigate the church's page.
		const [mounted] = runEmbed({ src: 'https://ochorus.com/embed.js', 'data-widget': 'today' });
		expect(frame.getAttribute('sandbox')).toBe(mounted.getAttribute('sandbox'));
	});
});

describe('embed.js', () => {
	it('inserts a lazy, sandboxed iframe after the tag, in the asked language and look', () => {
		const [frame] = runEmbed({
			src: 'https://ochorus.com/embed.js',
			'data-widget': 'today',
			'data-lang': 'sw',
			'data-theme': 'dark'
		});
		expect(frame.src).toBe('https://ochorus.com/sw/embed/today?theme=dark');
		expect(frame.src).toBe(embedUrl('https://ochorus.com', 'sw', 'dark'));
		expect(frame.getAttribute('loading')).toBe('lazy');
		expect(frame.getAttribute('sandbox')).not.toContain('allow-top-navigation');
		expect(frame.previousElementSibling?.tagName).toBe('SCRIPT');
		expect(frame.style.height).toBe('420px');
	});

	it('defaults to English and light, and ignores bad values', () => {
		const [frame] = runEmbed({
			src: 'https://ochorus.com/embed.js',
			'data-widget': 'today',
			'data-lang': '"><x',
			'data-theme': 'neon',
			'data-height': '300'
		});
		expect(frame.src).toBe('https://ochorus.com/embed/today');
		expect(frame.style.height).toBe('300px');
	});

	it('mounts each tag once, however many times it runs', () => {
		runEmbed({ src: 'https://ochorus.com/embed.js', 'data-widget': 'today' });
		new Function(EMBED_JS)();
		expect(document.querySelectorAll('iframe')).toHaveLength(1);
	});

	it('leaves other scripts and other widgets alone', () => {
		const frames = runEmbed(
			{ src: 'https://example.org/other.js', 'data-widget': 'today' },
			{ src: 'https://ochorus.com/embed.js', 'data-widget': 'calendar' }
		);
		expect(frames).toHaveLength(0);
	});

	it('grows the frame only to heights its own page reports', () => {
		const [frame] = runEmbed({ src: 'https://ochorus.com/embed.js', 'data-widget': 'today' });
		const post = (origin: string, height: number) =>
			window.dispatchEvent(
				new MessageEvent('message', {
					data: { type: EMBED_HEIGHT_MESSAGE, height },
					origin,
					source: frame.contentWindow
				})
			);
		post('https://evil.example', 900);
		expect(frame.style.height).toBe('420px');
		post('https://ochorus.com', 512.4);
		expect(frame.style.height).toBe('513px');
	});
});
