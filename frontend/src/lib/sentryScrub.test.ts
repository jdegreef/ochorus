import { afterEach, describe, expect, it, vi } from 'vitest';
import {
	ALLOW_URLS,
	REDACTED,
	isOffline,
	scrubBreadcrumb,
	scrubEvent,
	scrubUrl
} from './sentryScrub';

describe('scrubUrl', () => {
	it('drops a sign-in session from the hash', () => {
		expect(
			scrubUrl('https://ochorus.com/auth/callback/#access_token=eyJ.secret&refresh_token=r1')
		).toBe('https://ochorus.com/auth/callback/');
	});

	it('redacts the codes Supabase sends back in the query', () => {
		const out = scrubUrl('https://ochorus.com/auth/callback/?code=abc&token_hash=def&type=magiclink');
		expect(out).not.toContain('abc');
		expect(out).not.toContain('def');
		expect(new URL(out).searchParams.get('type')).toBe('magiclink');
	});

	it('redacts what a reader searched for, keeping the context a bug needs', () => {
		const out = scrubUrl('/api/library/search/?q=my+private+prayer&language=am&page=2');
		expect(out.startsWith('/api/library/search/?')).toBe(true);
		const params = new URLSearchParams(out.split('?')[1]);
		expect(params.get('q')).toBe(REDACTED);
		expect(params.get('language')).toBe('am');
		expect(params.get('page')).toBe('2');
	});

	it('matches secret keys whatever their case', () => {
		expect(scrubUrl('https://ochorus.com/?Email=a%40b.c')).not.toContain('a%40b.c');
	});

	it('leaves a URL with nothing secret as it was', () => {
		const url = 'https://api.ochorus.com/api/library/authors/hudson-taylor/?language=am';
		expect(scrubUrl(url)).toBe(url);
	});
});

describe('scrubEvent / scrubBreadcrumb', () => {
	it('scrubs the page URL and every breadcrumb URL, and drops the copied query', () => {
		const event = scrubEvent({
			request: { url: 'https://ochorus.com/search/?q=secret#access_token=t', query_string: 'q=secret' },
			exception: { values: [{ value: 'Bad response from /api/library/search/?q=secret' }] },
			breadcrumbs: [
				{ data: { from: '/auth/callback/#access_token=t', to: '/search/?q=secret' } },
				{ data: { url: 'https://api.ochorus.com/api/library/search/?q=secret', status_code: 200 } },
				{}
			]
		});
		const all = JSON.stringify(event);
		expect(all).not.toContain('secret');
		expect(all).not.toContain('access_token');
		expect(event.request?.query_string).toBeUndefined();
		expect(event.breadcrumbs?.[1].data?.status_code).toBe(200);
	});

	it('scrubs URLs inside a console line, where the API retry logs them', () => {
		const line =
			'[api] TypeError: Failed to fetch from https://api.ochorus.com/api/library/search/?q=my+secret+prayer&language=am — retrying in 700ms';
		const crumb = scrubBreadcrumb({ message: line, data: { arguments: [line, 42], logger: 'console' } });
		expect(JSON.stringify(crumb)).not.toContain('secret');
		expect(crumb.message).toContain('language=am');
		expect(crumb.message).toContain('— retrying in 700ms');
		expect(crumb.data?.arguments).toEqual([crumb.message, 42]);
	});

	it('leaves a breadcrumb without data alone', () => {
		const crumb: { message: string; data?: Record<string, unknown> } = { message: 'click' };
		expect(scrubBreadcrumb(crumb)).toEqual({ message: 'click' });
	});
});

describe('filters', () => {
	afterEach(() => vi.unstubAllGlobals());

	it('allows frames from our own bundle only', () => {
		const ours = 'https://ochorus.com/_app/immutable/chunks/CC0lEi9i.js';
		const extension = 'chrome-extension://abcdef/content.js';
		expect(ALLOW_URLS.some((r) => r.test(ours))).toBe(true);
		expect(ALLOW_URLS.some((r) => r.test(extension))).toBe(false);
	});

	it('knows when the reader is offline', () => {
		vi.stubGlobal('navigator', { onLine: false });
		expect(isOffline()).toBe(true);
		vi.stubGlobal('navigator', { onLine: true });
		expect(isOffline()).toBe(false);
	});
});
