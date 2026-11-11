import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { EMBED_HEIGHT_MESSAGE, embedSnippet, embedTheme, isEmbedRoute } from './embed';
import { isShellPath } from './shellRoutes';

const FRONTEND = process.cwd();
const EMBED_JS = readFileSync(join(FRONTEND, 'static', 'embed.js'), 'utf8');
const RENDER_YAML = readFileSync(join(FRONTEND, '..', 'render.yaml'), 'utf8');
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

	it('gives churches a tag embed.js will mount', () => {
		expect(embedSnippet('https://ochorus.com', 'fr')).toBe(
			'<script src="https://ochorus.com/embed.js" data-widget="today" data-lang="fr" async></script>'
		);
		expect(EMBED_JS).toContain(`'${EMBED_HEIGHT_MESSAGE}'`);
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
